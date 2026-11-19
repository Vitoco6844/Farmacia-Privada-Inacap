from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Producto
from clinica.models import LineaReceta, Paciente, Prescriptor, Receta
from compras.models import OrdenCompra, Proveedor
from operaciones.models import Existencia, Lote


class FlujosApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', verbosity=0)
        cls.admin = cls.usuario('api_admin', 'Administrador')
        cls.qf = cls.usuario('api_qf', 'Químico Farmacéutico')
        cls.vendedor = cls.usuario('api_vendedor', 'Vendedor')
        cls.producto = Producto.objects.create(
            codigo='ENS-3', barras='9991234567890', nombre='Producto ficticio',
            categoria=Categoria.objects.create(nombre='Ensayo'), precio=1000,
            condicion=Producto.Condicion.DIRECTA,
        )
        cls.lote = Lote.objects.create(producto=cls.producto, codigo='LOTE-3',
                                      vencimiento=timezone.localdate() + timedelta(days=30))
        Existencia.objects.create(lote=cls.lote, ubicacion='bodega', cantidad=10)

    @staticmethod
    def usuario(nombre, rol):
        usuario = get_user_model().objects.create_user(nombre)
        usuario.groups.add(Group.objects.get(name=rol))
        return usuario

    def ruta(self, modulo):
        return '/api/v1/operaciones/' + modulo + '/'

    def test_traslado_venta_academica_y_cierre(self):
        self.client.force_login(self.admin)
        ruta = self.ruta('traslado')
        formulario = self.client.get(ruta).json()['formularios'][0]
        token = next(c['valor'] for c in formulario['campos'] if c['nombre'] == 'token')
        r = self.client.post(ruta, {'token': token, 'lote': self.lote.pk, 'origen': 'bodega',
                                    'destino': 'vitrina', 'cantidad': 4})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Existencia.objects.get(lote=self.lote, ubicacion='vitrina').cantidad, 4)
        r = self.client.post(self.ruta('caja'), {'accion': 'abrir', 'fondo': 10000})
        self.assertEqual(r.status_code, 200, r.content)
        pos = self.client.get(self.ruta('pos')).json()
        r = self.client.post(self.ruta('pos'), {
            'items': '[{"producto_id":%d,"cantidad":2}]' % self.producto.pk,
            'caja_id': pos['pos']['caja'], 'clave': str(uuid4()), 'medio': 'efectivo',
            'tipo_documento': 'boleta',
        })
        self.assertEqual(r.status_code, 200, r.content)
        documento = r.json()['destino']
        self.assertTrue(documento.startswith('documento/'))
        r = self.client.post(self.ruta(documento), {'accion': 'emitir'})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Existencia.objects.get(lote=self.lote, ubicacion='vitrina').cantidad, 2)
        r = self.client.post(self.ruta('caja'), {'accion': 'cerrar', 'caja_id': pos['pos']['caja'], 'contado': 12000})
        self.assertEqual(r.status_code, 200, r.content)

    def test_reporte_entrega_archivo_y_auditoria_limita_datos(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.ruta('reporte-inventario'), {'formato': 'xlsx'})
        self.assertEqual(r.status_code, 200, r.content[:200])
        self.assertTrue(r.content.startswith(b'PK'))
        self.assertIn('attachment', r['Content-Disposition'])
        r = self.client.get(self.ruta('auditoria'))
        filas = r.json()['tablas'][0]['filas']
        self.assertTrue(filas)
        self.assertTrue(all(len(fila) == 5 for fila in filas))

    def test_proveedor_anulacion_y_restricciones_por_rol(self):
        self.client.force_login(self.admin)
        r = self.client.post(self.ruta('proveedor-nuevo'), {'codigo': 'P3', 'nombre': 'Proveedor ficticio', 'activo': 'on'})
        self.assertEqual(r.status_code, 200, r.content)
        orden = OrdenCompra.objects.create(proveedor=Proveedor.objects.get(codigo='P3'), proveedor_nombre='Proveedor',
                                           usuario=self.admin, total=0)
        r = self.client.post(self.ruta(f'anular/{orden.pk}'), {'motivo': 'Anulación del ensayo'})
        self.assertEqual(r.status_code, 200, r.content)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'anulada')
        self.client.force_login(self.vendedor)
        for pantalla in ('proveedores', 'auditoria', 'usuarios', 'traslado'):
            self.assertEqual(self.client.get(self.ruta(pantalla)).status_code, 403, pantalla)

    def test_revision_clinica_limitada_al_qf(self):
        hoy = timezone.localdate()
        receta = Receta.objects.create(
            paciente=Paciente.objects.create(identificador='P-3', nombre='Paciente ficticio'),
            prescriptor=Prescriptor.objects.create(identificador='M-3', nombre='Prescriptor ficticio', registro='3'),
            emitida=hoy, vence=hoy + timedelta(days=7),
        )
        LineaReceta.objects.create(receta=receta, producto=self.producto, cantidad=3)
        ruta = self.ruta(f'receta/{receta.pk}')
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(ruta, {'accion': 'revisar', 'decision': 'aprobar'}).status_code, 403)
        self.client.force_login(self.qf)
        self.assertEqual(self.client.post(ruta, {'accion': 'revisar', 'decision': 'aprobar'}).status_code, 200)
        receta.refresh_from_db()
        self.assertEqual(receta.estado, 'aprobada')

    def test_menu_y_registro_de_receta_con_formulario_independiente(self):
        self.client.force_login(self.admin)
        for entrada in self.client.get('/api/v1/sesion/').json()['pantallas']:
            with self.subTest(ruta=entrada['ruta']):
                r = self.client.get(self.ruta(entrada['ruta']))
                self.assertEqual(r.status_code, 200, r.content[:300])
                self.assertIn('titulo', r.json())
        paciente = Paciente.objects.create(identificador='P-4', nombre='Paciente de ensayo')
        prescriptor = Prescriptor.objects.create(identificador='M-4', nombre='Prescriptor de ensayo', registro='4')
        ruta = self.ruta('receta-nueva')
        form = self.client.get(ruta).json()['formularios'][0]
        prefijo = form['prefijo']
        hoy = timezone.localdate()
        r = self.client.post(ruta, {'paciente': paciente.pk, 'prescriptor': prescriptor.pk,
                                    'emitida': hoy.isoformat(), 'vence': (hoy + timedelta(days=7)).isoformat(),
                                    f'{prefijo}-TOTAL_FORMS': 1, f'{prefijo}-INITIAL_FORMS': 0,
                                    f'{prefijo}-0-producto': self.producto.pk, f'{prefijo}-0-cantidad': 3})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Receta.objects.get().lineas.get().cantidad, 3)
