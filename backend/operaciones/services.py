"""Operaciones atómicas. Todos los escritores bloquean usuario y después producto.

El bloqueo del producto serializa consumos incluso si todavía no existe una fila
de existencias. La clave de operación hace idempotentes los reintentos del mismo
usuario; cambiar el contenido de un reintento se rechaza.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from catalogo.models import Producto
from .models import DetalleVenta, Existencia, Lote, Movimiento, Ubicacion, Venta


def _actor(usuario, permiso):
    # NO KEY UPDATE serializa operaciones del actor y permite las referencias FK
    # de auditoría de otras pantallas sin provocar un ciclo de bloqueos.
    actor = get_user_model().objects.select_for_update(no_key=True).get(pk=usuario.pk)
    if not actor.is_active or not actor.has_perm(permiso):
        raise PermissionDenied('No tienes permiso para esta operación.')
    return actor


def _cantidad(cantidad):
    if isinstance(cantidad, bool) or not isinstance(cantidad, int) or not 1 <= cantidad <= 1000000:
        raise ValidationError('La cantidad debe ser un entero entre 1 y 1.000.000.')


def _ubicacion(ubicacion):
    if ubicacion not in Ubicacion.values:
        raise ValidationError('Ubicación inválida.')


def _movimiento_previo(clave, actor, tipo, producto_id, codigo, cantidad, origen, destino):
    previo = Movimiento.objects.select_related('lote').filter(clave=clave).first()
    if previo and (previo.usuario_id != actor.pk or previo.tipo != tipo
            or previo.lote.producto_id != producto_id or previo.lote.codigo != codigo
            or previo.cantidad != cantidad or previo.origen != origen or previo.destino != destino):
        raise ValidationError('La operación ya se utilizó con otros datos. Abre un formulario nuevo.')
    return previo


@transaction.atomic
def registrar_ingreso(*, usuario, producto_id, codigo, vencimiento, ubicacion, cantidad, clave):
    actor = _actor(usuario, 'operaciones.add_lote')
    _cantidad(cantidad)
    _ubicacion(ubicacion)
    codigo = codigo.strip().upper()
    if not codigo or len(codigo) > 60:
        raise ValidationError('Indica un código de lote de hasta 60 caracteres.')
    previo = _movimiento_previo(clave, actor, Movimiento.Tipo.INGRESO, producto_id, codigo, cantidad, '', ubicacion)
    if previo:
        if previo.lote.vencimiento != vencimiento:
            raise ValidationError('El vencimiento no coincide con la operación anterior.')
        return previo
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    if not producto.activo:
        raise ValidationError('No se puede ingresar stock para un producto inactivo.')
    lote, _ = Lote.objects.get_or_create(producto=producto, codigo=codigo, defaults={'vencimiento': vencimiento})
    if lote.vencimiento != vencimiento:
        raise ValidationError('Ese lote ya tiene otro vencimiento. Revisa su identificación.')
    stock, _ = Existencia.objects.get_or_create(lote=lote, ubicacion=ubicacion)
    stock.cantidad += cantidad
    stock.save(update_fields=['cantidad'])
    return Movimiento.objects.create(clave=clave, lote=lote, tipo=Movimiento.Tipo.INGRESO,
        destino=ubicacion, cantidad=cantidad, usuario=actor)


@transaction.atomic
def transferir(*, usuario, lote_id, origen, destino, cantidad, clave):
    actor = _actor(usuario, 'operaciones.change_existencia')
    _cantidad(cantidad)
    _ubicacion(origen)
    _ubicacion(destino)
    if origen == destino:
        raise ValidationError('Origen y destino deben ser diferentes.')
    lote = Lote.objects.get(pk=lote_id)
    previo = _movimiento_previo(clave, actor, Movimiento.Tipo.TRASLADO, lote.producto_id, lote.codigo, cantidad, origen, destino)
    if previo:
        return previo
    producto = Producto.objects.select_for_update().get(pk=lote.producto_id)
    if not producto.activo or lote.bloqueado or lote.vencimiento <= timezone.localdate():
        raise ValidationError('Solo se pueden trasladar lotes vigentes y habilitados de productos activos.')
    stock_origen = Existencia.objects.filter(lote=lote, ubicacion=origen).first()
    if not stock_origen or stock_origen.cantidad < cantidad:
        raise ValidationError('No hay existencias suficientes en el origen.')
    stock_destino, _ = Existencia.objects.get_or_create(lote=lote, ubicacion=destino)
    stock_origen.cantidad -= cantidad
    stock_destino.cantidad += cantidad
    stock_origen.save(update_fields=['cantidad'])
    stock_destino.save(update_fields=['cantidad'])
    return Movimiento.objects.create(clave=clave, lote=lote, tipo=Movimiento.Tipo.TRASLADO,
        origen=origen, destino=destino, cantidad=cantidad, usuario=actor)


@transaction.atomic
def confirmar_venta(*, usuario, producto_id, cantidad, clave):
    actor = _actor(usuario, 'operaciones.add_venta')
    _cantidad(cantidad)
    previa = Venta.objects.filter(clave=clave).first()
    if previa:
        detalle = previa.detalles.get()
        if previa.usuario_id != actor.pk or detalle.producto_id != producto_id or detalle.cantidad != cantidad:
            raise ValidationError('La operación ya se utilizó con otros datos. Abre una venta nueva.')
        return previa
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    if not producto.activo:
        raise ValidationError('El producto está inactivo.')
    if producto.condicion != Producto.Condicion.DIRECTA:
        raise ValidationError('Esta venta rápida solo admite venta directa. Recetas y condiciones pendientes están bloqueadas.')
    if producto.precio * cantidad > 99999999999999:
        raise ValidationError('El importe supera el máximo admitido por una venta rápida.')
    stocks = list(Existencia.objects.select_for_update(of=('self',)).select_related('lote').filter(
        lote__producto=producto, lote__bloqueado=False, lote__vencimiento__gt=timezone.localdate(),
        ubicacion=Ubicacion.VITRINA, cantidad__gt=0,
    ).order_by('lote__vencimiento', 'lote_id'))
    if sum(stock.cantidad for stock in stocks) < cantidad:
        raise ValidationError('Stock disponible insuficiente en vitrina. Revisa los lotes o registra un traslado.')
    venta = Venta.objects.create(clave=clave, usuario=actor, total=producto.precio * cantidad)
    detalle = DetalleVenta.objects.create(venta=venta, producto=producto, codigo=producto.codigo,
        nombre=producto.nombre, precio_unitario=producto.precio, cantidad=cantidad)
    pendiente = cantidad
    for stock in stocks:
        tomar = min(stock.cantidad, pendiente)
        stock.cantidad -= tomar
        stock.save(update_fields=['cantidad'])
        Movimiento.objects.create(lote=stock.lote, tipo=Movimiento.Tipo.VENTA, origen=Ubicacion.VITRINA,
            cantidad=tomar, usuario=actor, detalle_venta=detalle)
        pendiente -= tomar
        if not pendiente:
            break
    return venta
