from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.models import Existencia, Lote, Venta
from comercio.models import Caja
from comercio.services import confirmar_venta
from operaciones.services import registrar_ingreso


@skipUnlessDBFeature('has_select_for_update')
class ConcurrenciaPostgreSQLTests(TransactionTestCase):
    def setUp(self):
        call_command('configurar_roles', stdout=StringIO())
        self.usuarios = []
        for nombre in ['concurrente_a', 'concurrente_b']:
            user = get_user_model().objects.create_user(nombre)
            user.groups.add(Group.objects.get(name='Administrador'))
            self.usuarios.append(user.pk)
            Caja.objects.create(usuario=user, fondo=0)
        categoria = Categoria.objects.create(nombre='Prueba concurrente')
        self.producto = Producto.objects.create(codigo='CONC-1', barras='9900000022222', nombre='Última unidad',
            presentacion='Demo', categoria=categoria, condicion='Venta directa', precio=1000)
        self.lote = Lote.objects.create(producto=self.producto, codigo='ULTIMO', vencimiento=timezone.localdate() + timedelta(days=30))
        Existencia.objects.create(lote=self.lote, ubicacion='vitrina', cantidad=1)

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

    def vender(self, usuario, clave):
        # Se prueba el punto de venta real (comercio), única ruta de venta de la aplicación.
        return confirmar_venta(usuario=usuario, items=[{'producto_id': self.producto.pk, 'cantidad': 1}], clave=clave,
            caja_id=Caja.objects.get(usuario=usuario, cierre__isnull=True).pk).pk

    def test_dos_vendedores_solo_una_ultima_unidad(self):
        resultados = self.correr(lambda usuario: self.vender(usuario, uuid.uuid4()))
        self.assertEqual(resultados.count('rechazada'), 1)
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(Existencia.objects.get(lote=self.lote, ubicacion='vitrina').cantidad, 0)

    def test_doble_confirmacion_mismo_actor_una_venta(self):
        self.usuarios[1] = self.usuarios[0]
        clave = uuid.uuid4()
        resultados = self.correr(lambda usuario: self.vender(usuario, clave))
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(Venta.objects.count(), 1)

    def test_doble_ingreso_mismo_formulario_una_cantidad(self):
        self.usuarios[1] = self.usuarios[0]
        clave = uuid.uuid4()
        resultados = self.correr(lambda usuario: registrar_ingreso(usuario=usuario, producto_id=self.producto.pk,
            codigo='NUEVO', vencimiento=self.lote.vencimiento, ubicacion='bodega', cantidad=4, clave=clave).pk)
        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(Existencia.objects.get(lote__codigo='NUEVO', ubicacion='bodega').cantidad, 4)
