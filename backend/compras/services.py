import hashlib
import json
import uuid
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from catalogo.models import Producto
from operaciones.models import Lote, Ubicacion
from operaciones.services import registrar_ingreso
from .models import DetalleRecepcion, EventoCompra, LineaOrden, OrdenCompra, Proveedor, Recepcion


def _actor(usuario, permiso):
    actor = get_user_model().objects.select_for_update(no_key=True).get(pk=usuario.pk)
    if not actor.is_active or not actor.has_perm(permiso):
        raise PermissionDenied
    return actor


def _cantidad(valor):
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 1000000:
        raise ValidationError('La cantidad debe ser un entero entre 1 y 1.000.000 envases.')


def _huella(datos):
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@transaction.atomic
def crear_orden(*, usuario, proveedor_id, lineas, observaciones, clave):
    actor = _actor(usuario, 'compras.add_ordencompra')
    if not 1 <= len(lineas) <= 20:
        raise ValidationError('La orden debe contener entre 1 y 20 productos.')
    datos = []
    vistos = set()
    for linea in lineas:
        _cantidad(linea['cantidad'])
        try:
            costo = Decimal(str(linea['costo_unitario']))
            if not costo.is_finite() or costo != costo.to_integral_value() or not 0 <= costo <= 999999999999:
                raise InvalidOperation
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError('El costo debe ser un importe CLP entero no negativo de hasta 12 dígitos.')
        producto_id = linea['producto_id']
        if producto_id in vistos:
            raise ValidationError('No repitas un producto en la orden.')
        vistos.add(producto_id)
        datos.append({'producto_id': producto_id, 'cantidad': linea['cantidad'], 'costo_unitario': str(costo.quantize(Decimal('1')))})
    datos.sort(key=lambda d: d['producto_id'])
    observaciones = observaciones.strip()
    if len(observaciones) > 300:
        raise ValidationError('Las observaciones admiten hasta 300 caracteres.')
    huella = _huella({'proveedor': proveedor_id, 'lineas': datos, 'observaciones': observaciones})
    previa = OrdenCompra.objects.filter(clave=clave).first()
    if previa:
        if previa.usuario_id != actor.pk or previa.huella != huella:
            raise ValidationError('La clave de esta orden ya se utilizó con otros datos.')
        return previa
    proveedor = Proveedor.objects.select_for_update(no_key=True).get(pk=proveedor_id)
    if not proveedor.activo:
        raise ValidationError('El proveedor está inactivo para nuevas órdenes.')
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=vistos).order_by('pk')}
    if len(productos) != len(vistos) or any(not p.activo for p in productos.values()):
        raise ValidationError('Todos los productos de la orden deben existir y estar activos.')
    total = sum((Decimal(d['costo_unitario']) * d['cantidad'] for d in datos), Decimal('0'))
    orden = OrdenCompra.objects.create(clave=clave, huella=huella, proveedor=proveedor,
        proveedor_nombre=proveedor.nombre, usuario=actor, observaciones=observaciones, total=total)
    for d in datos:
        p = productos[d['producto_id']]
        LineaOrden.objects.create(orden=orden, producto=p, codigo=p.codigo, nombre=p.nombre,
            presentacion=p.presentacion, solicitada=d['cantidad'], costo_unitario=d['costo_unitario'])
    EventoCompra.objects.create(orden=orden, usuario=actor, accion='crear')
    return orden


