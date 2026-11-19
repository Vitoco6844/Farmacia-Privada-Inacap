from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from catalogo.models import Categoria, Producto
from compras.models import Proveedor, Recepcion
from operaciones.models import Existencia


class ComprasApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', verbosity=0)
        for nombre, grupo in (('admin_compras', 'Administrador'), ('vendedor_compras', 'Vendedor')):
            usuario = get_user_model().objects.create_user(nombre)
            usuario.groups.add(Group.objects.get(name=grupo))
        cls.proveedor = Proveedor.objects.create(codigo='PROV', nombre='Proveedor ficticio')
        cls.producto = Producto.objects.create(
            codigo='ENS-API', barras='909999000012', nombre='Producto de ensayo',
            categoria=Categoria.objects.create(nombre='Ensayo'), precio=500,
            condicion=Producto.Condicion.DIRECTA,
        )

    def test_recepcion_parcial_idempotente_y_consulta_stock(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(get_user_model().objects.get(username='admin_compras'))
        base = '/api/v1/compras/ordenes/'
        csrf = cliente.get('/api/v1/sesion/').json()['csrfToken']
        token = cliente.get(base + 'nueva/').json()['token']
        datos = {
            'proveedor': self.proveedor.pk, 'token': token,
            'lineas-TOTAL_FORMS': 1, 'lineas-INITIAL_FORMS': 0,
            'lineas-0-producto': self.producto.codigo, 'lineas-0-cantidad': 10,
            'lineas-0-costo_unitario': 100,
        }
        self.assertEqual(cliente.post(base + 'nueva/', datos).status_code, 403)
        r = cliente.post(base + 'nueva/', datos, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertFalse(Existencia.objects.exists())
        orden = r.json()['id']
        detalle = f'{base}{orden}/'
        datos = {
            'token': cliente.get(detalle + 'recibir/').json()['token'], 'referencia': 'GUIA-API',
            'partidas-TOTAL_FORMS': 1, 'partidas-INITIAL_FORMS': 0,
            'partidas-0-linea': r.json()['lineas'][0]['id'], 'partidas-0-codigo': 'LOTE-API',
            'partidas-0-vencimiento': (timezone.localdate() + timedelta(days=30)).isoformat(),
            'partidas-0-ubicacion': 'bodega', 'partidas-0-cantidad': 4,
        }
        for _ in range(2):
            recepcion = cliente.post(detalle + 'recibir/', datos, HTTP_X_CSRFTOKEN=csrf)
            self.assertEqual(recepcion.status_code, 200, recepcion.content)
        self.assertEqual(Recepcion.objects.count(), 1)
        actual = cliente.get(detalle).json()
        self.assertEqual(actual['estado'], 'parcial')
        self.assertEqual(actual['lineas'][0]['pendiente'], 6)
        self.assertEqual(actual['recepciones'][0]['referencia'], 'GUIA-API')
        stock = cliente.get('/api/v1/inventario/', {'q': 'LOTE-API'}).json()['existencias']
        self.assertEqual([(f['lote'], f['cantidad'], f['ubicacion']) for f in stock], [('LOTE-API', 4, 'bodega')])
        datos.update(token=cliente.get(detalle + 'recibir/').json()['token'], referencia='OTRA', **{'partidas-0-cantidad': 7})
        self.assertEqual(cliente.post(detalle + 'recibir/', datos, HTTP_X_CSRFTOKEN=csrf).status_code, 400)
        self.assertEqual(Existencia.objects.get().cantidad, 4)

    def test_vendedor_consulta_inventario_sin_acceso_a_compras(self):
        self.client.force_login(get_user_model().objects.get(username='vendedor_compras'))
        self.assertEqual(self.client.get('/api/v1/compras/ordenes/').status_code, 403)
        self.assertEqual(self.client.post('/api/v1/compras/ordenes/nueva/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/inventario/').status_code, 200)
