from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Trabajador(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='trabajador')
    rut = models.CharField('RUT', max_length=12, unique=True)
    telefono = models.CharField('teléfono', max_length=30)


class EventoGestion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=100)
    referencia = models.CharField(max_length=120)
    detalle = models.JSONField(default=dict)

    class Meta:
        default_permissions = ('view',)
        ordering = ['-fecha', '-pk']
        permissions = [
            ('administrar_usuarios', 'Administrar trabajadores y roles'),
            ('administrar_precios', 'Administrar precios y límites comerciales'),
            ('configurar_alertas', 'Configurar alertas por ubicación'),
            ('ver_auditoria', 'Consultar auditoría unificada'),
            ('revisar_condicion', 'Revisar profesionalmente condición de venta'),
        ]


class PoliticaPrecio(models.Model):
    producto = models.OneToOneField('catalogo.Producto', on_delete=models.PROTECT, related_name='politica_precio')
    aplica_cenabast = models.BooleanField('Aplica Cenabast', default=False)
    precio_maximo = models.DecimalField('Precio máximo Cenabast CLP', max_digits=12, decimal_places=0,
        null=True, blank=True, validators=[MinValueValidator(0)])
    descuento_maximo = models.DecimalField('Descuento máximo (%)', max_digits=5, decimal_places=2,
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    fuente = models.CharField('Fuente del límite', max_length=300)

    def clean(self):
        if self.aplica_cenabast and self.precio_maximo is None:
            raise ValidationError({'precio_maximo': 'Indica el precio máximo aplicable.'})

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(descuento_maximo__gte=0, descuento_maximo__lte=100), name='gestion_descuento_rango'),
            models.CheckConstraint(condition=models.Q(precio_maximo__isnull=True) | models.Q(precio_maximo__gte=0), name='gestion_cap_no_negativo'),
            models.CheckConstraint(condition=models.Q(aplica_cenabast=False) | models.Q(precio_maximo__isnull=False), name='gestion_cenabast_cap'),
        ]


class PrecioProgramado(models.Model):
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.PROTECT, related_name='precios_programados')
    precio = models.DecimalField('Precio CLP', max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    desde = models.DateField('Vigente desde')
    hasta = models.DateField('Vigente hasta (inclusive)', null=True, blank=True)
    fuente = models.CharField(max_length=300)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.hasta and self.desde and self.hasta < self.desde:
            raise ValidationError({'hasta': 'La fecha final no puede preceder al inicio.'})

    class Meta:
        ordering = ['-desde', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gte=0), name='gestion_precio_no_negativo'),
            models.CheckConstraint(condition=models.Q(hasta__isnull=True) | models.Q(hasta__gte=models.F('desde')), name='gestion_vigencia_orden'),
        ]


class ConfiguracionAlerta(models.Model):
    producto = models.ForeignKey('catalogo.Producto', on_delete=models.PROTECT)
    ubicacion = models.CharField('Ubicación', max_length=12, choices=[('bodega', 'Bodega'), ('vitrina', 'Vitrina')])
    stock_minimo = models.PositiveIntegerField('Umbral de stock')
    dias_vencimiento = models.PositiveIntegerField('Avisar vencimientos dentro de (días)', default=90)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['producto', 'ubicacion'], name='gestion_alerta_producto_ubicacion')]
