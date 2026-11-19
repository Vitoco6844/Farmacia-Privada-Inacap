import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.models import Existencia, Movimiento
from compras.models import Proveedor, Recepcion
from compras.services import crear_orden, recibir_orden


@skipUnlessDBFeature('has_select_for_update')
class RecepcionConcurrenteTests(TransactionTestCase):
    def setUp(self):
        call_command('configurar_roles', stdout=StringIO())
        self.usuarios = []
        for nombre in ['compras_a', 'compras_b']:
            usuario = get_user_model().objects.create_user(nombre)
            usuario.groups.add(Group.objects.get(name='Administrador'))
            self.usuarios.append(usuario.pk)
        proveedor = Proveedor.objects.create(codigo='CONC', nombre='Demo')
        categoria = Categoria.objects.create(nombre='Concurrente')
        producto = Producto.objects.create(codigo='CONC', barras='9990000011111', nombre='Demo',
            presentacion='Caja', categoria=categoria, precio=1000, condicion='Venta directa')
        self.orden = crear_orden(usuario=usuario, proveedor_id=proveedor.pk, observaciones='', clave=uuid.uuid4(),
            lineas=[{'producto_id': producto.pk, 'cantidad': 10, 'costo_unitario': 500}])
        self.partida = {'linea_id': self.orden.lineas.get().pk, 'codigo': 'CONC-LOTE',
            'vencimiento': timezone.localdate() + timedelta(days=30), 'ubicacion': 'bodega', 'cantidad': 8}

    def correr(self, funcion):
        barrera = Barrier(2)
        def worker(indice):
            close_old_connections()
            try:
                usuario = get_user_model().objects.get(pk=self.usuarios[indice])
                barrera.wait(timeout=10)
                return funcion(usuario)
            except ValidationError:
                return 'rechazada'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(worker, [0, 1]))

    def test_dos_recepciones_no_superan_saldo(self):
        resultados = self.correr(lambda usuario: recibir_orden(usuario=usuario, orden_id=self.orden.pk,
            referencia=f'GUIA-{usuario.pk}', partidas=[self.partida], clave=uuid.uuid4()).pk)
        self.assertEqual(resultados.count('rechazada'), 1)
        self.assertEqual(Existencia.objects.get().cantidad, 8)
        self.assertEqual(self.orden.lineas.get().recibida, 8)

    def test_reenvio_concurrente_mismo_actor(self):
        self.usuarios[1] = self.usuarios[0]
        clave = uuid.uuid4()
        resultados = self.correr(lambda usuario: recibir_orden(usuario=usuario, orden_id=self.orden.pk,
            referencia='GUIA-UNICA', partidas=[self.partida], clave=clave).pk)
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(Movimiento.objects.count(), 1)
        self.assertEqual(Existencia.objects.get().cantidad, 8)

    def test_referencia_repetida_entre_actores(self):
        self.partida['cantidad'] = 4
        resultados = self.correr(lambda usuario: recibir_orden(usuario=usuario, orden_id=self.orden.pk,
            referencia='GUIA-UNICA', partidas=[self.partida], clave=uuid.uuid4()).pk)
        self.assertEqual(resultados.count('rechazada'), 1)
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(Existencia.objects.get().cantidad, 4)
