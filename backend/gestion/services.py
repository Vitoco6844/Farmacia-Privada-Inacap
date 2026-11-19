from datetime import datetime
from decimal import Decimal
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from catalogo.models import Producto, EventoCatalogo
from .models import EventoGestion, Trabajador, PrecioProgramado, PoliticaPrecio

ROLES = ('Administrador', 'Vendedor', 'Técnico en Farmacia', 'Químico Farmacéutico')


def precio_vigente(producto, fecha=None):
    fecha = fecha or timezone.localdate()
    if isinstance(fecha, datetime):
        fecha = timezone.localtime(fecha).date() if timezone.is_aware(fecha) else fecha.date()
    programado = PrecioProgramado.objects.filter(producto=producto, desde__lte=fecha).filter(
        Q(hasta__isnull=True) | Q(hasta__gte=fecha)).order_by('-desde', '-pk').first()
    precio = programado.precio if programado else producto.precio
    politica = PoliticaPrecio.objects.filter(producto=producto).first()
    if politica and politica.aplica_cenabast:
        precio = min(precio, politica.precio_maximo)
    return Decimal(precio)


def limite_descuento(producto):
    politica = PoliticaPrecio.objects.filter(producto=producto).first()
    return politica.descuento_maximo if politica else Decimal('0')


def exigir(usuario, permiso):
    if not usuario.is_active or not usuario.has_perm(permiso):
        raise PermissionDenied


@transaction.atomic
def guardar_usuario(actor, usuario, datos, grupos, trabajador, password=''):
    exigir(actor, 'gestion.administrar_usuarios')
    # Bloqueo estable compartido: serializa cambios que podrían retirar el último administrador.
    usuarios = list(get_user_model().objects.select_for_update().order_by('pk'))
    anterior = next((u for u in usuarios if u.pk == usuario.pk), None)
    if usuario.is_superuser or (anterior and anterior.is_superuser):
        raise PermissionDenied('Los superusuarios se gestionan fuera de esta interfaz.')
    grupos = list(grupos)
    if any(g.name not in ROLES for g in grupos):
        raise ValidationError('Solo puedes asignar los cuatro roles de la farmacia.')
    roles = set(g.pk for g in grupos)
    if anterior and actor.pk == anterior.pk:
        if roles != set(anterior.groups.values_list('pk', flat=True)) or not datos.get('is_active', anterior.is_active):
            raise ValidationError('No puedes cambiar tus propios roles ni desactivar tu cuenta.')
    for campo in ('username', 'first_name', 'last_name', 'email', 'is_active'):
        if campo in datos:
            setattr(usuario, campo, datos[campo])
    conserva_admin = usuario.is_active and (
        any(g.permissions.filter(content_type__app_label='gestion', codename='administrar_usuarios').exists() for g in grupos)
        or (anterior and anterior.user_permissions.filter(content_type__app_label='gestion', codename='administrar_usuarios').exists()))
    if anterior and anterior.has_perm('gestion.administrar_usuarios') and not conserva_admin:
        if not any(u.pk != usuario.pk and u.is_active and u.has_perm('gestion.administrar_usuarios') for u in usuarios):
            raise ValidationError('Debe quedar al menos un administrador activo.')
    if password:
        password_validation.validate_password(password, usuario)
        usuario.set_password(password)
    elif not usuario.pk:
        usuario.set_unusable_password()
    usuario.full_clean(exclude=['password'])
    usuario.save()
    usuario.groups.set(grupos)
    if trabajador:
        perfil, _ = Trabajador.objects.get_or_create(usuario=usuario, defaults=trabajador)
        for campo in ('rut', 'telefono'):
            setattr(perfil, campo, trabajador[campo])
        perfil.full_clean()
        perfil.save()
    EventoGestion.objects.create(usuario=actor, accion='Actualizar usuario' if anterior else 'Crear usuario',
        referencia=f'Usuario {usuario.pk}', detalle={'activo': usuario.is_active, 'roles': [g.name for g in grupos]})
    return usuario


@transaction.atomic
def revisar_condicion(actor, producto_id, condicion, motivo):
    exigir(actor, 'gestion.revisar_condicion')
    if not actor.groups.filter(name='Químico Farmacéutico').exists():
        raise PermissionDenied('Se requiere un Químico Farmacéutico habilitado.')
    if condicion not in Producto.Condicion.values or not motivo.strip():
        raise ValidationError('Indica una condición válida y el fundamento profesional.')
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    anterior = producto.condicion
    producto.condicion = condicion
    producto.save(update_fields=['condicion', 'actualizado'])
    EventoCatalogo.objects.create(producto=producto, usuario=actor, accion='editar',
        anterior={'condicion': anterior}, posterior={'condicion': condicion})
    EventoGestion.objects.create(usuario=actor, accion='Revisar condición de venta',
        referencia=f'Producto {producto.pk}', detalle={'anterior': anterior, 'posterior': condicion, 'fundamento': motivo})
    return producto
