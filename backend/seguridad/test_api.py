from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase

from catalogo.models import Categoria, Producto


class ApiCatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', verbosity=0)
        from django.contrib.auth.models import Group
        cls.usuario = get_user_model().objects.create_user('api_vendedor', password='Prueba-Local-42!')
        cls.usuario.groups.add(Group.objects.get(name='Vendedor'))
        categoria = Categoria.objects.create(nombre='Ensayo')
        Producto.objects.create(codigo='P-001', barras='1234567890123', nombre='Producto de ensayo',
                                categoria=categoria, condicion=Producto.Condicion.DIRECTA, precio=900)

    def test_login_busqueda_y_salida_con_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        sesion = '/api/v1/sesion/'
        ingreso = '/api/v1/sesion/ingresar/'
        productos = '/api/v1/productos/'
        self.assertEqual(cliente.get(productos).status_code, 401)
        token = cliente.get(sesion).json()['csrfToken']
        datos = {'username': self.usuario.username, 'password': 'Prueba-Local-42!'}
        self.assertEqual(cliente.post(ingreso, datos).status_code, 403)
        respuesta = cliente.post(ingreso, datos, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(respuesta.status_code, 200)
        consulta = cliente.get(productos, {'q': 'ensayo'}).json()
        self.assertEqual([p['codigo'] for p in consulta['productos']], ['P-001'])
        self.assertEqual(consulta['resumen'], {'total': 1, 'activos': 1, 'receta': 0})
        self.assertEqual(consulta['categorias'], ['Ensayo'])
        self.assertEqual(cliente.get(productos, {'categoria': 'Ensayo', 'condicion': 'Venta directa'}).json()['total'], 1)
        self.assertEqual(cliente.get(productos, {'condicion': 'Receta simple'}).json()['total'], 0)
        self.assertEqual(cliente.get(productos, {'q': 'ausente'}).json()['productos'], [])
        self.assertEqual(cliente.post('/api/v1/sesion/salir/', HTTP_X_CSRFTOKEN=respuesta.json()['csrfToken']).status_code, 200)
        self.assertEqual(cliente.get(productos).status_code, 401)

    def test_sin_permiso_y_limite_de_intentos(self):
        usuario = get_user_model().objects.create_user('api_sin_rol')
        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/api/v1/productos/').status_code, 403)
        self.client.logout()
        for _ in range(4):
            r = self.client.post('/api/v1/sesion/ingresar/', {'username': self.usuario.username, 'password': 'incorrecta'})
            self.assertEqual(r.status_code, 401)
        r = self.client.post('/api/v1/sesion/ingresar/', {'username': self.usuario.username, 'password': 'incorrecta'})
        self.assertEqual(r.status_code, 429)
        self.assertGreater(int(r['Retry-After']), 0)

    def test_expiracion_devuelve_respuesta_api(self):
        self.client.force_login(self.usuario)
        sesion = self.client.session
        sesion['ultima_actividad_humana'] = 1
        sesion.save()
        self.assertEqual(self.client.get('/api/v1/productos/').status_code, 401)
