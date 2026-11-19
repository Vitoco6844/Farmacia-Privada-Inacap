from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    class Condicion(models.TextChoices):
        DIRECTA = 'Venta directa', 'Venta directa'
        SIMPLE = 'Receta simple', 'Receta simple'
        RETENIDA = 'Receta retenida', 'Receta retenida'
        VERIFICAR = 'Por verificar', 'Por verificar'

    codigo = models.CharField('código', max_length=30, unique=True,
        validators=[RegexValidator(r'^[A-Z0-9-]+$', 'Usa letras mayúsculas, números y guiones.')])
    barras = models.CharField('código de barras', max_length=14, unique=True,
        validators=[RegexValidator(r'^\d{8,14}$', 'Ingresa entre 8 y 14 dígitos.')])
    nombre = models.CharField(max_length=160)
    presentacion = models.CharField('presentación', max_length=180)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name='categoría')
    condicion = models.CharField('condición de venta', max_length=30, choices=Condicion.choices)
    precio = models.DecimalField('precio en CLP', max_digits=12, decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))])
    activo = models.BooleanField(default=True)
    stock_minimo = models.PositiveIntegerField('stock mínimo de envases', default=10)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['codigo', 'pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gte=0), name='producto_precio_no_negativo'),
            models.CheckConstraint(condition=models.Q(condicion__in=['Venta directa', 'Receta simple', 'Receta retenida', 'Por verificar']), name='producto_condicion_valida'),
        ]

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    @property
    def precio_visible(self):
        return f'{self.precio:,.0f}'.replace(',', '.')

    @property
    def iniciales(self):
        return ''.join(p[0] for p in self.nombre.split()[:2]).upper()


class EventoCatalogo(models.Model):
    """Historial sin interfaz de edición o borrado para usuarios operativos."""
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='eventos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    accion = models.CharField(max_length=20, choices=[('crear', 'Crear'), ('editar', 'Editar'), ('desactivar', 'Desactivar')])
    fecha = models.DateTimeField(auto_now_add=True)
    anterior = models.JSONField(default=dict)
    posterior = models.JSONField(default=dict)

    class Meta:
        ordering = ['-fecha', '-pk']
        default_permissions = ('view',)


class PrecioReferencia(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='referencias')
    precio = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(0)])
    farmacia = models.CharField(max_length=80)
    tipo = models.CharField(max_length=80)
    fuente = models.URLField(max_length=500)
    consultado = models.DateField()
    nota = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-consultado', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['producto', 'fuente', 'consultado'], name='referencia_producto_fuente_fecha'),
            models.CheckConstraint(condition=models.Q(precio__gte=0), name='referencia_precio_no_negativo'),
        ]
