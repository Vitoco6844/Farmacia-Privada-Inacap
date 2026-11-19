from datetime import datetime, time, timedelta
from decimal import Decimal
from django.db.models import Count, F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from catalogo.models import Producto
from .models import Lote, Venta


def productos_bajo_minimo(hoy=None):
    hoy = hoy or timezone.localdate()
    return Producto.objects.filter(activo=True).annotate(disponible=Coalesce(
        Sum('lotes__existencias__cantidad', filter=Q(lotes__vencimiento__gt=hoy, lotes__bloqueado=False)),
        0, output_field=IntegerField(),
    )).filter(disponible__lte=F('stock_minimo')).order_by('disponible', 'codigo')


def construir_panel(*, ver_comercial):
    ahora = timezone.now()
    zona = timezone.get_current_timezone()
    hoy = timezone.localdate(ahora)
    inicio = timezone.make_aware(datetime.combine(hoy, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hoy + timedelta(days=1), time.min), zona)
    bajos = productos_bajo_minimo(hoy)
    con_stock = Lote.objects.select_related('producto').annotate(envases=Sum('existencias__cantidad')).filter(envases__gt=0)
    vencidos = con_stock.filter(vencimiento__lte=hoy).order_by('vencimiento', 'pk')
    proximos = con_stock.filter(vencimiento__gt=hoy, vencimiento__lte=hoy + timedelta(days=60)).order_by('vencimiento', 'pk')
    datos = {
        'actualizado': ahora, 'hoy': hoy, 'ver_comercial': ver_comercial,
        'bajos_total': bajos.count(), 'bajos': list(bajos[:6]),
        'proximos_total': proximos.count(), 'proximos': list(proximos[:6]),
        'vencidos_total': vencidos.count(), 'vencidos': list(vencidos[:6]),
    }
    if ver_comercial:
        diarias = Venta.objects.filter(fecha__gte=inicio, fecha__lt=fin)
        datos['ventas_hoy'] = diarias.count()
        datos['importe_hoy'] = diarias.aggregate(total=Sum('total'))['total'] or Decimal('0')
        datos['ultimas_ventas'] = list(Venta.objects.select_related('usuario').order_by('-fecha', '-pk')[:5])
        desde = hoy - timedelta(days=6)
        inicio_semana = timezone.make_aware(datetime.combine(desde, time.min), zona)
        registros = Venta.objects.filter(fecha__gte=inicio_semana, fecha__lt=fin).annotate(
            dia=TruncDate('fecha', tzinfo=zona)).values('dia').annotate(total=Sum('total'), cantidad=Count('pk'))
        por_dia = {registro['dia']: registro for registro in registros}
        dias = []
        for offset in range(7):
            dia = desde + timedelta(days=offset)
            fila = por_dia.get(dia, {'total': Decimal('0'), 'cantidad': 0})
            dias.append({'dia': dia, 'total': fila['total'], 'cantidad': fila['cantidad']})
        maximo = max((d['total'] for d in dias), default=0)
        for dia in dias:
            dia['ancho'] = int(dia['total'] / maximo * 100) if maximo else 0
        datos['dias'] = dias
    return datos
