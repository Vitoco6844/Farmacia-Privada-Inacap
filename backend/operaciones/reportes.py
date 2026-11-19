"""Consultas y filas compartidas por la pantalla y sus exportaciones."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from django import forms
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from .models import DetalleVenta, Existencia, Ubicacion

MAX_EXPORT_ROWS = 5000


class VentasFiltro(forms.Form):
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), input_formats=['%Y-%m-%d'])
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), input_formats=['%Y-%m-%d'])
    q = forms.CharField(required=False, max_length=120, label='Nombre o código histórico')

    def clean(self):
        datos = super().clean()
        if datos.get('desde') and datos.get('hasta') and datos['desde'] > datos['hasta']:
            raise forms.ValidationError('La fecha Desde debe ser anterior o igual a Hasta.')
        if datos.get('hasta') == date.max:
            self.add_error('hasta', 'Selecciona una fecha anterior al 31/12/9999.')
        return datos


class InventarioFiltro(forms.Form):
    q = forms.CharField(required=False, max_length=120, label='Nombre, código o lote')
    ubicacion = forms.ChoiceField(required=False, label='Ubicación', choices=[('', 'Todas')] + list(Ubicacion.choices))
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos'), ('disponible', 'Disponible'),
        ('vencido', 'Vencido / vence hoy'), ('proximo', 'Vence en 60 días'), ('bloqueado', 'Bloqueado / inactivo'), ('sin_stock', 'Sin stock')])


def consulta(tipo, filtros):
    q = filtros.get('q', '')
    if tipo == 'ventas':
        qs = DetalleVenta.objects.select_related('venta__usuario').annotate(importe=ExpressionWrapper(
            F('precio_unitario') * F('cantidad'), output_field=DecimalField(max_digits=24, decimal_places=0)))
        if filtros.get('desde'):
            inicio = timezone.make_aware(datetime.combine(filtros['desde'], time.min))
            qs = qs.filter(venta__fecha__gte=inicio)
        if filtros.get('hasta'):
            fin = timezone.make_aware(datetime.combine(filtros['hasta'] + timedelta(days=1), time.min))
            qs = qs.filter(venta__fecha__lt=fin)
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
        return qs.order_by('-venta__fecha', '-venta_id', 'pk')
    hoy = timezone.localdate()
    qs = Existencia.objects.select_related('lote__producto')
    if q:
        qs = qs.filter(Q(lote__producto__nombre__icontains=q) | Q(lote__producto__codigo__icontains=q) | Q(lote__codigo__icontains=q))
    if filtros.get('ubicacion'):
        qs = qs.filter(ubicacion=filtros['ubicacion'])
    estado = filtros.get('estado')
    if estado == 'disponible':
        qs = qs.filter(cantidad__gt=0, lote__bloqueado=False, lote__producto__activo=True, lote__vencimiento__gt=hoy)
    elif estado == 'vencido':
        qs = qs.filter(cantidad__gt=0, lote__vencimiento__lte=hoy)
    elif estado == 'proximo':
        qs = qs.filter(cantidad__gt=0, lote__vencimiento__gt=hoy, lote__vencimiento__lte=hoy + timedelta(days=60))
    elif estado == 'bloqueado':
        qs = qs.filter(Q(lote__bloqueado=True) | Q(lote__producto__activo=False))
    elif estado == 'sin_stock':
        qs = qs.filter(cantidad=0)
    return qs.order_by('lote__producto__codigo', 'lote__vencimiento', 'lote_id', 'ubicacion')


def resumen(tipo, qs):
    agregado = qs.aggregate(envases=Sum('cantidad'), **({'total': Sum('importe')} if tipo == 'ventas' else {}))
    return {'filas': qs.count(), 'envases': agregado['envases'] or 0,
        'total': (agregado.get('total') or Decimal('0')) if tipo == 'ventas' else None}


def estado_stock(stock, hoy):
    if stock.lote.vencimiento <= hoy:
        return 'Vencido / vence hoy'
    if stock.lote.bloqueado or not stock.lote.producto.activo:
        return 'Bloqueado / inactivo'
    if not stock.cantidad:
        return 'Sin stock'
    if stock.lote.vencimiento <= hoy + timedelta(days=60):
        return 'Próximo a vencer'
    return 'Disponible'


def columnas(tipo):
    if tipo == 'ventas':
        return ['Venta', 'Fecha Santiago', 'Código', 'Producto histórico', 'Envases', 'Precio CLP', 'Importe CLP', 'Responsable']
    return ['Código', 'Producto / presentación', 'Lote', 'Vencimiento', 'Ubicación', 'Envases', 'Estado']


def filas(tipo, registros, hoy=None):
    hoy = hoy or timezone.localdate()
    if tipo == 'ventas':
        return [[f'V-{d.venta_id}', timezone.localtime(d.venta.fecha).replace(tzinfo=None), d.codigo, d.nombre,
            d.cantidad, d.precio_unitario, d.importe, d.venta.usuario.username] for d in registros]
    return [[s.lote.producto.codigo, f'{s.lote.producto.nombre} · {s.lote.producto.presentacion}', s.lote.codigo,
        s.lote.vencimiento, s.get_ubicacion_display(), s.cantidad, estado_stock(s, hoy)] for s in registros]


def descripcion_filtros(filtros):
    etiquetas = {'desde': 'Desde', 'hasta': 'Hasta', 'q': 'Búsqueda', 'ubicacion': 'Ubicación', 'estado': 'Estado'}
    return '; '.join(f'{etiquetas[k]}: {v.isoformat() if hasattr(v, "isoformat") else v}'
        for k, v in filtros.items() if v) or 'Sin filtros: todos los registros'
