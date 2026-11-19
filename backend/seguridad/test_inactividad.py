import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase


class InactividadTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('idle', password='Prueba-segura-2026')
        self.client.force_login(self.usuario)

    def test_refresco_no_renueva_actividad_y_caduca(self):
        sesion = self.client.session
        inicio = time.time()
        sesion['ultima_actividad_humana'] = inicio
        sesion.save()
        with patch('seguridad.middleware.time.time', return_value=inicio + 899):
            self.client.get('/inicio/?_automatico=1')
        self.assertEqual(self.client.session['ultima_actividad_humana'], inicio)
        with patch('seguridad.middleware.time.time', return_value=inicio + 901):
            respuesta = self.client.get('/inicio/?_automatico=1')
        self.assertRedirects(respuesta, '/cuentas/ingresar/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_solicitud_humana_renueva_actividad(self):
        inicio = time.time()
        sesion = self.client.session
        sesion['ultima_actividad_humana'] = inicio - 100
        sesion.save()
        with patch('seguridad.middleware.time.time', return_value=inicio):
            self.client.get('/inicio/')
        self.assertEqual(self.client.session['ultima_actividad_humana'], inicio)


from django.core import mail
from django.test import override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RecuperacionTests(TestCase):
    def test_correo_solo_para_usuario_activo_sin_revelar_existencia(self):
        User = get_user_model()
        User.objects.create_user('recuperar', email='demo@example.test', password='Clave-original-2026')
        User.objects.create_user('inactivo', email='inactivo@example.test', password='Clave-original-2026', is_active=False)
        for correo in ['demo@example.test', 'inactivo@example.test', 'nadie@example.test']:
            respuesta = self.client.post(reverse('password_reset'), {'email': correo})
            self.assertRedirects(respuesta, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/cuentas/restablecer/', mail.outbox[0].body)

    def test_limite_recuperacion(self):
        for _ in range(5):
            self.assertEqual(self.client.post(reverse('password_reset'), {'email': 'nadie@example.test'}).status_code, 302)
        self.assertEqual(self.client.post(reverse('password_reset'), {'email': 'nadie@example.test'}).status_code, 429)
