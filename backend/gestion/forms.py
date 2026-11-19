from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from catalogo.models import Categoria, Producto
from .models import Trabajador, PoliticaPrecio, PrecioProgramado, ConfiguracionAlerta
from .services import ROLES


class UsuarioForm(forms.ModelForm):
    rut = forms.CharField(label='RUT', max_length=12, help_text='Sin puntos y con guion; se valida el dígito verificador.')
    telefono = forms.CharField(label='Teléfono', max_length=30)
    grupos = forms.ModelMultipleChoiceField(label='Roles', queryset=Group.objects.filter(name__in=ROLES), required=False,
        widget=forms.CheckboxSelectMultiple, help_text='Marca los roles que corresponden al trabajador. Sin roles no tendrá acceso a las operaciones.')
    nueva_clave = forms.CharField(label='Contraseña inicial / nueva', widget=forms.PasswordInput, required=False,
        help_text='Obligatoria al crear; deja vacío al editar para conservarla.')

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {'username': 'Nombre de usuario', 'first_name': 'Nombres', 'last_name': 'Apellidos',
            'email': 'Correo electrónico', 'is_active': 'Cuenta activa'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        if self.instance.pk:
            self.initial['grupos'] = self.instance.groups.all()
            perfil = Trabajador.objects.filter(usuario=self.instance).first()
            if perfil:
                self.initial.update(rut=perfil.rut, telefono=perfil.telefono)

    def clean_rut(self):
        rut = self.cleaned_data['rut'].replace('.', '').upper().strip()
        partes = rut.split('-')
        if len(partes) != 2 or not partes[0].isdigit() or not 7 <= len(partes[0]) <= 8:
            raise ValidationError('Usa el formato 12345678-5.')
        suma = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(partes[0])))
        dv = 11 - suma % 11
        if partes[1] != ('K' if dv == 10 else '0' if dv == 11 else str(dv)):
            raise ValidationError('El dígito verificador del RUT no coincide.')
        if Trabajador.objects.filter(rut=rut).exclude(usuario_id=self.instance.pk).exists():
            raise ValidationError('Este RUT ya tiene una cuenta.')
        return rut

    def clean_nueva_clave(self):
        clave = self.cleaned_data['nueva_clave']
        if not self.instance.pk and not clave:
            raise ValidationError('Indica una contraseña inicial.')
        if clave:
            password_validation.validate_password(clave, self.instance)
        return clave


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']


class PoliticaForm(forms.ModelForm):
    class Meta:
        model = PoliticaPrecio
        fields = ['aplica_cenabast', 'precio_maximo', 'descuento_maximo', 'fuente']


class PrecioForm(forms.ModelForm):
    class Meta:
        model = PrecioProgramado
        fields = ['producto', 'precio', 'desde', 'hasta', 'fuente']
        widgets = {'desde': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'hasta': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}


class AlertaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionAlerta
        fields = ['producto', 'ubicacion', 'stock_minimo', 'dias_vencimiento']


class CondicionForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all())
    condicion = forms.ChoiceField(label='Condición revisada', choices=Producto.Condicion.choices)
    motivo = forms.CharField(label='Fundamento profesional y fuente', max_length=1000, widget=forms.Textarea)
