import uuid
from django import forms
from django.core import signing
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
    field_order = ['producto', 'codigo', 'vencimiento', 'ubicacion', 'cantidad', 'token']


class TrasladoForm(OperacionForm):
    lote = forms.ModelChoiceField(queryset=Lote.objects.select_related('producto'))
    origen = forms.ChoiceField(choices=Ubicacion.choices)
    destino = forms.ChoiceField(choices=Ubicacion.choices)
    field_order = ['lote', 'origen', 'destino', 'cantidad', 'token']


class ProductoVentaSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            opcion['attrs']['data-precio'] = str(value.instance.precio)
        return opcion


class ProductoVentaChoice(forms.ModelChoiceField):
    def label_from_instance(self, producto):
        return f'{producto.codigo} · {producto.nombre} · {producto.presentacion} · $ {producto.precio_visible} CLP'


class VentaForm(OperacionForm):
    producto = ProductoVentaChoice(queryset=Producto.objects.filter(activo=True, condicion=Producto.Condicion.DIRECTA), widget=ProductoVentaSelect)
    field_order = ['producto', 'cantidad', 'token']
