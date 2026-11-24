"""Datos de los gráficos del panel del turno (Inicio).

Cada función devuelve listas simples (sin objetos de modelo) para que la plantilla de Django y la API del
frontend independiente dibujen lo mismo. Los altos y anchos se entregan en porcentaje (0–100) respecto del
máximo de cada serie, de modo que el dibujo no necesite cálculos en el navegador.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, IntegerField, Q, Sum
from django.db.models.functions import Coalesce, ExtractHour

from catalogo.models import Producto

DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def porcentaje(valor, maximo, minimo_visible=2):
    """Altura relativa; un valor positivo nunca queda invisible (mínimo 2 %)."""
    if not maximo or not valor:
        return 0
    return max(minimo_visible, int(Decimal(valor) / Decimal(maximo) * 100))


def ventas_por_hora(ventas_hoy, zona, ahora):
    """Ventas de hoy agrupadas por hora local, desde la primera hora con ventas hasta la hora actual."""
    filas = {f['hora']: f for f in ventas_hoy.annotate(hora=ExtractHour('fecha', tzinfo=zona)).values('hora')
             .annotate(total=Sum('total'), cantidad=Count('pk'))}
    if not filas:
        return []
    desde = min(filas)
    hasta = max(max(filas), ahora.astimezone(zona).hour)
    maximo = max(f['total'] for f in filas.values())
    horas = []
    for hora in range(desde, hasta + 1):
        fila = filas.get(hora, {'total': Decimal('0'), 'cantidad': 0})
        horas.append({
            'etiqueta': f'{hora:02d}', 'rango': f'{hora:02d}:00–{(hora + 1) % 24:02d}:00',
            'total': fila['total'], 'cantidad': fila['cantidad'], 'alto': porcentaje(fila['total'], maximo),
            'pico': fila['total'] == maximo,
        })
    return horas


def completar_semana(dias, hoy):
    """Agrega a la serie de 7 días la etiqueta del día, si es hoy y la altura relativa."""
    maximo = max((d['total'] for d in dias), default=0)
    for dia in dias:
        dia['es_hoy'] = dia['dia'] == hoy
        dia['etiqueta'] = 'Hoy' if dia['es_hoy'] else DIAS_SEMANA[dia['dia'].weekday()]
        dia['alto'] = porcentaje(dia['total'], maximo)
    return dias


def medios_de_pago(ventas_hoy):
    """Importe de hoy por medio de pago (efectivo, tarjeta, transferencia), incluidos los que suman cero."""
    from comercio.models import Cobro
    medios = dict(Cobro._meta.get_field('medio').choices)
    totales = {f['medio']: f for f in Cobro.objects.filter(venta__in=ventas_hoy).values('medio')
               .annotate(total=Sum('venta__total'), cantidad=Count('pk'))}
    suma = sum((f['total'] for f in totales.values()), Decimal('0'))
    maximo = max((f['total'] for f in totales.values()), default=0)
    resultado = []
    for clave, nombre in medios.items():
        fila = totales.get(clave, {'total': Decimal('0'), 'cantidad': 0})
        resultado.append({
            'clave': clave, 'nombre': nombre, 'total': fila['total'], 'cantidad': fila['cantidad'],
            'porcentaje': int(round(fila['total'] / suma * 100)) if suma else 0,
            'ancho': porcentaje(fila['total'], maximo),
        })
    return resultado


def _nombres(productos, limite=3):
    nombres = [p.nombre for p in productos[:limite]]
    resto = len(productos) - limite
    return ', '.join(nombres) + (f' y {resto} más' if resto > 0 else '')


def estado_vitrina(hoy, bajos_ids):
    """Productos activos según su vitrina: agotado (sin stock vigente en vitrina), bajo mínimo (en la lista de
    reposición) o al día. Usa la misma lista de reposición que el resto del panel."""
    productos = list(Producto.objects.filter(activo=True).annotate(vitrina=Coalesce(
        Sum('lotes__existencias__cantidad', filter=Q(lotes__vencimiento__gt=hoy, lotes__bloqueado=False,
                                                     lotes__existencias__ubicacion='vitrina')),
        0, output_field=IntegerField())).order_by('nombre'))
    grupos = {'ok': [], 'bajo': [], 'agotado': []}
    for producto in productos:
        if producto.vitrina == 0:
            grupos['agotado'].append(producto)
        elif producto.pk in bajos_ids:
            grupos['bajo'].append(producto)
        else:
            grupos['ok'].append(producto)
    total = len(productos)
    nombres = {'ok': 'Al día', 'bajo': 'Bajo mínimo', 'agotado': 'Agotado en vitrina'}
    return [{
        'clave': clave, 'nombre': nombres[clave], 'cantidad': len(grupos[clave]),
        'porcentaje': round(len(grupos[clave]) / total * 100) if total else 0,
        'detalle': _nombres(grupos[clave]) if grupos[clave] else 'Ninguno',
    } for clave in ('ok', 'bajo', 'agotado')]
