from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from operaciones.services import _actor, _cantidad
from operaciones.models import Venta, DetalleVenta, Movimiento, Existencia, Ubicacion
from catalogo.models import Producto
from .models import Caja, MovimientoCaja, Convenio, Cobro, Documento, EventoComercial


def pesos(valor):
    try: valor = Decimal(str(valor))
    except (InvalidOperation, ValueError): raise ValidationError('Importe inválido.')
    if not valor.is_finite() or valor < 0 or valor > 99999999999999 or valor != valor.to_integral_value():
        raise ValidationError('El importe debe ser un entero CLP positivo o cero.')
    return valor


def resumen_caja(caja):
    pagos = {m: sum((c.venta.total for c in caja.cobros.select_related('venta').filter(medio=m)), Decimal(0)) for m in ['efectivo','tarjeta','transferencia']}
    ingresos = sum((m.monto for m in caja.movimientos.filter(tipo='ingreso')), Decimal(0))
    retiros = sum((m.monto for m in caja.movimientos.filter(tipo='retiro')), Decimal(0))
    return dict(pagos, ingresos=ingresos, retiros=retiros, esperado=caja.fondo + pagos['efectivo'] + ingresos - retiros)


def _caja(actor, caja_id):
    caja = Caja.objects.select_for_update().get(pk=caja_id)
    if caja.usuario_id != actor.pk: raise PermissionDenied('Solo puedes operar tu propia caja.')
    return caja


@transaction.atomic
def abrir_caja(*, usuario, fondo):
    actor = _actor(usuario, 'comercio.operar_caja')
    fondo = pesos(fondo)
    if Caja.objects.filter(usuario=actor, cierre__isnull=True).exists(): raise ValidationError('Ya tienes una caja abierta.')
    return Caja.objects.create(usuario=actor, fondo=fondo)


@transaction.atomic
def mover_caja(*, usuario, caja_id, tipo, monto, motivo, clave):
    actor = _actor(usuario, 'comercio.operar_caja')
    caja = _caja(actor, caja_id)
    monto = pesos(monto)
    motivo = motivo.strip()
    previo = MovimientoCaja.objects.filter(clave=clave).first()
    if previo:
        if (previo.caja_id, previo.tipo, previo.monto, previo.motivo) != (caja.pk, tipo, monto, motivo): raise ValidationError('Clave utilizada con otros datos.')
        return previo
    if caja.cierre: raise ValidationError('La caja está cerrada.')
    if tipo not in ['ingreso','retiro'] or monto <= 0 or not motivo or len(motivo)>250: raise ValidationError('Indica tipo, monto positivo y motivo de hasta 250 caracteres.')
    if tipo == 'retiro' and monto > resumen_caja(caja)['esperado']: raise ValidationError('El retiro supera el efectivo disponible.')
    return MovimientoCaja.objects.create(caja=caja,tipo=tipo,monto=monto,motivo=motivo,clave=clave)


@transaction.atomic
def cerrar_caja(*, usuario, caja_id, contado, motivo=''):
    actor = _actor(usuario, 'comercio.operar_caja')
    caja = _caja(actor, caja_id)
    contado = pesos(contado)
    motivo = motivo.strip()
    if caja.cierre:
        if caja.contado != contado or caja.motivo_diferencia != motivo: raise ValidationError('La caja ya se cerró con otros datos.')
        return caja
    esperado = resumen_caja(caja)['esperado']
    if contado != esperado and not motivo: raise ValidationError('Explica la diferencia entre efectivo esperado y contado.')
    caja.contado, caja.esperado_cierre, caja.motivo_diferencia, caja.cierre = contado, esperado, motivo, timezone.now()
    caja.save()
    return caja


