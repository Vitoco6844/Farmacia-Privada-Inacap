import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Ubicacion(models.TextChoices):
    BODEGA = 'bodega', 'Bodega'
    VITRINA = 'vitrina', 'Vitrina'


class Lote(models.Model):
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.PROTECT, related_name='lotes')
    codigo = models.CharField('lote', max_length=60)
    vencimiento = models.DateField()
    bloqueado = models.BooleanField(default=False)

    class Meta:
        ordering = ['vencimiento', 'pk']
        constraints = [models.UniqueConstraint(fields=['producto', 'codigo'], name='lote_producto_codigo_unico')]

    def __str__(self):
        return f'{self.producto.codigo} · {self.codigo}'


class Existencia(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name='existencias')
    ubicacion = models.CharField(max_length=10, choices=Ubicacion.choices)
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        permissions = [('exportar_inventario', 'Puede consultar y exportar reportes de inventario')]
        constraints = [
            models.UniqueConstraint(fields=['lote', 'ubicacion'], name='existencia_lote_ubicacion_unica'),
            models.CheckConstraint(condition=models.Q(cantidad__gte=0), name='existencia_no_negativa'),
            models.CheckConstraint(condition=models.Q(ubicacion__in=Ubicacion.values), name='existencia_ubicacion_valida'),
        ]


class Venta(models.Model):
    clave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=14, decimal_places=0)

    class Meta:
        permissions = [('exportar_ventas', 'Puede consultar y exportar reportes de ventas')]
        ordering = ['-fecha', '-pk']
        default_permissions = ('add', 'view')
        constraints = [models.CheckConstraint(condition=models.Q(total__gte=0), name='venta_total_no_negativo')]


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='detalles')
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.PROTECT)
    nombre = models.CharField(max_length=160)
    codigo = models.CharField(max_length=30)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        default_permissions = ()
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='detalle_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gte=0), name='detalle_precio_no_negativo'),
        ]


class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = 'ingreso', 'Ingreso'
        TRASLADO = 'traslado', 'Traslado'
        VENTA = 'venta', 'Venta'

    clave = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    origen = models.CharField(max_length=10, choices=Ubicacion.choices, blank=True)
    destino = models.CharField(max_length=10, choices=Ubicacion.choices, blank=True)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    detalle_venta = models.ForeignKey(DetalleVenta, on_delete=models.PROTECT, null=True, blank=True, related_name='asignaciones')

    class Meta:
        ordering = ['-fecha', '-pk']
        default_permissions = ('view',)
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='movimiento_cantidad_positiva'),
            models.CheckConstraint(condition=(
                models.Q(tipo='ingreso', origen='', destino__in=Ubicacion.values, detalle_venta__isnull=True)
                | (models.Q(tipo='traslado', origen__in=Ubicacion.values, destino__in=Ubicacion.values, detalle_venta__isnull=True) & ~models.Q(origen=models.F('destino')))
                | models.Q(tipo='venta', origen='vitrina', destino='', detalle_venta__isnull=False)
            ), name='movimiento_tipo_coherente'),
        ]


class EventoReporte(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=12, choices=[('ventas', 'Ventas'), ('inventario', 'Inventario'), ('compras', 'Compras')])
    formato = models.CharField(max_length=4, choices=[('pdf', 'PDF'), ('xlsx', 'Excel')])
    filtros = models.JSONField(default=dict)
    filas = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=24, decimal_places=0, null=True, blank=True)

    class Meta:
        default_permissions = ('view',)
        ordering = ['-fecha', '-pk']
