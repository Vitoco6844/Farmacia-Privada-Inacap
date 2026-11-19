from django.db import models


class LimiteAcceso(models.Model):
    """Claves HMAC: nunca almacenar contraseña, nombre de cuenta ni IP en claro."""
    clave = models.CharField(max_length=64, primary_key=True)
    inicio = models.DateTimeField()
    intentos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        default_permissions = ()


class EventoAcceso(models.Model):
    cuenta = models.CharField(max_length=64)
    origen = models.CharField(max_length=64)
    fecha = models.DateTimeField(auto_now_add=True)
    resultado = models.CharField(max_length=12, choices=[('correcto', 'Correcto'), ('fallido', 'Fallido'), ('limitado', 'Limitado')])

    class Meta:
        default_permissions = ('view',)
        ordering = ['-fecha', '-pk']
