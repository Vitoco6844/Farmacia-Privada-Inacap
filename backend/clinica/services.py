import hashlib
from pathlib import Path
from io import BytesIO
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import *

def exigir_qf(usuario, permiso):
    if not usuario.is_active or not usuario.groups.filter(name='Químico Farmacéutico').exists() or not usuario.has_perm('clinica.'+permiso):
        raise ValidationError('Se requiere un Químico Farmacéutico habilitado con el permiso correspondiente.')

@transaction.atomic
def revisar_receta(*, usuario, receta, aprobar, nota=''):
    exigir_qf(usuario,'revisar_receta')
    receta=Receta.objects.select_for_update().get(pk=receta.pk)
    # Una decisión profesional no se sobrescribe sin control: solo se aprueba lo pendiente, el rechazo es
    # definitivo y revocar una aprobación (p. ej. por error detectado) exige dejar el motivo registrado.
    if receta.estado=='rechazada':
        raise ValidationError('La receta ya fue rechazada; si corresponde, registra una receta nueva.')
    if aprobar and receta.estado!='pendiente':
        raise ValidationError('La receta ya está aprobada.')
    if not aprobar and receta.estado=='aprobada' and not nota.strip():
        raise ValidationError('Para revocar una receta aprobada indica el motivo en Observaciones.')
    if aprobar and (not receta.lineas.exists() or receta.emitida > timezone.localdate() or receta.vence < timezone.localdate()):
        raise ValidationError('La receta debe tener productos y estar vigente.')
    receta.estado='aprobada' if aprobar else 'rechazada'
    receta.revisada_por=usuario; receta.revisada_el=timezone.now(); receta.nota_revision=nota
    receta.save()
    EventoClinico.objects.create(receta=receta,usuario=usuario,accion='revision',detalle={'estado':receta.estado,'nota':nota})
    return receta

@transaction.atomic
def autorizar_controlado(*, usuario, receta, producto, cantidad):
    exigir_qf(usuario,'autorizar_controlado')
    receta=Receta.objects.select_for_update().get(pk=receta.pk)
    linea=receta.lineas.filter(producto=producto).first()
    if receta.estado!='aprobada' or not linea or producto.condicion!='Receta retenida' or type(cantidad) is not int or cantidad <= 0 or linea.sin_limite or cantidad > linea.saldo:
        raise ValidationError('Revisa el estado, producto y saldo de la receta antes de autorizar.')
    return AutorizacionControlado.objects.create(receta=receta,producto=producto,cantidad=cantidad,profesional=usuario)

