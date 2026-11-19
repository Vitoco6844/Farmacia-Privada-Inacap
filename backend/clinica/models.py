import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.core.exceptions import ValidationError

def private_storage():
    return FileSystemStorage(location=getattr(settings,'PRIVATE_MEDIA_ROOT',settings.BASE_DIR/'private_media'))
def private_path(instance, filename):
    return 'cuarentena/'+uuid.uuid4().hex

class Paciente(models.Model):
    identificador=models.CharField('identificador / documento',max_length=40,unique=True)
    nombre=models.CharField(max_length=160)
    telefono=models.CharField('teléfono',max_length=40,blank=True)
    activo=models.BooleanField(default=True)
    def __str__(self): return f'{self.nombre} · {self.identificador}'

class Prescriptor(models.Model):
    identificador=models.CharField('identificador',max_length=40,unique=True)
    nombre=models.CharField(max_length=160)
    registro=models.CharField('registro profesional',max_length=80)
    activo=models.BooleanField(default=True)
    def __str__(self): return f'{self.nombre} · {self.registro}'

class Receta(models.Model):
    paciente=models.ForeignKey(Paciente,on_delete=models.PROTECT)
    prescriptor=models.ForeignKey(Prescriptor,on_delete=models.PROTECT)
    emitida=models.DateField('fecha de emisión')
    vence=models.DateField('vigencia hasta')
    estado=models.CharField(max_length=15,choices=[('pendiente','Pendiente de revisión'),('aprobada','Aprobada'),('rechazada','Rechazada')],default='pendiente')
    revisada_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,blank=True)
    revisada_el=models.DateTimeField(null=True,blank=True)
    nota_revision=models.TextField(blank=True)
    creada=models.DateTimeField(auto_now_add=True)
    class Meta:
        permissions=[('revisar_receta','Revisar recetas como QF'),('autorizar_controlado','Autorizar entrega de controlados como QF'),('descargar_adjunto','Descargar documentos clínicos privados'),('gestionar_clinica','Gestionar registros clínicos')]
        ordering=['-pk']
    def clean(self):
        if self.vence and self.emitida and self.vence < self.emitida: raise ValidationError('La vigencia no puede preceder la emisión.')
    def __str__(self): return f'Receta {self.pk} · {self.paciente}'

class LineaReceta(models.Model):
    receta=models.ForeignKey(Receta,on_delete=models.PROTECT,related_name='lineas')
    producto=models.ForeignKey('catalogo.Producto',on_delete=models.PROTECT)
    sin_limite=models.BooleanField('sin saldo definido',default=False)
    cantidad=models.PositiveIntegerField('cantidad prescrita',null=True,blank=True)
    entregada=models.PositiveIntegerField(default=0)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['receta','producto'],name='clinica_receta_producto'),models.CheckConstraint(condition=(models.Q(sin_limite=True,cantidad__isnull=True)|models.Q(sin_limite=False,cantidad__isnull=False,cantidad__gt=0,cantidad__gte=models.F('entregada'))),name='clinica_saldo_coherente')]
    @property
    def saldo(self): return None if self.sin_limite else self.cantidad-self.entregada
    def clean(self):
        if self.sin_limite: self.cantidad=None
        elif not self.cantidad: raise ValidationError('Indica una cantidad mayor a cero o selecciona sin saldo definido.')
        if self.producto_id and self.producto.condicion=='Receta retenida' and self.sin_limite: raise ValidationError('Un controlado requiere cantidad explícita.')

class AdjuntoReceta(models.Model):
    receta=models.ForeignKey(Receta,on_delete=models.PROTECT,related_name='adjuntos')
    archivo=models.FileField(storage=private_storage,upload_to=private_path)
    nombre=models.CharField(max_length=200)
    tipo=models.CharField(max_length=40)
    sha256=models.CharField(max_length=64)
    estado=models.CharField(max_length=15,default='cuarentena',choices=[('cuarentena','En cuarentena'),('revisado','Revisado manualmente'),('rechazado','Rechazado')])
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    revisado_por=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True,related_name='+')
    fecha=models.DateTimeField(auto_now_add=True)

class Entrega(models.Model):
    folio=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    receta=models.ForeignKey(Receta,on_delete=models.PROTECT,related_name='entregas')
    venta=models.OneToOneField('operaciones.Venta',on_delete=models.PROTECT,related_name='entrega_clinica')
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    retirante=models.ForeignKey(Paciente,on_delete=models.PROTECT)
    autorizacion_retiro=models.TextField(blank=True)
    instantanea=models.JSONField(default=dict)
    fecha=models.DateTimeField(auto_now_add=True)
    class Meta: default_permissions=('view',)

class DetalleEntrega(models.Model):
    entrega=models.ForeignKey(Entrega,on_delete=models.PROTECT,related_name='lineas')
    linea_receta=models.ForeignKey(LineaReceta,on_delete=models.PROTECT)
    cantidad=models.PositiveIntegerField()
    class Meta: default_permissions=('view',)

class AutorizacionControlado(models.Model):
    receta=models.ForeignKey(Receta,on_delete=models.PROTECT)
    producto=models.ForeignKey('catalogo.Producto',on_delete=models.PROTECT)
    cantidad=models.PositiveIntegerField()
    profesional=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    fecha=models.DateTimeField(auto_now_add=True)
    entrega=models.ForeignKey(Entrega,on_delete=models.PROTECT,null=True,blank=True)
    class Meta: default_permissions=('view',)

class AsientoControlado(models.Model):
    entrega=models.ForeignKey(Entrega,on_delete=models.PROTECT)
    producto=models.ForeignKey('catalogo.Producto',on_delete=models.PROTECT)
    cantidad=models.IntegerField()
    profesional=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    fecha=models.DateTimeField(auto_now_add=True)
    compensa=models.OneToOneField('self',on_delete=models.PROTECT,null=True,blank=True,related_name='compensacion')
    motivo=models.TextField(blank=True)
    class Meta:
        default_permissions=('view',)
        ordering=['-pk']

class EventoClinico(models.Model):
    receta=models.ForeignKey(Receta,on_delete=models.PROTECT,related_name='eventos')
    usuario=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    accion=models.CharField(max_length=30)
    detalle=models.JSONField(default=dict)
    fecha=models.DateTimeField(auto_now_add=True)
    class Meta:
        default_permissions=('view',)
        ordering=['-pk']
