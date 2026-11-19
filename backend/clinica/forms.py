from django import forms
from django.forms import inlineformset_factory
from .models import Paciente,Prescriptor,Receta,LineaReceta
class PacienteForm(forms.ModelForm):
    class Meta:
        model=Paciente
        fields=['identificador','nombre','telefono','activo']
class PrescriptorForm(forms.ModelForm):
    class Meta:
        model=Prescriptor
        fields=['identificador','nombre','registro','activo']
class RecetaForm(forms.ModelForm):
    class Meta:
        model=Receta
        fields=['paciente','prescriptor','emitida','vence']
        widgets={k:forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d') for k in ['emitida','vence']}
LineasFormSet=inlineformset_factory(Receta,LineaReceta,fields=['producto','cantidad','sin_limite'],extra=5,min_num=1,validate_min=True,can_delete=False)
class AdjuntoForm(forms.Form):
    archivo=forms.FileField(help_text='PDF, JPG o PNG. Máximo 10 MB. Se almacena en cuarentena; no aprueba la receta.')
