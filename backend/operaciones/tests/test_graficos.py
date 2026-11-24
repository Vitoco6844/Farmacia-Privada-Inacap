"""Gráficos del panel del turno: cálculos y presentación en Django y en la API del frontend."""
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalogo.models import Categoria, Producto
from comercio.models import Cobro
from comercio.services import abrir_caja, confirmar_venta
from operaciones.graficos import porcentaje
from operaciones.indicadores import construir_panel
from operaciones.models import Existencia, Lote, Venta


class GraficosPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('admin_graficos')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.tecnico = get_user_model().objects.create_user('tecnico_graficos')
        cls.tecnico.groups.add(Group.objects.get(name='Técnico en Farmacia'))
        categoria = Categoria.objects.create(nombre='Gráficos')
        hoy = timezone.localdate()

        def producto(codigo, vitrina, minimo):
            p = Producto.objects.create(codigo=codigo, barras='99' + codigo[-6:].rjust(6, '0'), nombre=f'Producto {codigo}',
                presentacion='Caja', categoria=categoria, condicion=Producto.Condicion.DIRECTA, precio=1000, stock_minimo=minimo)
            lote = Lote.objects.create(producto=p, codigo='L', vencimiento=hoy + timedelta(days=200))
            Existencia.objects.create(lote=lote, ubicacion='vitrina', cantidad=vitrina)
            return p
        cls.ok = producto('G-100001', 20, 5)
        cls.bajo = producto('G-100002', 3, 5)
        cls.agotado = producto('G-100003', 0, 5)

    def vender(self, cantidad, medio):
        caja = abrir_caja(usuario=self.admin, fondo=0) if not hasattr(self, 'caja') else self.caja
        self.caja = caja
        return confirmar_venta(usuario=self.admin, items=[{'producto_id': self.ok.pk, 'cantidad': cantidad}],
                               clave=uuid.uuid4(), caja_id=caja.pk, medio=medio)

    def test_porcentaje_minimo_visible_y_ceros(self):
        self.assertEqual(porcentaje(0, 100), 0)
        self.assertEqual(porcentaje(1, 1000), 2)
        self.assertEqual(porcentaje(50, 100), 50)
        self.assertEqual(porcentaje(5, 0), 0)

    def test_estado_vitrina_clasifica_productos(self):
        vitrina = {g['clave']: g for g in construir_panel(ver_comercial=False)['vitrina']}
        self.assertEqual(vitrina['ok']['cantidad'], 1)
        self.assertEqual(vitrina['bajo']['cantidad'], 1)
        self.assertEqual(vitrina['agotado']['cantidad'], 1)
        self.assertIn('G-100003', vitrina['agotado']['detalle'])
        self.assertEqual(sum(g['porcentaje'] for g in vitrina.values()), 99)  # 33 % cada uno, redondeado

    def test_horas_semana_y_pagos_cuadran_con_las_ventas(self):
        self.vender(2, 'efectivo')
        self.vender(1, 'tarjeta')
        datos = construir_panel(ver_comercial=True)
        self.assertEqual(sum(h['total'] for h in datos['horas']), Decimal('3000'))
        self.assertEqual(sum(h['cantidad'] for h in datos['horas']), 2)
        self.assertTrue(datos['pico'])
        self.assertEqual(datos['dias'][-1]['etiqueta'], 'Hoy')
        self.assertTrue(datos['dias'][-1]['es_hoy'])
        self.assertEqual(datos['dias'][-1]['alto'], 100)
        pagos = {p['clave']: p for p in datos['pagos']}
        self.assertEqual(pagos['efectivo']['total'], Decimal('2000'))
        self.assertEqual(pagos['tarjeta']['total'], Decimal('1000'))
        self.assertEqual(pagos['transferencia']['total'], Decimal('0'))
        self.assertEqual((pagos['efectivo']['porcentaje'], pagos['tarjeta']['porcentaje']), (67, 33))
        self.assertEqual(pagos['efectivo']['ancho'], 100)

    def test_horas_rellenan_huecos_hasta_la_hora_actual(self):
        venta = self.vender(1, 'efectivo')
        zona = timezone.get_current_timezone()
        hoy = timezone.localdate()
        temprano = timezone.make_aware(datetime.combine(hoy, time(0, 30)), zona)
        Venta.objects.filter(pk=venta.pk).update(fecha=temprano)
        horas = construir_panel(ver_comercial=True)['horas']
        self.assertEqual(horas[0]['etiqueta'], '00')
        self.assertEqual(horas[-1]['etiqueta'], f'{timezone.localtime().hour:02d}')
        self.assertEqual(len(horas), timezone.localtime().hour + 1)

    def test_sin_ventas_muestra_estados_vacios(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get('/inicio/')
        self.assertContains(respuesta, 'Todavía no hay ventas hoy')
        self.assertContains(respuesta, 'Sin pagos registrados hoy')
        self.assertContains(respuesta, 'Estado de la vitrina')

    def test_panel_django_muestra_graficos_segun_permiso(self):
        self.vender(1, 'efectivo')
        self.client.force_login(self.admin)
        respuesta = self.client.get('/inicio/')
        for texto in ['Ventas por hora', 'Última semana', 'Estado de la vitrina', 'Cómo pagaron hoy', 'Ver datos como tabla']:
            self.assertContains(respuesta, texto)
        self.client.force_login(self.tecnico)
        respuesta = self.client.get('/inicio/')
        self.assertContains(respuesta, 'Estado de la vitrina')
        self.assertNotContains(respuesta, 'Ventas por hora')
        self.assertNotContains(respuesta, 'Cómo pagaron hoy')

    def test_api_frontend_entrega_graficos(self):
        self.vender(1, 'transferencia')
        self.client.force_login(self.admin)
        datos = self.client.get('/api/v1/operaciones/panel/').json()
        self.assertEqual(datos['titulo'], 'Turno de hoy')
        self.assertEqual([g['tipo'] for g in datos['graficos']], ['columnas', 'columnas', 'segmentos', 'barras'])
        semana = datos['graficos'][1]
        self.assertTrue(semana['items'][-1]['destacado'])
        self.assertEqual(semana['items'][-1]['valor'], '$ 1.000')
        self.client.force_login(self.tecnico)
        datos = self.client.get('/api/v1/operaciones/panel/').json()
        self.assertEqual([g['tipo'] for g in datos['graficos']], ['segmentos'])
        self.assertTrue(Cobro.objects.exists())