@transaction.atomic
def procesar_entrega(*, usuario, receta_id, items, venta, retirante_id=None, autorizacion_retiro=''):
    if not usuario.is_active or not usuario.has_perm('operaciones.add_venta'):
        raise ValidationError('No tienes permiso para entregar medicamentos.')
    try: receta=Receta.objects.select_for_update().select_related('paciente','prescriptor').get(pk=receta_id)
    except Receta.DoesNotExist: raise ValidationError('Receta inexistente.')
    if Entrega.objects.filter(venta=venta).exists(): raise ValidationError('Esta venta ya tiene una entrega registrada.')
    if receta.estado!='aprobada' or not receta.emitida <= timezone.localdate() <= receta.vence or not receta.paciente.activo or not receta.prescriptor.activo:
        raise ValidationError('La receta no está aprobada, vigente o sus participantes están inactivos.')
    try: retirante=Paciente.objects.get(pk=retirante_id or receta.paciente_id,activo=True)
    except Paciente.DoesNotExist: raise ValidationError('Identifica a la persona que retira con un registro activo.')
    if retirante.pk!=receta.paciente_id and not autorizacion_retiro.strip(): raise ValidationError('Registra relación y autorización del paciente para el retiro por tercero.')
    if not items: raise ValidationError('La entrega debe contener productos.')
    acumulado={}
    for item in items:
        cantidad=item.get('cantidad'); producto_id=item.get('producto_id')
        if type(cantidad) is not int or cantidad <= 0 or type(producto_id) is not int: raise ValidationError('Las cantidades deben ser enteros positivos.')
        acumulado[producto_id]=acumulado.get(producto_id,0)+cantidad
    lineas={l.producto_id:l for l in LineaReceta.objects.select_for_update().filter(receta=receta).select_related('producto').order_by('producto_id')}
    preparadas=[]
    for producto_id,cantidad in sorted(acumulado.items()):
        linea=lineas.get(producto_id)
        if not linea or not linea.producto.activo: raise ValidationError('Producto no prescrito o inactivo.')
        if not linea.sin_limite and cantidad > linea.saldo: raise ValidationError('La cantidad supera el saldo de la receta.')
        autorizacion=None
        if linea.producto.condicion=='Receta retenida':
            if linea.sin_limite: raise ValidationError('Un controlado requiere saldo explícito.')
            autorizacion=AutorizacionControlado.objects.select_for_update().filter(receta=receta,producto_id=producto_id,cantidad=cantidad,entrega__isnull=True,fecha__date=timezone.localdate()).order_by('pk').first()
            if not autorizacion: raise ValidationError('Falta autorización QF de hoy para este producto y cantidad exacta.')
            exigir_qf(autorizacion.profesional,'autorizar_controlado')
        preparadas.append((linea,cantidad,autorizacion))
    snapshot={'paciente':str(receta.paciente),'prescriptor':str(receta.prescriptor),'retirante':str(retirante),'emitida':str(receta.emitida),'vence':str(receta.vence),'usuario':usuario.get_username(),'productos':[{'codigo':l.producto.codigo,'nombre':l.producto.nombre,'cantidad':c} for l,c,a in preparadas]}
    entrega=Entrega.objects.create(receta=receta,venta=venta,usuario=usuario,retirante=retirante,autorizacion_retiro=autorizacion_retiro,instantanea=snapshot)
    for linea,cantidad,autorizacion in preparadas:
        linea.entregada+=cantidad; linea.save(update_fields=['entregada'])
        DetalleEntrega.objects.create(entrega=entrega,linea_receta=linea,cantidad=cantidad)
        if autorizacion:
            autorizacion.entrega=entrega; autorizacion.save(update_fields=['entrega'])
            AsientoControlado.objects.create(entrega=entrega,producto=linea.producto,cantidad=cantidad,profesional=autorizacion.profesional)
    return entrega

@transaction.atomic
def compensar_asiento(*, usuario, asiento_id, motivo):
    exigir_qf(usuario,'autorizar_controlado')
    asiento=AsientoControlado.objects.select_for_update().get(pk=asiento_id)
    if not motivo.strip() or asiento.compensa_id or AsientoControlado.objects.filter(compensa=asiento).exists(): raise ValidationError('Indica motivo; un asiento original solo admite una compensación.')
    # Book correction does not reverse the physical delivery, sale or prescription balance.
    return AsientoControlado.objects.create(entrega=asiento.entrega,producto=asiento.producto,cantidad=-asiento.cantidad,profesional=usuario,compensa=asiento,motivo=motivo)

def subir_adjunto(*,usuario,receta,archivo):
    if not usuario.has_perm('clinica.gestionar_clinica'): raise ValidationError('Sin permiso para adjuntar archivos.')
    if archivo.size > 10*1024*1024: raise ValidationError('El máximo permitido es 10 MB.')
    contenido=archivo.read(10*1024*1024+1)
    if len(contenido)>10*1024*1024: raise ValidationError('El máximo permitido es 10 MB.')
    extension=Path(archivo.name).suffix.lower()
    if extension=='.pdf' and contenido.startswith(b'%PDF-') and b'%%EOF' in contenido[-2048:]: tipo='application/pdf'
    elif extension in ('.jpg','.jpeg','.png'):
        try:
            from PIL import Image
            imagen=Image.open(BytesIO(contenido)); formato=imagen.format; imagen.verify()
            if formato not in ('JPEG','PNG') or (extension=='.png')!=(formato=='PNG'): raise ValueError()
            tipo='image/png' if formato=='PNG' else 'image/jpeg'
        except Exception: raise ValidationError('La imagen no es un JPG/PNG válido.')
    else: raise ValidationError('Solo se permiten PDF, JPG o PNG con contenido válido.')
    archivo.seek(0)
    return AdjuntoReceta.objects.create(receta=receta,archivo=archivo,nombre=Path(archivo.name).name[:200],tipo=tipo,sha256=hashlib.sha256(contenido).hexdigest(),usuario=usuario)
