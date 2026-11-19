import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Proveedor(models.Model):
    codigo = models.CharField('código interno', max_length=30, unique=True)
    nombre = models.CharField(max_length=160)
    email = models.EmailField('correo', blank=True)
    telefono = models.CharField('teléfono', max_length=30, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre', 'pk']
        default_permissions = ('add', 'change', 'view')

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'


class OrdenCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PARCIAL = 'parcial', 'Recepción parcial'
        COMPLETA = 'completa', 'Recibida completa'
        ANULADA = 'anulada', 'Anulada'

    clave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    huella = models.CharField(max_length=64)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    proveedor_nombre = models.CharField(max_length=160)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.CharField(max_length=300, blank=True)
    total = models.DecimalField(max_digits=24, decimal_places=0)

    class Meta:
        ordering = ['-fecha', '-pk']
        default_permissions = ('add', 'view')
        permissions = [('anular_ordencompra', 'Puede anular órdenes sin recepciones'), ('exportar_compras', 'Puede exportar compras')]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name='orden_total_no_negativo'),
            models.CheckConstraint(condition=models.Q(estado__in=['pendiente', 'parcial', 'completa', 'anulada']), name='orden_estado_valido'),
        ]


class LineaOrden(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name='lineas')
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.PROTECT)
    codigo = models.CharField(max_length=30)
    nombre = models.CharField(max_length=160)
    presentacion = models.CharField(max_length=180)
    solicitada = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    recibida = models.PositiveIntegerField(default=0)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])

    class Meta:
        default_permissions = ()
        ordering = ['pk']
        constraints = [
            models.UniqueConstraint(fields=['orden', 'producto'], name='orden_producto_unico'),
            models.CheckConstraint(condition=models.Q(solicitada__gt=0), name='orden_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(recibida__gte=0, recibida__lte=models.F('solicitada')), name='orden_recibida_en_rango'),
            models.CheckConstraint(condition=models.Q(costo_unitario__gte=0), name='orden_costo_no_negativo'),
        ]

    @property
    def pendiente(self):
        return self.solicitada - self.recibida

    @property
    def subtotal(self):
        return self.solicitada * self.costo_unitario

    def __str__(self):
        return f'{self.codigo} · {self.nombre} · Pendiente: {self.pendiente}'


class Recepcion(models.Model):
    clave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    huella = models.CharField(max_length=64)
    orden = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name='recepciones')
    referencia = models.CharField('referencia de entrega', max_length=60)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        default_permissions = ('add', 'view')
        constraints = [models.UniqueConstraint(fields=['orden', 'referencia'], name='orden_referencia_recepcion_unica')]


class DetalleRecepcion(models.Model):
    recepcion = models.ForeignKey(Recepcion, on_delete=models.PROTECT, related_name='detalles')
    linea = models.ForeignKey(LineaOrden, on_delete=models.PROTECT, related_name='entregas')
    movimiento = models.OneToOneField('operaciones.Movimiento', on_delete=models.PROTECT, related_name='recepcion_detalle')

    class Meta:
        default_permissions = ()
        ordering = ['pk']


class EventoCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name='eventos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=12, choices=[('crear', 'Crear'), ('anular', 'Anular')])
    motivo = models.CharField(max_length=300, blank=True)

    class Meta:
        default_permissions = ('view',)


class EventoProveedor(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    anterior = models.JSONField(default=dict)
    posterior = models.JSONField(default=dict)

    class Meta:
        default_permissions = ('view',)
