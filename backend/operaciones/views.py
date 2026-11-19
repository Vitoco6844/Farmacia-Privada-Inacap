from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import DatabaseError
import logging
from django.shortcuts import get_object_or_404, redirect
from config.respuestas import render
from django.utils import timezone
from .forms import IngresoForm, TrasladoForm, VentaForm
from .models import Existencia, Movimiento, Ubicacion, Venta
from .services import confirmar_venta, registrar_ingreso, transferir
from .indicadores import construir_panel, productos_bajo_minimo

logger = logging.getLogger(__name__)


@login_required
@permission_required('operaciones.view_existencia', raise_exception=True)
def panel(request):
    try:
        datos = construir_panel(ver_comercial=request.user.has_perm('operaciones.view_venta'))
    except DatabaseError:
        logger.error('No se pudieron consultar los indicadores del panel.')
        return render(request, 'operaciones/panel.html', {'error_datos': True}, status=503)
    respuesta = render(request, 'operaciones/panel.html', datos)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


@login_required
@permission_required('operaciones.view_existencia', raise_exception=True)
def alertas_stock(request):
    productos = productos_bajo_minimo()
    return render(request, 'operaciones/alertas_stock.html', {
        'pagina': Paginator(productos, 15).get_page(request.GET.get('pagina')),
    })


@login_required
@permission_required('operaciones.view_existencia', raise_exception=True)
def inventario(request):
    hoy = timezone.localdate()
    q = request.GET.get('q', '').strip()
    ubicacion = request.GET.get('ubicacion', '')
    estado = request.GET.get('estado', '')
    stocks = Existencia.objects.select_related('lote__producto').order_by('lote__producto__codigo', 'lote__vencimiento', 'pk')
    if q:
        stocks = stocks.filter(Q(lote__producto__nombre__icontains=q) | Q(lote__producto__codigo__icontains=q) | Q(lote__codigo__icontains=q) | Q(lote__producto__barras__icontains=q))
    if ubicacion in Ubicacion.values:
        stocks = stocks.filter(ubicacion=ubicacion)
    if estado == 'disponible':
        stocks = stocks.filter(lote__vencimiento__gt=hoy, lote__bloqueado=False, lote__producto__activo=True, cantidad__gt=0)
    elif estado == 'vencido':
        stocks = stocks.filter(lote__vencimiento__lte=hoy, cantidad__gt=0)
    elif estado == 'proximo':
        stocks = stocks.filter(lote__vencimiento__gt=hoy, lote__vencimiento__lte=hoy + timedelta(days=60), cantidad__gt=0)
    pagina = Paginator(stocks, 12).get_page(request.GET.get('pagina'))
    params = request.GET.copy()
    params.pop('pagina', None)
    return render(request, 'operaciones/inventario.html', {
        'pagina': pagina, 'params': params.urlencode(), 'q': q, 'ubicacion': ubicacion, 'estado': estado,
        'hoy': hoy, 'proximo': hoy + timedelta(days=60), 'ubicaciones': Ubicacion.choices,
        'total': stocks.aggregate(total=Sum('cantidad'))['total'] or 0,
    })


def _formulario(request, clase, tipo, titulo, intro):
    form = clase(request.POST if request.method == 'POST' else None, usuario=request.user, tipo=tipo)
    if request.method == 'POST' and form.is_valid():
        datos = form.cleaned_data
        try:
            if tipo == 'ingreso':
                registrar_ingreso(usuario=request.user, producto_id=datos['producto'].pk, codigo=datos['codigo'],
                    vencimiento=datos['vencimiento'], ubicacion=datos['ubicacion'], cantidad=datos['cantidad'], clave=datos['token'])
            elif tipo == 'traslado':
                transferir(usuario=request.user, lote_id=datos['lote'].pk, origen=datos['origen'], destino=datos['destino'],
                    cantidad=datos['cantidad'], clave=datos['token'])
            else:
                venta = confirmar_venta(usuario=request.user, producto_id=datos['producto'].pk,
                    cantidad=datos['cantidad'], clave=datos['token'])
                return redirect('operaciones:venta_detalle', pk=venta.pk)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Operación registrada. Un reintento del mismo formulario no duplica las cantidades.')
            return redirect('operaciones:inventario')
    return render(request, 'operaciones/formulario.html', {'form': form, 'titulo': titulo, 'intro': intro, 'tipo': tipo})


@login_required
@permission_required('operaciones.add_lote', raise_exception=True)
def ingreso(request):
    return _formulario(request, IngresoForm, 'ingreso', 'Registrar ingreso de stock',
        'Registra cantidades por lote y ubicación. Los lotes vencidos se conservan en inventario, pero no se venden.')


@login_required
@permission_required('operaciones.change_existencia', raise_exception=True)
def traslado(request):
    return _formulario(request, TrasladoForm, 'traslado', 'Trasladar existencias',
        'Mueve envases entre bodega y vitrina. El total del lote se conserva.')


@login_required
@permission_required('operaciones.add_venta', raise_exception=True)
def nueva_venta(request):
    from comercio.views import pos
    return pos(request)


@login_required
@permission_required('operaciones.view_venta', raise_exception=True)
def ventas(request):
    ventas_qs = Venta.objects.select_related('usuario').prefetch_related('detalles').all()
    return render(request, 'operaciones/ventas.html', {'pagina': Paginator(ventas_qs, 12).get_page(request.GET.get('pagina'))})


@login_required
@permission_required('operaciones.view_venta', raise_exception=True)
def venta_detalle(request, pk):
    venta = get_object_or_404(Venta.objects.select_related('usuario').prefetch_related('detalles__asignaciones__lote'), pk=pk)
    return render(request, 'operaciones/venta_detalle.html', {'venta': venta})


@login_required
@permission_required('operaciones.view_movimiento', raise_exception=True)
def movimientos(request):
    qs = Movimiento.objects.select_related('lote__producto', 'usuario', 'detalle_venta')
    return render(request, 'operaciones/movimientos.html', {'pagina': Paginator(qs, 15).get_page(request.GET.get('pagina'))})