@transaction.atomic
def confirmar_venta(*, usuario, items, clave, caja_id, medio='efectivo', convenio_id=None, descuento=0, receta_id=None, retirante_id=None, autorizacion_retiro='', tipo_documento='boleta', receptor='', rut=''):
    actor = _actor(usuario, 'operaciones.add_venta')
    if not isinstance(items,list) or not 1 <= len(items) <= 100: raise ValidationError('Agrega entre 1 y 100 productos.')
    normal = {}
    for item in items:
        if not isinstance(item, dict): raise ValidationError('Cada producto debe incluir identificador y cantidad.')
        cantidad = item.get('cantidad')
        _cantidad(cantidad)
        pid = item.get('producto_id')
        if isinstance(pid,bool) or not isinstance(pid,int) or pid <= 0: raise ValidationError('Producto inválido.')
        normal[pid] = normal.get(pid,0) + cantidad
        _cantidad(normal[pid])
    items = [dict(producto_id=p,cantidad=q) for p,q in sorted(normal.items())]
    try: descuento = Decimal(str(descuento))
    except InvalidOperation: raise ValidationError('Descuento inválido.')
    if not descuento.is_finite() or not 0 <= descuento <= 100: raise ValidationError('Descuento fuera de rango.')
    if medio not in ['efectivo','tarjeta','transferencia']: raise ValidationError('Medio de pago inválido.')
    if tipo_documento not in ['boleta','factura']: raise ValidationError('Tipo de documento inválido.')
    receptor, rut = receptor.strip(), rut.strip()
    if len(receptor)>160 or len(rut)>20: raise ValidationError('Datos de receptor demasiado largos.')
    if tipo_documento == 'factura' and (not receptor or not rut): raise ValidationError('La factura requiere razón social y RUT.')
    if rut:
        from config.rut import normalizar_rut
        try: rut = normalizar_rut(rut)
        except ValidationError as error: raise ValidationError(f'RUT del receptor: {error.messages[0]}')
    solicitud = dict(items=items,caja_id=int(caja_id),medio=medio,convenio_id=convenio_id,descuento=str(descuento.normalize()),receta_id=receta_id,retirante_id=retirante_id,autorizacion_retiro=autorizacion_retiro,tipo_documento=tipo_documento,receptor=receptor,rut=rut)
    previa = Venta.objects.filter(clave=clave).first()
    if previa:
        cobro = Cobro.objects.filter(venta=previa).first()
        if previa.usuario_id != actor.pk or not cobro or cobro.solicitud != solicitud: raise ValidationError('La clave ya corresponde a otra operación.')
        return previa
    caja = _caja(actor, caja_id)
    if caja.cierre: raise ValidationError('Abre una caja para vender.')
    from gestion.services import precio_vigente, limite_descuento
    productos = {p.pk:p for p in Producto.objects.select_for_update().filter(pk__in=normal).order_by('pk')}
    if len(productos) != len(normal): raise ValidationError('Algún producto no existe.')
    precios, stocks = {}, {}
    for pid, cantidad in normal.items():
        producto = productos[pid]
        if not producto.activo or producto.condicion == Producto.Condicion.VERIFICAR: raise ValidationError(f'{producto.nombre}: producto inactivo o condición sin verificar.')
        if descuento > limite_descuento(producto): raise ValidationError(f'{producto.nombre}: descuento superior al autorizado.')
        precios[pid] = precio_vigente(producto)
        stocks[pid] = list(Existencia.objects.select_for_update(of=('self',)).select_related('lote').filter(lote__producto=producto,lote__bloqueado=False,lote__vencimiento__gt=timezone.localdate(),ubicacion=Ubicacion.VITRINA,cantidad__gt=0).order_by('lote__vencimiento','lote_id'))
        if sum(s.cantidad for s in stocks[pid]) < cantidad: raise ValidationError(f'{producto.nombre}: stock vigente insuficiente en vitrina.')
    bruto = sum(precios[p]*q for p,q in normal.items())
    rebaja = (bruto * descuento / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    convenio, beneficio = None, Decimal(0)
    if convenio_id:
        if descuento: raise ValidationError('El convenio no se acumula con descuentos manuales.')
        convenio = Convenio.objects.select_for_update().get(pk=convenio_id)
        if not convenio.activo or not convenio.inicio <= timezone.localdate() <= convenio.fin: raise ValidationError('El convenio no está vigente.')
        beneficio = (bruto*convenio.porcentaje/100).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        if convenio.tope is not None: beneficio=min(beneficio,convenio.tope)
    total=pesos(bruto-rebaja-beneficio)
    venta=Venta.objects.create(clave=clave,usuario=actor,total=total)
    requeridos=[i for i in items if productos[i['producto_id']].condicion != Producto.Condicion.DIRECTA]
    if requeridos:
        if not receta_id: raise ValidationError('Selecciona una receta validada para estos productos.')
        from clinica.services import procesar_entrega
        procesar_entrega(usuario=actor,receta_id=receta_id,items=requeridos,venta=venta,retirante_id=retirante_id,autorizacion_retiro=autorizacion_retiro)
    for pid,cantidad in normal.items():
        p=productos[pid]
        detalle=DetalleVenta.objects.create(venta=venta,producto=p,nombre=p.nombre,codigo=p.codigo,precio_unitario=precios[pid],cantidad=cantidad)
        pendiente=cantidad
        for stock in stocks[pid]:
            tomar=min(stock.cantidad,pendiente)
            stock.cantidad-=tomar
            stock.save(update_fields=['cantidad'])
            Movimiento.objects.create(lote=stock.lote,tipo=Movimiento.Tipo.VENTA,origen=Ubicacion.VITRINA,cantidad=tomar,usuario=actor,detalle_venta=detalle)
            pendiente-=tomar
            if not pendiente: break
    Cobro.objects.create(venta=venta,caja=caja,solicitud=solicitud,bruto=bruto,descuento=rebaja,beneficio=beneficio,convenio=convenio,convenio_nombre=convenio.nombre if convenio else '',medio=medio)
    Documento.objects.create(venta=venta,tipo=tipo_documento,receptor=receptor,rut=rut)
    return venta


@transaction.atomic
def emitir_documento(*, usuario, documento_id, simular_error=False):
    actor = _actor(usuario,'comercio.emitir_documento')
    documento = Documento.objects.select_for_update().get(pk=documento_id)
    if documento.estado == 'emitido': return documento
    documento.intentos += 1
    documento.estado = 'error' if simular_error else 'emitido'
    documento.error = 'Fallo simulado: reintenta la emisión sin repetir la venta.' if simular_error else ''
    documento.emitido = None if simular_error else timezone.now()
    documento.save()
    EventoComercial.objects.create(usuario=actor,accion='Emisión académica',referencia=f'Documento {documento.pk}',detalle={'estado':documento.estado,'intento':documento.intentos})
    return documento


@transaction.atomic
def guardar_convenio(*, usuario, datos, convenio_id=None):
    actor=_actor(usuario,'comercio.change_convenio' if convenio_id else 'comercio.add_convenio')
    convenio=Convenio.objects.select_for_update().get(pk=convenio_id) if convenio_id else Convenio()
    campos=['nombre','inicio','fin','porcentaje','tope','activo']
    anterior={k:str(getattr(convenio,k)) for k in campos} if convenio.pk else {}
    for campo in campos: setattr(convenio,campo,datos[campo])
    convenio.full_clean()
    convenio.save()
    EventoComercial.objects.create(usuario=actor,accion='Actualizar convenio' if convenio_id else 'Crear convenio',referencia=f'Convenio {convenio.pk}',detalle={'anterior':anterior,'posterior':{k:str(getattr(convenio,k)) for k in campos}})
    return convenio