@transaction.atomic
def recibir_orden(*, usuario, orden_id, referencia, partidas, clave):
    actor = _actor(usuario, 'compras.add_recepcion')
    if not actor.has_perm('operaciones.add_lote'):
        raise PermissionDenied
    if not 1 <= len(partidas) <= 30:
        raise ValidationError('La recepción debe contener entre 1 y 30 partidas.')
    referencia = referencia.strip().upper()
    if not referencia or len(referencia) > 60:
        raise ValidationError('Indica una referencia de entrega de hasta 60 caracteres.')
    datos, vistos = [], set()
    for p in partidas:
        _cantidad(p['cantidad'])
        codigo = p['codigo'].strip().upper()
        vencimiento = p['vencimiento']
        if not codigo or len(codigo) > 60 or p['ubicacion'] not in Ubicacion.values:
            raise ValidationError('Revisa lote y ubicación de cada partida.')
        if not isinstance(vencimiento, date) or isinstance(vencimiento, datetime):
            raise ValidationError('El vencimiento debe ser una fecha válida.')
        identificador = (p['linea_id'], codigo, vencimiento.isoformat(), p['ubicacion'])
        if identificador in vistos:
            raise ValidationError('Combina las cantidades de las partidas con el mismo producto, lote y ubicación.')
        vistos.add(identificador)
        datos.append({'linea_id': p['linea_id'], 'codigo': codigo, 'vencimiento': vencimiento.isoformat(),
            'ubicacion': p['ubicacion'], 'cantidad': p['cantidad']})
    datos.sort(key=lambda d: (d['linea_id'], d['codigo'], d['vencimiento'], d['ubicacion']))
    huella = _huella({'orden': orden_id, 'referencia': referencia, 'partidas': datos})
    previa = Recepcion.objects.filter(clave=clave).first()
    if previa:
        if previa.usuario_id != actor.pk or previa.huella != huella:
            raise ValidationError('La clave de esta recepción ya se utilizó con otros datos.')
        return previa
    orden = OrdenCompra.objects.select_for_update().get(pk=orden_id)
    if orden.estado not in (OrdenCompra.Estado.PENDIENTE, OrdenCompra.Estado.PARCIAL):
        raise ValidationError('Solo se pueden recibir órdenes pendientes o parciales.')
    if orden.recepciones.filter(referencia=referencia).exists():
        raise ValidationError('Esta referencia ya fue registrada para la orden. Revisa el historial de recepciones.')
    lineas = {l.pk: l for l in orden.lineas.select_for_update().order_by('pk')}
    cantidades = Counter()
    for d in datos:
        if d['linea_id'] not in lineas:
            raise ValidationError('Una de las líneas no pertenece a esta orden.')
        cantidades[d['linea_id']] += d['cantidad']
        if date.fromisoformat(d['vencimiento']) <= timezone.localdate():
            raise ValidationError('No se reciben compras con lotes vencidos o que vencen hoy.')
    for linea_id, cantidad in cantidades.items():
        if cantidad > lineas[linea_id].pendiente:
            raise ValidationError(f'La cantidad de {lineas[linea_id].nombre} supera lo pendiente de recibir.')
    productos_ids = sorted({lineas[k].producto_id for k in cantidades})
    productos = list(Producto.objects.select_for_update().filter(pk__in=productos_ids).order_by('pk'))
    if any(not p.activo for p in productos):
        raise ValidationError('No se puede recibir un producto inactivo.')
    for d in datos:
        if Lote.objects.filter(producto_id=lineas[d['linea_id']].producto_id, codigo=d['codigo'], bloqueado=True).exists():
            raise ValidationError('No se puede recibir una compra en un lote bloqueado.')
    recepcion = Recepcion.objects.create(clave=clave, huella=huella, orden=orden, referencia=referencia, usuario=actor)
    for indice, d in enumerate(datos):
        linea = lineas[d['linea_id']]
        movimiento = registrar_ingreso(usuario=actor, producto_id=linea.producto_id, codigo=d['codigo'],
            vencimiento=date.fromisoformat(d['vencimiento']), ubicacion=d['ubicacion'], cantidad=d['cantidad'],
            clave=uuid.uuid5(clave, str(indice)))
        DetalleRecepcion.objects.create(recepcion=recepcion, linea=linea, movimiento=movimiento)
    for linea_id, cantidad in cantidades.items():
        linea = lineas[linea_id]
        linea.recibida += cantidad
        linea.save(update_fields=['recibida'])
    orden.estado = OrdenCompra.Estado.COMPLETA if all(l.pendiente == 0 for l in lineas.values()) else OrdenCompra.Estado.PARCIAL
    orden.save(update_fields=['estado'])
    return recepcion


@transaction.atomic
def anular_orden(*, usuario, orden_id, motivo):
    actor = _actor(usuario, 'compras.anular_ordencompra')
    orden = OrdenCompra.objects.select_for_update().get(pk=orden_id)
    if orden.estado == OrdenCompra.Estado.ANULADA:
        return orden
    if orden.estado != OrdenCompra.Estado.PENDIENTE or orden.recepciones.exists():
        raise ValidationError('Una orden con recepciones no puede anularse en este prototipo.')
    motivo = motivo.strip()
    if not 10 <= len(motivo) <= 300:
        raise ValidationError('Indica un motivo de entre 10 y 300 caracteres.')
    orden.estado = OrdenCompra.Estado.ANULADA
    orden.save(update_fields=['estado'])
    EventoCompra.objects.create(orden=orden, usuario=actor, accion='anular', motivo=motivo)
    return orden
