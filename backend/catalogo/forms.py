from django import forms
from .models import Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['codigo', 'barras', 'nombre', 'presentacion', 'categoria', 'condicion', 'precio', 'stock_minimo']
        widgets = {'precio': forms.NumberInput(attrs={'min': 0, 'step': 1})}
        help_texts = {
            'codigo': 'Identificador único. Ejemplo: PRD-009.',
            'barras': 'Entre 8 y 14 dígitos. Usa códigos ficticios.',
            'precio': 'Pesos chilenos, sin decimales.',
            'stock_minimo': 'Mínimo total (bodega + vitrina). Para un umbral distinto en una sola ubicación usa Alertas por ubicación.',
        }

    def __init__(self, *args, puede_definir_condicion=True, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['condicion'].disabled = True
            self.fields['condicion'].help_text = 'Se conserva la condición; su modificación requiere revisión técnica.'
        elif not puede_definir_condicion:
            # La condición de venta es una decisión profesional (HU03): sin QF, el producto nace pendiente de revisión.
            self.fields['condicion'].disabled = True
            self.fields['condicion'].initial = Producto.Condicion.VERIFICAR
            self.fields['condicion'].help_text = ('Queda «Por verificar» y no se vende hasta que un Químico Farmacéutico '
                                                  'la revise en Revisión de productos.')
        for name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{name}_ayuda'

    def clean_codigo(self):
        return self.cleaned_data['codigo'].strip().upper()
