from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from operaciones.models import Existencia, Ubicacion
from .forms import LineasOrdenFormSet, OrdenForm, PartidasFormSet, RecepcionForm
from .models import OrdenCompra, Proveedor
from .services import crear_orden, recibir_orden


def error(texto, status=400):
    return JsonResponse({'error': texto}, status=status)


def endpoint(metodos, *permisos):
    def decorar(vista):
        @never_cache
        @require_http_methods(metodos)
        @wraps(vista)
        def protegida(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return error('Inicia sesión para continuar.', 401)
            if not request.user.has_perms(permisos):
                return error('Tu cuenta no tiene permiso para esta operación.', 403)
            try:
                return vista(request, *args, **kwargs)
            except PermissionDenied:
                return error('Tu cuenta no tiene permiso para esta operación.', 403)
            except ObjectDoesNotExist:
                return error('El registro solicitado no está disponible.', 404)
            except ValidationError as exc:
                return error(' '.join(exc.messages))
        return protegida
    return decorar


def resumen(orden):
    return {'id': orden.pk, 'proveedor': orden.proveedor_nombre, 'estado': orden.estado,
            'estadoTexto': orden.get_estado_display(), 'total': str(orden.total)}


def detalle(orden, usuario):
    datos = resumen(orden)
    datos['lineas'] = [{'id': linea.pk, 'codigo': linea.codigo, 'nombre': linea.nombre,
                        'solicitada': linea.solicitada, 'recibida': linea.recibida,
                        'pendiente': linea.pendiente} for linea in orden.lineas.all()]
    if usuario.has_perm('compras.view_recepcion'):
        datos['recepciones'] = list(orden.recepciones.values('id', 'referencia', 'fecha')[:20])
    return datos


def validar(formulario, partidas):
    if not (formulario.is_valid() and partidas.is_valid()):
        errores = [*formulario.errors.values(), partidas.non_form_errors()]
        errores.extend(mensajes for fila in partidas.errors for mensajes in fila.values())
        raise ValidationError([str(m) for grupo in errores for m in grupo])
    return [fila for fila in partidas.cleaned_data if fila and not fila.get('DELETE')]


def pagina(request, registros):
    return Paginator(registros, 20).get_page(request.GET.get('pagina'))


@endpoint(['GET'], 'compras.view_ordencompra')
def ordenes(request):
    resultado = pagina(request, OrdenCompra.objects.all())
    return JsonResponse({'ordenes': [resumen(orden) for orden in resultado],
                         'pagina': resultado.number, 'paginas': resultado.paginator.num_pages})


@endpoint(['GET'], 'compras.view_ordencompra')
def orden(request, pk):
    return JsonResponse(detalle(OrdenCompra.objects.get(pk=pk), request.user))


@endpoint(['GET', 'POST'], 'compras.add_ordencompra', 'compras.view_ordencompra')
def nueva(request):
    if request.method == 'GET':
        form = OrdenForm(usuario=request.user, tipo='orden')
        proveedores = list(Proveedor.objects.filter(activo=True).values('id', 'codigo', 'nombre'))
        return JsonResponse({'token': form.initial['token'], 'proveedores': proveedores})
    form = OrdenForm(request.POST, usuario=request.user, tipo='orden')
    lineas = LineasOrdenFormSet(request.POST, prefix='lineas')
    for fila in lineas.forms:
        fila.fields['producto'].to_field_name = 'codigo'
    filas = validar(form, lineas)
    creada = crear_orden(usuario=request.user, proveedor_id=form.cleaned_data['proveedor'].pk,
                        observaciones=form.cleaned_data['observaciones'], clave=form.cleaned_data['token'],
                        lineas=[{'producto_id': f['producto'].pk, 'cantidad': f['cantidad'],
                                 'costo_unitario': f['costo_unitario']} for f in filas])
    return JsonResponse(detalle(creada, request.user))


@endpoint(['GET', 'POST'], 'compras.view_ordencompra', 'compras.add_recepcion', 'operaciones.add_lote')
def recibir(request, pk):
    orden = OrdenCompra.objects.get(pk=pk)
    tipo = f'recepcion:{pk}'
    if request.method == 'GET':
        form = RecepcionForm(usuario=request.user, tipo=tipo)
        return JsonResponse({'token': form.initial['token']})
    form = RecepcionForm(request.POST, usuario=request.user, tipo=tipo)
    partidas = PartidasFormSet(request.POST, prefix='partidas', form_kwargs={'orden': orden})
    filas = validar(form, partidas)
    recepcion = recibir_orden(usuario=request.user, orden_id=pk, clave=form.cleaned_data['token'],
                              referencia=form.cleaned_data['referencia'],
                              partidas=[{'linea_id': f['linea'].pk, 'codigo': f['codigo'],
                                         'vencimiento': f['vencimiento'], 'ubicacion': f['ubicacion'],
                                         'cantidad': f['cantidad']} for f in filas])
    orden.refresh_from_db()
    datos = detalle(orden, request.user)
    datos['recepcionId'] = recepcion.pk
    return JsonResponse(datos)


@endpoint(['GET'], 'operaciones.view_existencia')
def inventario(request):
    q = request.GET.get('q', '').strip()
    ubicacion = request.GET.get('ubicacion', '')
    lote = request.GET.get('lote', '').strip()
    producto = request.GET.get('producto', '').strip()
    if (len(q) > 100 or len(lote) > 60 or len(producto) > 30
            or ubicacion not in ['', *Ubicacion.values]):
        return error('Revisa el texto de búsqueda y la ubicación.')
    registros = Existencia.objects.select_related('lote__producto')
    if q:
        registros = registros.filter(Q(lote__codigo__icontains=q) | Q(lote__producto__codigo__icontains=q)
                                     | Q(lote__producto__nombre__icontains=q)
                                     | Q(lote__producto__barras__icontains=q))
    if ubicacion:
        registros = registros.filter(ubicacion=ubicacion)
    if lote:
        registros = registros.filter(lote__codigo=lote)
    if producto:
        registros = registros.filter(lote__producto__codigo=producto)
    resultado = pagina(request, registros.order_by('lote__producto__codigo', 'lote__vencimiento', 'pk'))
    return JsonResponse({'existencias': [{
        'producto': fila.lote.producto.nombre, 'codigo': fila.lote.producto.codigo, 'lote': fila.lote.codigo,
        'vencimiento': fila.lote.vencimiento, 'ubicacion': fila.ubicacion,
        'ubicacionTexto': fila.get_ubicacion_display(), 'cantidad': fila.cantidad,
    } for fila in resultado], 'pagina': resultado.number, 'paginas': resultado.paginator.num_pages})


urlpatterns = [
    path('compras/ordenes/', ordenes),
    path('compras/ordenes/nueva/', nueva),
    path('compras/ordenes/<int:pk>/', orden),
    path('compras/ordenes/<int:pk>/recibir/', recibir),
    path('inventario/', inventario),
]
