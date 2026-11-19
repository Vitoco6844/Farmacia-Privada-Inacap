from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import EventoAcceso, LimiteAcceso


class LimitesAccesoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user('cuenta_seguridad', password='ClaveLarga-Pruebas-123')

    def post(self, password='incorrecta', username='cuenta_seguridad', url=None):
        return self.client.post(url or reverse('login'), {'username': username, 'password': password})

    def test_cinco_fallos_bloquean_incluso_clave_correcta(self):
        for _ in range(4):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post().status_code, 429)
        r = self.post(password='ClaveLarga-Pruebas-123')
        self.assertEqual(r.status_code, 429)
        self.assertGreater(int(r['Retry-After']), 0)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(r, 'temporalmente', status_code=429)

    def test_bloqueo_no_verifica_contrasenas(self):
        for _ in range(5):
            self.post()
        with patch('django.contrib.auth.forms.authenticate', side_effect=AssertionError('No autenticar durante el bloqueo')):
            self.assertEqual(self.post().status_code, 429)

    def test_expiracion_del_bloqueo_permita_ingreso(self):
        for _ in range(5):
            self.post()
        LimiteAcceso.objects.update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.post(password='ClaveLarga-Pruebas-123').status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_exito_reinicia_fallos_de_cuenta(self):
        for _ in range(4):
            self.post()
        self.post(password='ClaveLarga-Pruebas-123')
        self.client.logout()
        self.assertEqual(self.post().status_code, 200)
        self.assertTrue(EventoAcceso.objects.filter(resultado='correcto').exists())

    def test_ventana_caducada_reinicia_contador(self):
        for _ in range(4):
            self.post()
        LimiteAcceso.objects.update(inicio=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(set(LimiteAcceso.objects.values_list('intentos', flat=True)), {1})

    def test_variar_mayusculas_no_elude_limite(self):
        for nombre in ['CUENTA_SEGURIDAD', 'cuenta_seguridad', 'Cuenta_Seguridad', ' cuenta_seguridad ', 'cuenta_seguridad']:
            r = self.post(username=nombre)
        self.assertEqual(r.status_code, 429)
        self.assertEqual(LimiteAcceso.objects.count(), 2)

    def test_cuentas_inexistentes_tambien_se_limitan(self):
        for _ in range(5):
            r = self.post(username='inexistente')
        self.assertEqual(r.status_code, 429)

    def test_limite_origen_con_cuentas_distintas(self):
        for i in range(30):
            r = self.post(username=f'cuenta_inexistente_{i}')
        self.assertEqual(r.status_code, 429)
        self.assertEqual(self.post(password='ClaveLarga-Pruebas-123').status_code, 429)

    def test_no_confiar_en_cabecera_de_proxy_para_eludir(self):
        for i in range(5):
            r = self.client.post(reverse('login'), {'username': 'cuenta_seguridad', 'password': 'incorrecta'},
                HTTP_X_FORWARDED_FOR=f'10.0.0.{i}')
        self.assertEqual(r.status_code, 429)

    def test_acceso_admin_comparte_limites(self):
        for _ in range(4):
            self.post()
        r = self.post(url='/administracion/login/')
        self.assertEqual(r.status_code, 429)

    def test_eventos_no_contienen_datos_en_claro(self):
        self.post()
        evento = EventoAcceso.objects.get()
        self.assertEqual(len(evento.cuenta), 64)
        self.assertEqual(len(evento.origen), 64)
        texto = str(list(EventoAcceso.objects.values()))
        for dato in ['cuenta_seguridad', '127.0.0.1', 'incorrecta']:
            self.assertNotIn(dato, texto)
