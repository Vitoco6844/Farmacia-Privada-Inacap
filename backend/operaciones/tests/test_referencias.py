from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from catalogo.medicamentos_referencia import FECHA_CONSULTA, MEDICAMENTOS
from catalogo.models import PrecioReferencia, Producto
from operaciones.models import Existencia, Movimiento


class ReferenciasTests(TestCase):
    def test_carga_idempotente_preserva_ediciones(self):
        call_command('cargar_medicamentos', stdout=StringIO())
        Producto.objects.filter(codigo='MED-001').update(nombre='Nombre editado', precio=1234)
        call_command('cargar_medicamentos', stdout=StringIO())
        self.assertEqual(Producto.objects.count(), 6)
        self.assertEqual(PrecioReferencia.objects.count(), 6)
        self.assertEqual(Producto.objects.get(codigo='MED-001').precio, 1234)
        self.assertEqual(Producto.objects.get(codigo='MED-001').nombre, 'Nombre editado')
        self.assertEqual(PrecioReferencia.objects.get(producto__codigo='MED-001').precio, 840)
        self.assertFalse(Producto.objects.get(codigo='MED-005').condicion == 'Venta directa')

    def test_fuentes_presentacion_y_fecha_completas(self):
        self.assertEqual(len(MEDICAMENTOS), 6)
        self.assertEqual(len({p['codigo'] for p in MEDICAMENTOS}), 6)
        for p in MEDICAMENTOS:
            self.assertTrue(p['fuente'].startswith('https://'))
            self.assertGreater(p['precio'], 0)
            self.assertIn('Envase', p['presentacion'])
        self.assertEqual(str(FECHA_CONSULTA), '2026-10-19')

    def test_stock_demo_no_repone_lo_consumido(self):
        call_command('cargar_medicamentos', stdout=StringIO())
        call_command('cargar_stock_demo', stdout=StringIO())
        stock = Existencia.objects.filter(lote__producto__codigo='MED-001', lote__codigo__endswith='CERCANO').get()
        stock.cantidad -= 2
        stock.save()
        call_command('cargar_stock_demo', stdout=StringIO())
        stock.refresh_from_db()
        self.assertEqual(stock.cantidad, 6)
        self.assertEqual(Movimiento.objects.count(), 24)
        self.assertEqual(Existencia.objects.count(), 24)

    def test_condicion_pendiente_no_se_cuenta_como_receta(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.urls import reverse
        call_command('configurar_roles', stdout=StringIO())
        call_command('cargar_medicamentos', stdout=StringIO())
        usuario = get_user_model().objects.create_user('lector_referencias')
        usuario.groups.add(Group.objects.get(name='Vendedor'))
        self.client.force_login(usuario)
        r = self.client.get(reverse('catalogo:lista'))
        self.assertEqual(r.context['con_receta'], 0)
        self.assertEqual(r.context['por_verificar'], 4)
