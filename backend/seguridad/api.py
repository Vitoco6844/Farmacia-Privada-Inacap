from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.urls import path
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from catalogo.models import Producto
from .views import IngresarView


def estado_sesion(request):
    from config.ui_api import menu
    usuario = request.user
    return JsonResponse({
        'csrfToken': get_token(request),
        'usuario': usuario.get_username() if usuario.is_authenticated else None,
        'roles': list(usuario.groups.values_list('name', flat=True)) if usuario.is_authenticated else [],
        'pantallas': menu(usuario),
        'permisos': {
            'compras': usuario.has_perm('compras.view_ordencompra'),
            'crearOrden': usuario.has_perms(['compras.view_ordencompra', 'compras.add_ordencompra']),
            'recibirOrden': usuario.has_perms(['compras.view_ordencompra', 'compras.add_recepcion',
                                               'operaciones.add_lote']),
            'inventario': usuario.has_perm('operaciones.view_existencia'),
            'anularOrden': usuario.has_perm('compras.anular_ordencompra'),
            'crearProducto': usuario.has_perm('catalogo.add_producto'),
            'editarProducto': usuario.has_perm('catalogo.change_producto'),
        },
    })


class IngresarApi(IngresarView):
    http_method_names = ['post']
    redirect_authenticated_user = False

    def form_valid(self, form):
        super().form_valid(form)
        return estado_sesion(self.request)

    def form_invalid(self, form):
        return JsonResponse({'error': 'Usuario o contraseña incorrectos.'}, status=401)

    def _limitado(self, form, hasta):
        respuesta_html = super()._limitado(form, hasta)
        respuesta = JsonResponse({'error': 'Ingreso limitado temporalmente. Intenta más tarde.'}, status=429)
        respuesta['Retry-After'] = respuesta_html['Retry-After']
        return respuesta


@require_POST
def salir(request):
    logout(request)
    return estado_sesion(request)


@require_GET
def productos(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Inicia sesión para consultar productos.'}, status=401)
    if not request.user.has_perm('catalogo.view_producto'):
        return JsonResponse({'error': 'Tu cuenta no tiene permiso para consultar productos.'}, status=403)
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    condicion = request.GET.get('condicion', '')
    estado = request.GET.get('estado', '')
    if len(q) > 100 or len(categoria) > 100 or condicion not in ['', *Producto.Condicion.values] or estado not in ('', 'activo', 'inactivo'):
        return JsonResponse({'error': 'Revisa los filtros de búsqueda.'}, status=400)
    visibles = Producto.objects.all()
    if not request.user.has_perm('catalogo.change_producto'):
        visibles = visibles.filter(activo=True)
    resumen = visibles.aggregate(
        total=Count('pk'),
        activos=Count('pk', filter=Q(activo=True)),
        receta=Count('pk', filter=Q(condicion__in=(Producto.Condicion.SIMPLE, Producto.Condicion.RETENIDA))),
    )
    registros = visibles.select_related('categoria').order_by('codigo', 'pk')
    if q:
        registros = registros.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(barras__icontains=q))
    if categoria:
        registros = registros.filter(categoria__nombre=categoria)
    if condicion:
        registros = registros.filter(condicion=condicion)
    if estado:
        registros = registros.filter(activo=estado == 'activo')
    pagina = Paginator(registros, 12).get_page(request.GET.get('pagina'))
    return JsonResponse({
        'productos': [{
            'id': p.pk, 'codigo': p.codigo, 'nombre': p.nombre, 'categoria': p.categoria.nombre,
            'presentacion': p.presentacion, 'condicion': p.condicion, 'iniciales': p.iniciales,
            'precio': str(p.precio), 'activo': p.activo,
        } for p in pagina],
        'pagina': pagina.number, 'paginas': pagina.paginator.num_pages, 'total': pagina.paginator.count,
        'resumen': resumen, 'categorias': list(visibles.order_by('categoria__nombre').values_list(
            'categoria__nombre', flat=True).distinct()), 'condiciones': Producto.Condicion.values,
    })


urlpatterns = [
    path('sesion/', never_cache(require_GET(estado_sesion))),
    path('sesion/ingresar/', never_cache(IngresarApi.as_view())),
    path('sesion/salir/', never_cache(salir)),
    path('productos/', never_cache(productos)),
]
