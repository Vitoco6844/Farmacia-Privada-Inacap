import uuid
from django import forms
from django.core import signing
from django.utils import timezone
from catalogo.models import Producto
from .models import Lote, Ubicacion


class OperacionForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)
    cantidad = forms.IntegerField(min_value=1, max_value=1000000, label='Cantidad de envases')

    def __init__(self, *args, usuario, tipo, **kwargs):
        self.usuario = usuario
        self.tipo = tipo
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial['token'] = signing.dumps({'usuario': usuario.pk, 'tipo': tipo, 'clave': str(uuid.uuid4())}, salt='operaciones')

    def clean_token(self):
        try:
            datos = signing.loads(self.cleaned_data['token'], salt='operaciones', max_age=7200)
            if datos['usuario'] != self.usuario.pk or datos['tipo'] != self.tipo:
                raise ValueError
            return uuid.UUID(datos['clave'])
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise forms.ValidationError('El formulario venció o no corresponde a tu cuenta. Abre uno nuevo.')


class IngresoForm(OperacionForm):
    producto = forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True))
    codigo = forms.CharField(max_length=60, label='Código de lote')
    vencimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), input_formats=['%Y-%m-%d'], label='Fecha de vencimiento')
    ubicacion = forms.ChoiceField(choices=Ubicacion.choices, label='Ubicación')
    confirmar_vencido = forms.BooleanField(required=False, label='Confirmo que registro un lote vencido o que vence hoy',
        help_text='Solo para dejar constancia de stock vencido encontrado. Ese lote no se podrá vender ni trasladar.')
    field_order = ['producto', 'codigo', 'vencimiento', 'ubicacion', 'cantidad', 'confirmar_vencido', 'token']

    def clean(self):
        datos = super().clean()
        vencimiento = datos.get('vencimiento')
        if vencimiento and vencimiento <= timezone.localdate() and not datos.get('confirmar_vencido'):
            self.add_error('vencimiento', 'La fecha indica un lote vencido o que vence hoy. Revisa la fecha o marca la '
                                          'confirmación para registrarlo como stock no vendible.')
        return datos


class TrasladoForm(OperacionForm):
    lote = forms.ModelChoiceField(queryset=Lote.objects.select_related('producto'))
    origen = forms.ChoiceField(choices=Ubicacion.choices)
    destino = forms.ChoiceField(choices=Ubicacion.choices)
    field_order = ['lote', 'origen', 'destino', 'cantidad', 'token']
