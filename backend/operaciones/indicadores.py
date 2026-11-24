from datetime import datetime, time, timedelta
from decimal import Decimal
from django.db.models import Case, CharField, Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from catalogo.models import Producto
from .models import Lote, Venta


HORIZONTE_VENCIMIENTO = 60


def productos_bajo_minimo(hoy=None):
    """Una sola lista de reposición: combina el mínimo total del producto (bodega + vitrina) con los umbrales
    por ubicación configurados en «Alertas por ubicación». Antes eran dos sistemas sin conexión."""
    from gestion.models import ConfiguracionAlerta
    hoy = hoy or timezone.localdate()
    vigente = Q(lotes__vencimiento__gt=hoy, lotes__bloqueado=False)

    def disponible(ubicacion=None):
        filtro = vigente & Q(lotes__existencias__ubicacion=ubicacion) if ubicacion else vigente
        return Coalesce(Sum('lotes__existencias__cantidad', filter=filtro), 0, output_field=IntegerField())

    def umbral(ubicacion):
        return Subquery(ConfiguracionAlerta.objects.filter(producto=OuterRef('pk'), ubicacion=ubicacion).values('stock_minimo')[:1])

    return Producto.objects.filter(activo=True).annotate(
        disponible=disponible(), disponible_vitrina=disponible('vitrina'), disponible_bodega=disponible('bodega'),
        umbral_vitrina=umbral('vitrina'), umbral_bodega=umbral('bodega'),
    ).filter(
        Q(disponible__lte=F('stock_minimo'))
        | Q(umbral_vitrina__isnull=False, disponible_vitrina__lte=F('umbral_vitrina'))
        | Q(umbral_bodega__isnull=False, disponible_bodega__lte=F('umbral_bodega'))
    ).annotate(motivo=Case(
        When(disponible__lte=F('stock_minimo'), then=Value('Total bajo el mínimo del producto')),
        When(umbral_vitrina__isnull=False, disponible_vitrina__lte=F('umbral_vitrina'), then=Value('Vitrina bajo su umbral')),
        default=Value('Bodega bajo su umbral'), output_field=CharField(),
    )).order_by('disponible', 'codigo')


def lotes_por_vencer(con_stock, hoy):
    """Lotes vigentes dentro del aviso de vencimiento: 60 días, o el plazo mayor configurado para el producto."""
    from gestion.models import ConfiguracionAlerta
    plazos = {}
    for producto_id, dias in ConfiguracionAlerta.objects.values_list('producto_id', 'dias_vencimiento'):
        plazos[producto_id] = max(dias, plazos.get(producto_id, HORIZONTE_VENCIMIENTO))
    limite = hoy + timedelta(days=max(plazos.values(), default=HORIZONTE_VENCIMIENTO))
    candidatos = con_stock.filter(vencimiento__gt=hoy, vencimiento__lte=limite).order_by('vencimiento', 'pk')
    return [lote for lote in candidatos
            if lote.vencimiento <= hoy + timedelta(days=plazos.get(lote.producto_id, HORIZONTE_VENCIMIENTO))]


def construir_panel(*, ver_comercial):
    ahora = timezone.now()
    zona = timezone.get_current_timezone()
    hoy = timezone.localdate(ahora)
    inicio = timezone.make_aware(datetime.combine(hoy, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hoy + timedelta(days=1), time.min), zona)
    bajos = productos_bajo_minimo(hoy)
    from .graficos import completar_semana, estado_vitrina, medios_de_pago, ventas_por_hora
    con_stock = Lote.objects.select_related('producto').annotate(envases=Sum('existencias__cantidad')).filter(envases__gt=0)
    vencidos = con_stock.filter(vencimiento__lte=hoy).order_by('vencimiento', 'pk')
    proximos = lotes_por_vencer(con_stock, hoy)
    datos = {
        'actualizado': ahora, 'hoy': hoy, 'ver_comercial': ver_comercial,
        'bajos_total': bajos.count(), 'bajos': list(bajos[:6]),
        'proximos_total': len(proximos), 'proximos': proximos[:6],
        'vencidos_total': vencidos.count(), 'vencidos': list(vencidos[:6]),
        'vitrina': estado_vitrina(hoy, set(bajos.values_list('pk', flat=True))),
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
        datos['dias'] = completar_semana(dias, hoy)
        datos['horas'] = ventas_por_hora(diarias, zona, ahora)
        datos['pagos'] = medios_de_pago(diarias)
        datos['pico'] = next((h for h in datos['horas'] if h['pico']), None)
    return datos
