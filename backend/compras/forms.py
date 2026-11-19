import uuid
from django import forms
from django.core import signing
from django.forms import BaseFormSet, formset_factory
from catalogo.models import Producto
from operaciones.models import Ubicacion
from .models import LineaOrden, Proveedor


class TokenCompraForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, usuario, tipo, **kwargs):
        self.usuario, self.tipo = usuario, tipo
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial['token'] = signing.dumps({'usuario': usuario.pk, 'tipo': tipo, 'clave': str(uuid.uuid4())}, salt='compras')

    def clean_token(self):
        try:
            datos = signing.loads(self.cleaned_data['token'], salt='compras', max_age=7200)
            if datos['usuario'] != self.usuario.pk or datos['tipo'] != self.tipo:
                raise ValueError
            return uuid.UUID(datos['clave'])
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise forms.ValidationError('Este formulario venció o no corresponde a la operación. Abre uno nuevo.')


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['codigo', 'nombre', 'email', 'telefono', 'activo']
        help_texts = {'codigo': 'Identificador interno único; no es un RUT.',
            'activo': 'Al desactivar se impiden nuevas órdenes; las existentes conservan su historial.'}

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()


class OrdenForm(TokenCompraForm):
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.filter(activo=True))
    observaciones = forms.CharField(required=False, max_length=300, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            self.fields['proveedor'].queryset = Proveedor.objects.all()


class LineaOrdenForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True))
    cantidad = forms.IntegerField(min_value=1, max_value=1000000, initial=1, label='Envases pedidos')
    costo_unitario = forms.DecimalField(min_value=0, max_value=999999999999, max_digits=12, decimal_places=0,
        label='Costo por envase CLP', widget=forms.NumberInput(attrs={'min': 0, 'step': 1}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            self.fields['producto'].queryset = Producto.objects.all()


class LineasOrdenBase(BaseFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        vistos = set()
        for form in self.forms:
            datos = form.cleaned_data
            if not datos or datos.get('DELETE'):
                continue
            producto = datos.get('producto')
            if producto and producto.pk in vistos:
                raise forms.ValidationError('Cada producto debe aparecer una sola vez. Ajusta su cantidad en la misma fila.')
            if producto:
                vistos.add(producto.pk)


LineasOrdenFormSet = formset_factory(LineaOrdenForm, formset=LineasOrdenBase, extra=0, min_num=1,
    validate_min=True, max_num=20, validate_max=True, can_delete=True)


class RecepcionForm(TokenCompraForm):
    referencia = forms.CharField(max_length=60, label='Referencia de entrega',
        help_text='Ejemplo: GUIA-DEMO-001. Una referencia solo puede registrarse una vez por orden.')


class PartidaRecepcionForm(forms.Form):
    linea = forms.ModelChoiceField(queryset=LineaOrden.objects.none(), label='Producto de esta orden')
    codigo = forms.CharField(max_length=60, label='Lote recibido')
    vencimiento = forms.DateField(input_formats=['%Y-%m-%d'], label='Vencimiento',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    ubicacion = forms.ChoiceField(choices=Ubicacion.choices, label='Ubicación de destino', initial=Ubicacion.BODEGA)
    cantidad = forms.IntegerField(min_value=1, max_value=1000000, label='Envases recibidos')

    def __init__(self, *args, orden, **kwargs):
        super().__init__(*args, **kwargs)
        # Conservar todas las líneas para poder validar un reintento tras completar la orden.
        self.fields['linea'].queryset = orden.lineas.all()


PartidasFormSet = formset_factory(PartidaRecepcionForm, extra=0, min_num=1, validate_min=True,
    max_num=30, validate_max=True, can_delete=True)


class AnularForm(forms.Form):
    motivo = forms.CharField(min_length=10, max_length=300, label='Motivo de anulación', widget=forms.Textarea(attrs={'rows': 2}))
