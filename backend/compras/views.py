from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from config.respuestas import render
from django.views.decorators.http import require_POST
from .forms import AnularForm, LineasOrdenFormSet, OrdenForm, PartidasFormSet, ProveedorForm, RecepcionForm
from .models import EventoProveedor, OrdenCompra, Proveedor, Recepcion
from .services import anular_orden, crear_orden, recibir_orden


@login_required
@permission_required('compras.view_ordencompra', raise_exception=True)
def ordenes(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    qs = OrdenCompra.objects.select_related('usuario', 'proveedor')
    if q:
        filtro = Q(proveedor_nombre__icontains=q) | Q(lineas__nombre__icontains=q) | Q(lineas__codigo__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro).distinct()
    if estado in OrdenCompra.Estado.values:
        qs = qs.filter(estado=estado)
    params = request.GET.copy()
    params.pop('pagina', None)
    return render(request, 'compras/ordenes.html', {'pagina': Paginator(qs, 15).get_page(request.GET.get('pagina')),
        'q': q, 'estado': estado, 'estados': OrdenCompra.Estado.choices, 'params': params.urlencode()})


@login_required
@permission_required('compras.add_ordencompra', raise_exception=True)
def nueva_orden(request):
    datos = request.POST if request.method == 'POST' else None
    form = OrdenForm(datos, usuario=request.user, tipo='orden')
    lineas = LineasOrdenFormSet(datos, prefix='lineas')
    if request.method == 'POST':
        valido = form.is_valid()
        lineas_validas = lineas.is_valid()
        if valido and lineas_validas:
            try:
                orden = crear_orden(usuario=request.user, proveedor_id=form.cleaned_data['proveedor'].pk,
                    observaciones=form.cleaned_data['observaciones'], clave=form.cleaned_data['token'],
                    lineas=[{'producto_id': d['producto'].pk, 'cantidad': d['cantidad'], 'costo_unitario': d['costo_unitario']}
                        for d in lineas.cleaned_data if d and not d.get('DELETE')])
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, 'Orden registrada. Crear una orden no aumenta el inventario.')
                return redirect('compras:orden_detalle', pk=orden.pk)
    return render(request, 'compras/formulario.html', {'form': form, 'lineas': lineas, 'tipo': 'orden',
        'titulo': 'Nueva orden de compra', 'introduccion': 'Selecciona proveedor y productos. Los costos de compra se registran por separado de los precios de venta.'})


@login_required
@permission_required('compras.view_ordencompra', raise_exception=True)
def orden_detalle(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.select_related('usuario', 'proveedor').prefetch_related(
        'lineas', 'recepciones__usuario', 'eventos__usuario'), pk=pk)
    return render(request, 'compras/orden_detalle.html', {'orden': orden, 'anular_form': AnularForm(),
        'abierta': orden.estado in (OrdenCompra.Estado.PENDIENTE, OrdenCompra.Estado.PARCIAL)})


@login_required
@permission_required('compras.add_recepcion', raise_exception=True)
def nueva_recepcion(request, pk):
    orden = get_object_or_404(OrdenCompra.objects.prefetch_related('lineas'), pk=pk)
    datos = request.POST if request.method == 'POST' else None
    form = RecepcionForm(datos, usuario=request.user, tipo=f'recepcion:{pk}')
    lineas = PartidasFormSet(datos, prefix='partidas', form_kwargs={'orden': orden})
    if request.method == 'POST':
        valido = form.is_valid()
        lineas_validas = lineas.is_valid()
        if valido and lineas_validas:
            try:
                recepcion = recibir_orden(usuario=request.user, orden_id=pk, referencia=form.cleaned_data['referencia'],
                    clave=form.cleaned_data['token'], partidas=[{'linea_id': d['linea'].pk, 'codigo': d['codigo'],
                        'vencimiento': d['vencimiento'], 'ubicacion': d['ubicacion'], 'cantidad': d['cantidad']}
                        for d in lineas.cleaned_data if d and not d.get('DELETE')])
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, 'Recepción registrada e inventario actualizado.')
                return redirect('compras:recepcion_detalle', pk=recepcion.pk)
    return render(request, 'compras/formulario.html', {'form': form, 'lineas': lineas, 'tipo': 'recepcion', 'orden': orden,
        'titulo': f'Recibir orden OC-{pk}', 'introduccion': 'Registra únicamente los envases efectivamente entregados. Puedes repartir un producto entre varios lotes o ubicaciones.'})


@login_required
@permission_required('compras.view_recepcion', raise_exception=True)
def recepcion_detalle(request, pk):
    recepcion = get_object_or_404(Recepcion.objects.select_related('orden', 'usuario').prefetch_related(
        'detalles__linea', 'detalles__movimiento__lote'), pk=pk)
    return render(request, 'compras/recepcion_detalle.html', {'recepcion': recepcion})


@login_required
@permission_required('compras.anular_ordencompra', raise_exception=True)
@require_POST
def anular(request, pk):
    get_object_or_404(OrdenCompra, pk=pk)
    form = AnularForm(request.POST)
    if form.is_valid():
        try:
            anular_orden(usuario=request.user, orden_id=pk, motivo=form.cleaned_data['motivo'])
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'Orden anulada. Su historial se conserva.')
    else:
        messages.error(request, 'Indica un motivo de anulación de entre 10 y 300 caracteres.')
    return redirect('compras:orden_detalle', pk=pk)


@login_required
@permission_required('compras.view_proveedor', raise_exception=True)
def proveedores(request):
    return render(request, 'compras/proveedores.html', {'pagina': Paginator(Proveedor.objects.all(), 20).get_page(request.GET.get('pagina'))})


def _proveedor_formulario(request, proveedor=None):
    form = ProveedorForm(request.POST if request.method == 'POST' else None, instance=proveedor)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                anterior = Proveedor.objects.filter(pk=proveedor.pk).values('codigo', 'nombre', 'email', 'telefono', 'activo').first() if proveedor else {}
                guardado = form.save()
                posterior = {k: getattr(guardado, k) for k in ('codigo', 'nombre', 'email', 'telefono', 'activo')}
                EventoProveedor.objects.create(proveedor=guardado, usuario=request.user, anterior=anterior, posterior=posterior)
        except IntegrityError:
            form.add_error(None, 'No se pudo guardar. Revisa que el código sea único.')
        else:
            messages.success(request, 'Proveedor guardado. Las órdenes previas conservan su nombre histórico.')
            return redirect('compras:proveedores')
    return render(request, 'compras/proveedor_formulario.html', {'form': form, 'proveedor': proveedor})


@login_required
@permission_required('compras.add_proveedor', raise_exception=True)
def nuevo_proveedor(request):
    return _proveedor_formulario(request)


@login_required
@permission_required('compras.change_proveedor', raise_exception=True)
def editar_proveedor(request, pk):
    return _proveedor_formulario(request, get_object_or_404(Proveedor, pk=pk))
