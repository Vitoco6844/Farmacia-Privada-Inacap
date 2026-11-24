from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from config.rut import es_rut_valido, normalizar_rut
from .models import Paciente,Prescriptor,Receta,LineaReceta


class PacienteForm(forms.ModelForm):
    documento_extranjero=forms.BooleanField(label='Documento extranjero (pasaporte u otro)',required=False,
        help_text='Marca esta opción solo si la persona no tiene RUT chileno.')
    class Meta:
        model=Paciente
        fields=['identificador','nombre','telefono','activo']
        labels={'identificador':'RUT o documento'}
        help_texts={'identificador':'RUT con o sin puntos, por ejemplo 12.345.678-5.'}
    field_order=['identificador','documento_extranjero','nombre','telefono','activo']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.instance.pk and not es_rut_valido(self.instance.identificador):
            self.initial['documento_extranjero']=True
    def clean(self):
        datos=super().clean()
        identificador=' '.join((datos.get('identificador') or '').split())
        if not identificador: return datos
        if datos.get('documento_extranjero'):
            if len(identificador)<5: self.add_error('identificador','Indica el número completo del documento extranjero.')
            datos['identificador']=identificador.upper()
        else:
            try: datos['identificador']=normalizar_rut(identificador)
            except ValidationError as error: self.add_error('identificador',error)
        return datos


class PrescriptorForm(forms.ModelForm):
    class Meta:
        model=Prescriptor
        fields=['identificador','nombre','registro','activo']
        labels={'identificador':'RUT del profesional'}
        help_texts={'identificador':'Con o sin puntos, por ejemplo 12.345.678-5.'}
    def clean_identificador(self):
        return normalizar_rut(self.cleaned_data['identificador'])


class RecetaForm(forms.ModelForm):
    class Meta:
        model=Receta
        fields=['paciente','prescriptor','emitida','vence']
        widgets={k:forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d') for k in ['emitida','vence']}
LineasFormSet=inlineformset_factory(Receta,LineaReceta,fields=['producto','cantidad','sin_limite'],extra=5,min_num=1,validate_min=True,can_delete=False)
class AdjuntoForm(forms.Form):
    archivo=forms.FileField(help_text='PDF, JPG o PNG. Máximo 10 MB. Se almacena en cuarentena; no aprueba la receta.')
