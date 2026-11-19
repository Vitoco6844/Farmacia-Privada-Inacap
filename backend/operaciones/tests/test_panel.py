from datetime import datetime, time, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.indicadores import construir_panel, productos_bajo_minimo
from operaciones.models import Existencia, Lote, Venta


class PanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('panel_admin')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.tecnico = get_user_model().objects.create_user('panel_tecnico')
        cls.tecnico.groups.add(Group.objects.get(name='Técnico en Farmacia'))
        cls.categoria = Categoria.objects.create(nombre='Panel')

    def producto(self, codigo, **campos):
        return Producto.objects.create(codigo=codigo, barras=f'99000000{int(codigo[-3:]):05}', nombre=codigo,
            presentacion='Envase demo', categoria=self.categoria, condicion='Venta directa', precio=1000, **campos)

    def stock(self, producto, codigo, dias, cantidad, ubicacion='vitrina', bloqueado=False):
        lote = Lote.objects.create(producto=producto, codigo=codigo,
            vencimiento=timezone.localdate() + timedelta(days=dias), bloqueado=bloqueado)
        Existencia.objects.create(lote=lote, ubicacion=ubicacion, cantidad=cantidad)
        return lote

    def test_producto_sin_lotes_incluido_e_inactivo_excluido(self):
        p = self.producto('PNL-001')
        self.producto('PNL-002', activo=False)
        self.assertEqual(list(productos_bajo_minimo().values_list('pk', flat=True)), [p.pk])
        self.assertEqual(productos_bajo_minimo().get().disponible, 0)

    def test_minimo_suma_ubicaciones_y_excluye_vencidos_bloqueados(self):
        p = self.producto('PNL-001', stock_minimo=10)
        lote = self.stock(p, 'A', 10, 4)
        Existencia.objects.create(lote=lote, ubicacion='bodega', cantidad=6)
        self.stock(p, 'B', -1, 100)
        self.stock(p, 'C', 0, 100)
        self.stock(p, 'D', 5, 100, bloqueado=True)
        self.assertEqual(productos_bajo_minimo().get().disponible, 10)
        Existencia.objects.filter(lote=lote, ubicacion='bodega').update(cantidad=7)
        self.assertFalse(productos_bajo_minimo().exists())

    def test_alerta_lote_se_cuenta_una_vez_y_sin_stock_no_alerta(self):
        p = self.producto('PNL-001')
        lote = self.stock(p, 'CERCA', 60, 2)
        Existencia.objects.create(lote=lote, ubicacion='bodega', cantidad=3)
        self.stock(p, 'FUERA', 61, 10)
        self.stock(p, 'SIN-STOCK', 10, 0)
        self.stock(p, 'VENCIDO', -1, 4)
        self.stock(p, 'HOY', 0, 2)
        datos = construir_panel(ver_comercial=False)
        self.assertEqual(datos['proximos_total'], 1)
        self.assertEqual(datos['proximos'][0].envases, 5)
        self.assertEqual(datos['vencidos_total'], 2)

    def test_ventas_del_dia_segun_santiago_y_siete_dias(self):
        hoy = timezone.localdate()
        inicio = timezone.make_aware(datetime.combine(hoy, time.min))
        for fecha, total in [(inicio - timedelta(seconds=1), 50), (inicio, 100),
                (inicio + timedelta(hours=12), 200), (inicio + timedelta(days=1), 400)]:
            venta = Venta.objects.create(usuario=self.admin, total=total)
            Venta.objects.filter(pk=venta.pk).update(fecha=fecha)
        datos = construir_panel(ver_comercial=True)
        self.assertEqual(datos['ventas_hoy'], 2)
        self.assertEqual(datos['importe_hoy'], Decimal('300'))
        self.assertEqual(len(datos['dias']), 7)
        self.assertEqual(datos['dias'][-1]['total'], Decimal('300'))
        self.assertEqual(datos['dias'][-2]['total'], Decimal('50'))

    def test_sin_ventas_ceros_son_datos_validos(self):
        datos = construir_panel(ver_comercial=True)
        self.assertEqual(datos['ventas_hoy'], 0)
        self.assertEqual(datos['importe_hoy'], 0)
        self.assertTrue(all(d['ancho'] == 0 for d in datos['dias']))

    def test_permiso_comercial_oculta_datos_y_consultas(self):
        datos = construir_panel(ver_comercial=False)
        for campo in ['ventas_hoy', 'importe_hoy', 'ultimas_ventas', 'dias']:
            self.assertNotIn(campo, datos)
        self.client.force_login(self.tecnico)
        r = self.client.get(reverse('operaciones:panel'))
        self.assertContains(r, 'Reposición prioritaria')
        self.assertNotContains(r, 'Importe vendido hoy')
        self.assertNotContains(r, 'Últimas ventas')

    def test_error_no_se_presenta_como_stock_cero(self):
        self.client.force_login(self.admin)
        with patch('operaciones.views.construir_panel', side_effect=DatabaseError):
            r = self.client.get(reverse('operaciones:panel'))
        self.assertContains(r, 'No pudimos consultar', status_code=503)
        self.assertNotContains(r, 'Productos bajo mínimo', status_code=503)

    def test_panel_alertas_y_permisos_por_url(self):
        self.assertEqual(self.client.get(reverse('operaciones:panel')).status_code, 302)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('operaciones:panel')), 'Importe vendido hoy')
        self.assertEqual(self.client.get(reverse('operaciones:alertas_stock')).status_code, 200)
        self.admin.groups.clear()
        self.assertEqual(self.client.get(reverse('operaciones:panel')).status_code, 403)
