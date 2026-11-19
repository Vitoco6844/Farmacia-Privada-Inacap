from datetime import datetime, time, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.exportaciones import generar_excel, generar_pdf
from operaciones.models import DetalleVenta, EventoReporte, Existencia, Lote, Venta
from operaciones.reportes import VentasFiltro, columnas, consulta, filas, resumen


class ReportesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('admin_reportes')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.vendedor = get_user_model().objects.create_user('vendedor_reportes')
        cls.vendedor.groups.add(Group.objects.get(name='Vendedor'))
        cls.quimico = get_user_model().objects.create_user('quimico_reportes')
        cls.quimico.groups.add(Group.objects.get(name='Químico Farmacéutico'))
        categoria = Categoria.objects.create(nombre='Reportes')
        cls.producto = Producto.objects.create(codigo='REP-001', barras='9900000033333', nombre='Producto actual',
            presentacion='Caja de prueba', categoria=categoria, condicion='Venta directa', precio=9000)
        hoy = timezone.localdate()
        for codigo, dias, cantidad in [('A', 10, 8), ('B', -1, 3), ('C', 90, 0)]:
            lote = Lote.objects.create(producto=cls.producto, codigo=codigo, vencimiento=hoy + timedelta(days=dias))
            Existencia.objects.create(lote=lote, ubicacion='vitrina', cantidad=cantidad)
        cls.lote = Lote.objects.get(codigo='A')
        Existencia.objects.create(lote=cls.lote, ubicacion='bodega', cantidad=20)
        cls.venta = Venta.objects.create(usuario=cls.admin, total=2000)
        DetalleVenta.objects.create(venta=cls.venta, producto=cls.producto, nombre='Nombre histórico',
            codigo='HIST-001', precio_unitario=1000, cantidad=2)
        ayer = Venta.objects.create(usuario=cls.admin, total=3000)
        DetalleVenta.objects.create(venta=ayer, producto=cls.producto, nombre='Otro histórico',
            codigo='HIST-002', precio_unitario=3000, cantidad=1)
        limite = timezone.make_aware(datetime.combine(hoy, time.min))
        Venta.objects.filter(pk=ayer.pk).update(fecha=limite - timedelta(seconds=1))

    def login(self, usuario=None):
        self.client.force_login(usuario or self.admin)

    def test_anonimo_y_vendedor_sin_exportacion(self):
        for ruta in ['reportes', 'reporte_ventas', 'reporte_inventario']:
            self.assertEqual(self.client.get(reverse('operaciones:' + ruta)).status_code, 302)
        self.login(self.vendedor)
        for ruta in ['reportes', 'reporte_ventas', 'reporte_inventario']:
            for formato in ['', 'pdf', 'xlsx']:
                with self.subTest(ruta=ruta, formato=formato):
                    self.assertEqual(self.client.get(reverse('operaciones:' + ruta), {'formato': formato}).status_code, 403)
        self.assertEqual(EventoReporte.objects.count(), 0)

    def test_quimico_solo_inventario(self):
        self.login(self.quimico)
        self.assertRedirects(self.client.get(reverse('operaciones:reportes')), reverse('operaciones:reporte_inventario'))
        self.assertEqual(self.client.get(reverse('operaciones:reporte_ventas'), {'formato': 'xlsx'}).status_code, 403)
        self.assertEqual(self.client.get(reverse('operaciones:reporte_inventario')).status_code, 200)

    def test_fechas_inclusivas_santiago_y_valores_historicos(self):
        self.login()
        fecha = timezone.localdate().isoformat()
        r = self.client.get(reverse('operaciones:reporte_ventas'), {'desde': fecha, 'hasta': fecha})
        self.assertEqual(r.context['totales'], {'filas': 1, 'envases': 2, 'total': Decimal('2000')})
        self.assertContains(r, 'Nombre histórico')
        self.assertNotContains(r, 'Producto actual')
        self.assertNotContains(r, 'Otro histórico')

    def test_fechas_invalidas_y_formato_inexistente(self):
        self.login()
        for parametros in [{'desde': '2026-12-31', 'hasta': '2026-01-01'}, {'hasta': '9999-12-31'},
                {'desde': 'no-fecha', 'formato': 'pdf'}, {'formato': 'exe'}]:
            with self.subTest(parametros=parametros):
                self.assertEqual(self.client.get(reverse('operaciones:reporte_ventas'), parametros).status_code, 400)
        self.assertEqual(EventoReporte.objects.count(), 0)

    def test_busqueda_historica_coincide_en_pantalla_y_excel(self):
        from openpyxl import load_workbook
        self.login()
        url = reverse('operaciones:reporte_ventas')
        parametros = {'q': 'HIST-001'}
        vista = self.client.get(url, parametros)
        descarga = self.client.get(url, {**parametros, 'formato': 'xlsx'})
        ws = load_workbook(BytesIO(descarga.content)).active
        self.assertEqual(vista.context['totales']['envases'], ws['E7'].value)
        self.assertEqual(vista.context['totales']['total'], ws['G7'].value)
        self.assertEqual(ws['D7'].value, 'Nombre histórico')
        self.assertIn('HIST-001', ws['A3'].value)
        evento = EventoReporte.objects.get()
        self.assertEqual(evento.usuario, self.admin)
        self.assertEqual(evento.filtros['q'], 'HIST-001')
        self.assertEqual(evento.total, 2000)
        self.assertEqual(evento.filas, 1)

    def test_inventario_filtros_y_totales(self):
        self.login()
        url = reverse('operaciones:reporte_inventario')
        r = self.client.get(url, {'ubicacion': 'vitrina', 'estado': 'disponible'})
        self.assertEqual(r.context['totales']['envases'], 8)
        self.assertEqual(r.context['totales']['filas'], 1)
        for estado, esperado in [('vencido', 3), ('proximo', 28), ('sin_stock', 0)]:
            r = self.client.get(url, {'estado': estado})
            self.assertEqual(r.context['totales']['envases'], esperado)
        self.assertEqual(self.client.get(url, {'ubicacion': 'inventada'}).status_code, 400)

    def test_excel_inventario_fecha_y_cantidad_nativas(self):
        from openpyxl import load_workbook
        self.login()
        r = self.client.get(reverse('operaciones:reporte_inventario'), {'q': 'REP-001', 'ubicacion': 'bodega', 'formato': 'xlsx'})
        ws = load_workbook(BytesIO(r.content)).active
        self.assertEqual(ws['F7'].value, 20)
        self.assertIsInstance(ws['D7'].value, datetime)
        self.assertEqual(ws.freeze_panes, 'A7')
        self.assertEqual(ws.auto_filter.ref, 'A6:G7')
        self.assertIn('private, no-store', r['Cache-Control'])

    def test_excel_textos_peligrosos_se_conservan_sin_formulas(self):
        from openpyxl import load_workbook
        DetalleVenta.objects.filter(venta=self.venta).update(nombre='=HYPERLINK("https://example.org", "abrir")')
        self.login()
        r = self.client.get(reverse('operaciones:reporte_ventas'), {'q': 'HIST-001', 'formato': 'xlsx'})
        celda = load_workbook(BytesIO(r.content)).active['D7']
        self.assertTrue(celda.value.startswith('='))
        self.assertEqual(celda.data_type, 's')

    def test_pdf_descargable_y_auditoria(self):
        self.login()
        r = self.client.get(reverse('operaciones:reporte_ventas'), {'q': 'HIST-001', 'formato': 'pdf'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF-'))
        self.assertIn('attachment;', r['Content-Disposition'])
        self.assertTrue(EventoReporte.objects.filter(formato='pdf', filas=1).exists())

    def test_reportes_vacios_exportan(self):
        from openpyxl import load_workbook
        self.login()
        url = reverse('operaciones:reporte_ventas')
        r = self.client.get(url, {'q': 'no-existe', 'formato': 'xlsx'})
        ws = load_workbook(BytesIO(r.content)).active
        self.assertIn('Registros: 0', ws['A4'].value)
        self.assertEqual(ws['B8'].value, 0)
        self.assertTrue(self.client.get(url, {'q': 'no-existe', 'formato': 'pdf'}).content.startswith(b'%PDF-'))

    def test_limite_exportacion_no_trunca(self):
        self.login()
        with patch('operaciones.vistas_reportes.MAX_EXPORT_ROWS', 1):
            r = self.client.get(reverse('operaciones:reporte_ventas'), {'formato': 'xlsx'})
        self.assertContains(r, 'Acota los filtros', status_code=400)
        self.assertEqual(EventoReporte.objects.count(), 0)

    def test_fallo_exportacion_no_registra_generacion(self):
        self.login()
        with patch('operaciones.vistas_reportes.generar_excel', side_effect=ImportError):
            r = self.client.get(reverse('operaciones:reporte_ventas'), {'formato': 'xlsx'})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(EventoReporte.objects.count(), 0)

    def test_totales_completos_y_exportacion_no_solo_pagina(self):
        from openpyxl import load_workbook
        for _ in range(23):
            venta = Venta.objects.create(usuario=self.admin, total=100)
            DetalleVenta.objects.create(venta=venta, producto=self.producto, nombre='Extra', codigo='EXTRA', precio_unitario=100, cantidad=1)
        self.login()
        url = reverse('operaciones:reporte_ventas')
        r = self.client.get(url, {'q': 'EXTRA', 'pagina': 2})
        self.assertEqual(r.context['totales']['filas'], 23)
        self.assertEqual(len(r.context['filas_pantalla']), 3)
        descarga = self.client.get(url, {'q': 'EXTRA', 'pagina': 2, 'formato': 'xlsx'})
        ws = load_workbook(BytesIO(descarga.content)).active
        self.assertEqual(ws.auto_filter.ref, 'A6:H29')
        self.assertEqual(EventoReporte.objects.get().filas, 23)

    def test_excel_preserva_importe_superior_a_precision_numerica(self):
        from openpyxl import load_workbook
        contenido = generar_excel(titulo='Prueba', cabeceras=columnas('ventas'), datos=[], filtros='Sin filtros',
            generado='Prueba', usuario='Prueba', totales={'filas': 0, 'envases': 0, 'total': Decimal('99999999999999999')}, tipo='ventas')
        ws = load_workbook(BytesIO(contenido)).active
        self.assertEqual(ws['B9'].value, '99999999999999999')
        self.assertEqual(ws['B9'].data_type, 's')
