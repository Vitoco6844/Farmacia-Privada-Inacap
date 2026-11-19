from types import SimpleNamespace
from django.http import HttpResponseNotFound, JsonResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from .middleware import PaginaNoEncontradaMiddleware


class PaginaNoEncontradaTests(SimpleTestCase):
    def test_enlaces_segun_sesion_con_y_sin_debug(self):
        for debug in (True, False):
            for authenticated, link in ((False, '/cuentas/ingresar/'), (True, '/inicio/')):
                with self.subTest(debug=debug, authenticated=authenticated), override_settings(DEBUG=debug):
                    request = RequestFactory().get('/pagina-inexistente/', HTTP_ACCEPT='text/html')
                    request.user = SimpleNamespace(is_authenticated=authenticated)
                    response = PaginaNoEncontradaMiddleware(lambda r: HttpResponseNotFound())(request)
                    self.assertContains(response, f'href="{link}"', status_code=404)
                    self.assertContains(response, 'No encontramos esta página', status_code=404)

    def test_no_reemplaza_errores_json(self):
        request = RequestFactory().get('/buscar/', HTTP_ACCEPT='application/json')
        original = JsonResponse({'error': 'No encontrado'}, status=404)
        response = PaginaNoEncontradaMiddleware(lambda r: original)(request)
        self.assertIs(response, original)
