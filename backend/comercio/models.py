from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

class Caja(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    apertura = models.DateTimeField(auto_now_add=True)
    cierre = models.DateTimeField(null=True, blank=True)
    fondo = models.DecimalField(max_digits=14, decimal_places=0)
    contado = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    esperado_cierre = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)
    motivo_diferencia = models.TextField(blank=True)
    class Meta:
        permissions = [('operar_caja', 'Puede abrir, mover y cerrar su caja')]
        constraints = [models.UniqueConstraint(fields=['usuario'], condition=models.Q(cierre__isnull=True), name='caja_abierta_por_usuario'), models.CheckConstraint(condition=models.Q(fondo__gte=0), name='caja_fondo_positivo')]

class MovimientoCaja(models.Model):
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='movimientos')
    clave = models.UUIDField(unique=True)
    tipo = models.CharField(max_length=10, choices=[('ingreso','Ingreso'),('retiro','Retiro')])
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    motivo = models.CharField(max_length=250)
    fecha = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(monto__gt=0), name='movimiento_caja_positivo')]

class Convenio(models.Model):
    nombre = models.CharField(max_length=120)
    inicio = models.DateField()
    fin = models.DateField()
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0),MaxValueValidator(100)])
    tope = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True, validators=[MinValueValidator(0)])
    activo = models.BooleanField(default=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(fin__gte=models.F('inicio')), name='convenio_fechas_validas'), models.CheckConstraint(condition=models.Q(porcentaje__gte=0,porcentaje__lte=100), name='convenio_porcentaje_valido')]
    def __str__(self): return self.nombre

class Cobro(models.Model):
    venta = models.OneToOneField('operaciones.Venta', on_delete=models.PROTECT, related_name='cobro')
    caja = models.ForeignKey(Caja, on_delete=models.PROTECT, related_name='cobros')
    solicitud = models.JSONField()
    bruto = models.DecimalField(max_digits=14, decimal_places=0)
    descuento = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    beneficio = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    convenio = models.ForeignKey(Convenio, on_delete=models.PROTECT, null=True, blank=True)
    convenio_nombre = models.CharField(max_length=120, blank=True)
    medio = models.CharField(max_length=15, choices=[('efectivo','Efectivo'),('tarjeta','Tarjeta'),('transferencia','Transferencia')])

class Documento(models.Model):
    venta = models.OneToOneField('operaciones.Venta', on_delete=models.PROTECT, related_name='documento')
    tipo = models.CharField(max_length=10, choices=[('boleta','Boleta'),('factura','Factura')])
    receptor = models.CharField(max_length=160, blank=True)
    rut = models.CharField(max_length=20, blank=True)
    estado = models.CharField(max_length=10, default='pendiente', choices=[('pendiente','Pendiente'),('emitido','Emitido'),('error','Error')])
    intentos = models.PositiveIntegerField(default=0)
    emitido = models.DateTimeField(null=True, blank=True)
    error = models.CharField(max_length=250, blank=True)
    class Meta:
        permissions = [('emitir_documento','Puede emitir documentos académicos')]
    @property
    def folio(self): return f'SIM-{self.tipo.upper()}-{self.pk:08d}'

class EventoComercial(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    accion = models.CharField(max_length=60)
    referencia = models.CharField(max_length=120)
    detalle = models.JSONField(default=dict)
    class Meta:
        default_permissions = ('view',)
        ordering = ['-fecha', '-pk']
