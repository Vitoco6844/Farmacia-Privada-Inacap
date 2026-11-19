from datetime import timedelta
from math import ceil
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import EventoAcceso, LimiteAcceso

VENTANA = timedelta(minutes=15)
LIMITES = {'cuenta': 5, 'origen': 30}


class IngresarView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def _limitado(self, form, hasta):
        form.add_error(None, 'Por seguridad se limitó temporalmente el ingreso. Espera antes de volver a intentarlo.')
        respuesta = self.render_to_response(self.get_context_data(form=form, response_limitada=True), status=429)
        respuesta['Retry-After'] = str(max(1, ceil((hasta - timezone.now()).total_seconds())))
        respuesta['Cache-Control'] = 'no-store'
        return respuesta

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ahora = timezone.now()
        usuario = get_user_model().normalize_username(request.POST.get('username', '').strip()).casefold()
        origen = request.META.get('REMOTE_ADDR', '')
        claves = {tipo: salted_hmac('farmacia-ingreso', f'{tipo}:{valor}', algorithm='sha256').hexdigest()
            for tipo, valor in [('cuenta', usuario), ('origen', origen)]}
        limites = {}
        # Orden estable para evitar interbloqueos entre peticiones simultáneas.
        for tipo, clave in sorted(claves.items(), key=lambda par: par[1]):
            fila, _ = LimiteAcceso.objects.get_or_create(clave=clave, defaults={'inicio': ahora})
            fila = LimiteAcceso.objects.select_for_update().get(pk=fila.pk)
            if (fila.bloqueado_hasta and fila.bloqueado_hasta <= ahora) or (
                    not fila.bloqueado_hasta and fila.inicio + VENTANA <= ahora):
                fila.inicio, fila.intentos, fila.bloqueado_hasta = ahora, 0, None
                fila.save()
            limites[tipo] = fila
        hasta = max((fila.bloqueado_hasta for fila in limites.values() if fila.bloqueado_hasta), default=None)
        form = self.get_form()
        if hasta and hasta > ahora:
            EventoAcceso.objects.create(cuenta=claves['cuenta'], origen=claves['origen'], resultado='limitado')
            # No verificar contraseñas mientras existe un bloqueo: formulario no vinculado.
            form = self.get_form_class()(request=request, initial={'username': request.POST.get('username', '')})
            form.full_clean()
            form.cleaned_data = {}
            return self._limitado(form, hasta)
        if form.is_valid():
            cuenta = limites['cuenta']
            cuenta.intentos, cuenta.bloqueado_hasta, cuenta.inicio = 0, None, ahora
            cuenta.save()
            EventoAcceso.objects.create(cuenta=claves['cuenta'], origen=claves['origen'], resultado='correcto')
            return self.form_valid(form)
        for tipo, fila in limites.items():
            fila.intentos += 1
            if fila.intentos >= LIMITES[tipo]:
                fila.bloqueado_hasta = ahora + VENTANA
            fila.save()
        EventoAcceso.objects.create(cuenta=claves['cuenta'], origen=claves['origen'], resultado='fallido')
        hasta = max((fila.bloqueado_hasta for fila in limites.values() if fila.bloqueado_hasta), default=None)
        return self._limitado(form, hasta) if hasta else self.form_invalid(form)


from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.urls import reverse_lazy


@login_required
@require_POST
def actividad(request):
    return HttpResponse(status=204)


class RecuperarView(PasswordResetView):
    template_name = 'registration/recuperar.html'
    email_template_name = 'registration/recuperar_email.txt'
    subject_template_name = 'registration/recuperar_asunto.txt'
    success_url = reverse_lazy('password_reset_done')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        ahora = timezone.now()
        clave = salted_hmac('farmacia-recuperacion', request.META.get('REMOTE_ADDR', ''), algorithm='sha256').hexdigest()
        fila, _ = LimiteAcceso.objects.get_or_create(clave=clave, defaults={'inicio': ahora})
        fila = LimiteAcceso.objects.select_for_update().get(pk=fila.pk)
        if fila.inicio + VENTANA <= ahora:
            fila.inicio, fila.intentos = ahora, 0
        if fila.intentos >= 5:
            respuesta = HttpResponse('Espera 15 minutos antes de volver a solicitar recuperación.', status=429)
            respuesta['Retry-After'] = '900'
            return respuesta
        fila.intentos += 1
        fila.save()
        return super().post(request, *args, **kwargs)
