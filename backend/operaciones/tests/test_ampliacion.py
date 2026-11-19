from io import StringIO, BytesIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from catalogo.models import Categoria, Producto
from compras.models import Proveedor, OrdenCompra, LineaOrden
from operaciones.models import EventoReporte


class ReporteComprasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('reporte_extra')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.seller = get_user_model().objects.create_user('seller_extra')
        cls.seller.groups.add(Group.objects.get(name='Vendedor'))
        categoria = Categoria.objects.create(nombre='Extra')
        producto = Producto.objects.create(codigo='EXT-1', barras='9999999911111', nombre='Extra', categoria=categoria, condicion='Venta directa', precio=100)
        proveedor = Proveedor.objects.create(codigo='EXT', nombre='Proveedor ficticio')
        orden = OrdenCompra.objects.create(proveedor=proveedor, proveedor_nombre=proveedor.nombre, usuario=cls.admin, huella='x'*64, total=500)
        LineaOrden.objects.create(orden=orden, producto=producto, codigo=producto.codigo, nombre='=NO_ES_FORMULA()', presentacion='Caja', solicitada=5, recibida=2, costo_unitario=100)

    def test_excel_y_pdf_registran_exportacion_y_no_formulas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('operaciones:reporte_compras'), {'formato':'xlsx'})
        self.assertEqual(r.status_code, 200)
        libro = load_workbook(BytesIO(r.content))
        self.assertEqual(libro.active['D7'].value, '=NO_ES_FORMULA()')
        self.assertEqual(libro.active['D7'].data_type, 's')
        pdf = self.client.get(reverse('operaciones:reporte_compras'), {'formato':'pdf'})
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(EventoReporte.objects.filter(tipo='compras').count(), 2)

    def test_filtro_invertido_y_permiso(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('operaciones:reporte_compras'), {'desde':'2026-10-20','hasta':'2026-10-01'})
        self.assertEqual(r.status_code, 400)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(reverse('operaciones:reporte_compras')).status_code, 403)

    def test_indicadores_renderizan_periodo_sin_ventas(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('operaciones:analisis')), 'Sin actividad en este período')
