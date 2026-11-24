import uuid
from datetime import timedelta
from io import StringIO
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.models import Existencia, Lote, Movimiento
from compras.forms import OrdenForm, RecepcionForm
from compras.models import EventoCompra, EventoProveedor, OrdenCompra, Proveedor, Recepcion
from compras.services import anular_orden, crear_orden, recibir_orden


class ComprasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('comprador')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.vendedor = get_user_model().objects.create_user('vendedor')
        cls.vendedor.groups.add(Group.objects.get(name='Vendedor'))
        cls.tecnico = get_user_model().objects.create_user('tecnico')
        cls.tecnico.groups.add(Group.objects.get(name='Técnico en Farmacia'))
        cls.proveedor = Proveedor.objects.create(codigo='DEMO', nombre='Proveedor original')
        categoria = Categoria.objects.create(nombre='Demo compras')
        cls.producto = Producto.objects.create(codigo='P-1', barras='9900000012345', nombre='Producto original',
            presentacion='Caja', categoria=categoria, condicion='Venta directa', precio=2500)
        cls.fecha = timezone.localdate() + timedelta(days=90)

    def orden(self, **kwargs):
        datos = dict(usuario=self.admin, proveedor_id=self.proveedor.pk, observaciones='', clave=uuid.uuid4(),
            lineas=[dict(producto_id=self.producto.pk, cantidad=20, costo_unitario=1000)])
        datos.update(kwargs)
        return crear_orden(**datos)

    def partida(self, orden, cantidad=8, **kwargs):
        datos = dict(linea_id=orden.lineas.get().pk, codigo='LOTE-A', vencimiento=self.fecha,
            ubicacion='bodega', cantidad=cantidad)
        datos.update(kwargs)
        return datos

    def recibir(self, orden, cantidad=8, **kwargs):
        datos = dict(usuario=self.admin, orden_id=orden.pk, referencia='GUIA-1', clave=uuid.uuid4(),
            partidas=kwargs.pop('partidas') if 'partidas' in kwargs else [self.partida(orden, cantidad)])
        datos.update(kwargs)
        return recibir_orden(**datos)

    def test_orden_no_genera_stock_y_conserva_historial(self):
        orden = self.orden()
        self.assertEqual(orden.total, Decimal('20000'))
        self.assertFalse(Existencia.objects.exists())
        self.assertEqual(orden.eventos.get().accion, 'crear')
        self.producto.nombre = 'Renombrado'
        self.producto.precio = 9999
        self.producto.save()
        self.proveedor.nombre = 'Otro nombre'
        self.proveedor.save()
        orden.refresh_from_db()
        self.assertEqual(orden.proveedor_nombre, 'Proveedor original')
        self.assertEqual(orden.lineas.get().nombre, 'Producto original')
        self.assertEqual(orden.lineas.get().costo_unitario, 1000)

    def test_orden_reintento_una_sola_orden(self):
        clave = uuid.uuid4()
        self.assertEqual(self.orden(clave=clave).pk, self.orden(clave=clave).pk)
        self.assertEqual(OrdenCompra.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.orden(clave=clave, observaciones='Datos distintos')

    def test_orden_rechaza_producto_duplicado(self):
        linea = dict(producto_id=self.producto.pk, cantidad=2, costo_unitario=10)
        with self.assertRaises(ValidationError):
            self.orden(lineas=[linea, linea])

    def test_orden_costos_invalidos(self):
        for costo in [-1, '1.5', 'NaN', 'Infinity', 1000000000000]:
            with self.subTest(costo=costo), self.assertRaises(ValidationError):
                self.orden(lineas=[dict(producto_id=self.producto.pk, cantidad=1, costo_unitario=costo)])

    def test_orden_cantidades_invalidas(self):
        for cantidad in [0, -1, True, 1.5, 1000001]:
            with self.subTest(cantidad=cantidad), self.assertRaises(ValidationError):
                self.orden(lineas=[dict(producto_id=self.producto.pk, cantidad=cantidad, costo_unitario=10)])

    def test_proveedor_inactivo_no_admite_orden_nueva(self):
        self.proveedor.activo = False
        self.proveedor.save()
        with self.assertRaises(ValidationError):
            self.orden()

    def test_producto_inactivo_no_admite_orden(self):
        self.producto.activo = False
        self.producto.save()
        with self.assertRaises(ValidationError):
            self.orden()

    def test_dos_recepciones_completan_y_suman_solo_lo_recibido(self):
        orden = self.orden()
        self.recibir(orden)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'parcial')
        self.assertEqual(orden.lineas.get().pendiente, 12)
        self.assertEqual(Existencia.objects.get().cantidad, 8)
        self.recibir(orden, 12, referencia='GUIA-2')
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'completa')
        self.assertEqual(orden.lineas.get().pendiente, 0)
        self.assertEqual(Existencia.objects.get().cantidad, 20)
        self.assertEqual(Movimiento.objects.count(), 2)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, 2500)

    def test_reintento_despues_de_completar_no_duplica(self):
        orden = self.orden()
        clave = uuid.uuid4()
        primera = self.recibir(orden, 20, clave=clave)
        self.assertEqual(self.recibir(orden, 20, clave=clave).pk, primera.pk)
        self.assertEqual(Existencia.objects.get().cantidad, 20)
        self.assertEqual(Recepcion.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.recibir(orden, 19, clave=clave)

    def test_referencia_se_normaliza_y_rechaza_duplicados(self):
        orden = self.orden()
        self.recibir(orden, referencia='  guia-1 ')
        with self.assertRaises(ValidationError):
            self.recibir(orden, referencia='GUIA-1')
        self.assertEqual(Existencia.objects.get().cantidad, 8)

    def test_exceso_sumado_entre_lotes_se_rechaza(self):
        orden = self.orden()
        with self.assertRaises(ValidationError):
            self.recibir(orden, partidas=[self.partida(orden, 12), self.partida(orden, 9, codigo='LOTE-B')])
        self.assertFalse(Recepcion.objects.exists())
        self.assertFalse(Existencia.objects.exists())

    def test_recepcion_distribuye_lotes_y_ubicaciones(self):
        orden = self.orden()
        self.recibir(orden, partidas=[self.partida(orden, 4), self.partida(orden, 6, codigo='LOTE-B', ubicacion='vitrina')])
        self.assertEqual(list(Existencia.objects.order_by('cantidad').values_list('cantidad', flat=True)), [4, 6])
        self.assertEqual(orden.lineas.get().pendiente, 10)

    def test_rechaza_partida_identica_y_linea_de_otra_orden(self):
        orden, otra = self.orden(), self.orden()
        for partidas in [[self.partida(orden), self.partida(orden)], [self.partida(otra)]]:
            with self.assertRaises(ValidationError):
                self.recibir(orden, partidas=partidas)
        self.assertFalse(Recepcion.objects.exists())

    def test_rechaza_vencido_hoy_bloqueado_o_inactivo(self):
        orden = self.orden()
        for fecha in [timezone.localdate(), timezone.localdate() - timedelta(days=1)]:
            with self.assertRaises(ValidationError):
                self.recibir(orden, partidas=[self.partida(orden, vencimiento=fecha)])
        lote = Lote.objects.create(producto=self.producto, codigo='LOTE-A', vencimiento=self.fecha, bloqueado=True)
        with self.assertRaises(ValidationError):
            self.recibir(orden)
        lote.bloqueado = False
        lote.save()
        self.producto.activo = False
        self.producto.save()
        with self.assertRaises(ValidationError):
            self.recibir(orden)

    def test_fallo_segunda_partida_revierte_todo(self):
        orden = self.orden()
        Lote.objects.create(producto=self.producto, codigo='Z-EXISTENTE', vencimiento=self.fecha + timedelta(days=1))
        with self.assertRaises(ValidationError):
            self.recibir(orden, partidas=[self.partida(orden, 3, codigo='A-NUEVO'),
                self.partida(orden, 4, codigo='Z-EXISTENTE')])
        self.assertFalse(Recepcion.objects.exists())
        self.assertFalse(Movimiento.objects.exists())
        self.assertFalse(Lote.objects.filter(codigo='A-NUEVO').exists())
        self.assertEqual(orden.lineas.get().recibida, 0)
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'pendiente')

    def test_proveedor_desactivado_permite_recibir_orden_previa(self):
        orden = self.orden()
        self.proveedor.activo = False
        self.proveedor.save()
        self.recibir(orden)
        self.assertEqual(Existencia.objects.get().cantidad, 8)

    def test_anulacion_con_motivo_sin_borrado(self):
        orden = self.orden()
        with self.assertRaises(ValidationError):
            anular_orden(usuario=self.admin, orden_id=orden.pk, motivo='corto')
        for _ in range(2):
            anular_orden(usuario=self.admin, orden_id=orden.pk, motivo='Proveedor sin disponibilidad')
        self.assertEqual(EventoCompra.objects.filter(accion='anular').count(), 1)
        with self.assertRaises(ValidationError):
            self.recibir(orden)

    def test_no_anula_orden_parcial(self):
        orden = self.orden()
        self.recibir(orden)
        with self.assertRaises(ValidationError):
            anular_orden(usuario=self.admin, orden_id=orden.pk, motivo='Cancelar compra parcial')

    def test_permisos_en_servicios(self):
        orden = self.orden()
        with self.assertRaises(PermissionDenied):
            self.orden(usuario=self.vendedor)
        with self.assertRaises(PermissionDenied):
            self.recibir(orden, usuario=self.vendedor)
        self.recibir(orden, usuario=self.tecnico)
        self.admin.is_active = False
        self.admin.save()
        with self.assertRaises(PermissionDenied):
            self.recibir(orden, referencia='GUIA-2')

    def test_restriccion_bd_cantidad_recibida(self):
        linea = self.orden().lineas.get()
        with self.assertRaises(IntegrityError), transaction.atomic():
            linea.recibida = 21
            linea.save()

    def test_paginas_y_permisos_http(self):
        orden = self.orden()
        recepcion = self.recibir(orden)
        urls = ['/compras/', '/compras/nueva/', f'/compras/ordenes/{orden.pk}/',
            f'/compras/ordenes/{orden.pk}/recibir/', f'/compras/recepciones/{recepcion.pk}/',
            '/compras/proveedores/', '/compras/proveedores/nuevo/', f'/compras/proveedores/{self.proveedor.pk}/editar/']
        self.client.force_login(self.admin)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(f'/compras/ordenes/{orden.pk}/anular/').status_code, 405)
        self.client.force_login(self.vendedor)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_post_orden_y_recepcion_doble_envio(self):
        self.client.force_login(self.admin)
        token = OrdenForm(usuario=self.admin, tipo='orden').initial['token']
        datos = {'token': token, 'proveedor': self.proveedor.pk, 'observaciones': '',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0', 'lineas-0-producto': self.producto.pk,
            'lineas-0-cantidad': '20', 'lineas-0-costo_unitario': '1000'}
        for _ in range(2):
            self.assertEqual(self.client.post('/compras/nueva/', datos).status_code, 302)
        orden = OrdenCompra.objects.get()
        token = RecepcionForm(usuario=self.admin, tipo=f'recepcion:{orden.pk}').initial['token']
        datos = {'token': token, 'referencia': 'HTTP-1', 'partidas-TOTAL_FORMS': '1', 'partidas-INITIAL_FORMS': '0',
            'partidas-0-linea': orden.lineas.get().pk, 'partidas-0-codigo': 'HTTP-LOTE',
            'partidas-0-vencimiento': self.fecha.isoformat(), 'partidas-0-ubicacion': 'bodega', 'partidas-0-cantidad': '20'}
        for _ in range(2):
            self.assertEqual(self.client.post(f'/compras/ordenes/{orden.pk}/recibir/', datos).status_code, 302)
        self.assertEqual(Recepcion.objects.count(), 1)
        self.assertEqual(Existencia.objects.get().cantidad, 20)

    def test_formulario_recepcion_oculto_en_orden_completa_o_anulada(self):
        self.client.force_login(self.admin)
        abierta = self.orden()
        respuesta = self.client.get(f'/compras/ordenes/{abierta.pk}/recibir/')
        self.assertContains(respuesta, 'Registrar recepción')
        self.assertNotContains(respuesta, 'no admite nuevas recepciones')
        completa = self.orden(clave=uuid.uuid4())
        self.recibir(completa, 20)
        anulada = self.orden(clave=uuid.uuid4())
        anular_orden(usuario=self.admin, orden_id=anulada.pk, motivo='Proveedor sin disponibilidad')
        for orden in (completa, anulada):
            with self.subTest(estado=orden.estado):
                respuesta = self.client.get(f'/compras/ordenes/{orden.pk}/recibir/')
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, 'no admite nuevas recepciones')
                self.assertNotContains(respuesta, 'Registrar recepción')
                self.assertNotContains(respuesta, 'partidas-TOTAL_FORMS')

    def test_token_invalido_no_crea_orden(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post('/compras/nueva/', {'token': 'alterado'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(OrdenCompra.objects.exists())

    def test_proveedor_edicion_auditada(self):
        orden = self.orden()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(f'/compras/proveedores/{self.proveedor.pk}/editar/',
            {'codigo': 'DEMO', 'nombre': 'Nuevo proveedor', 'email': '', 'telefono': ''}).status_code, 302)
        evento = EventoProveedor.objects.get()
        self.assertEqual(evento.anterior['nombre'], 'Proveedor original')
        self.assertFalse(evento.posterior['activo'])
        orden.refresh_from_db()
        self.assertEqual(orden.proveedor_nombre, 'Proveedor original')

    def test_seed_no_reactiva_ni_sobrescribe(self):
        call_command('cargar_proveedores_demo', stdout=StringIO())
        proveedor = Proveedor.objects.get(codigo='PROV-DEMO-01')
        proveedor.activo = False
        proveedor.nombre = 'Personalizado'
        proveedor.save()
        call_command('cargar_proveedores_demo', stdout=StringIO())
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)
        self.assertEqual(proveedor.nombre, 'Personalizado')

    def test_orden_varios_productos_solo_completa_al_recibir_todos(self):
        otro = Producto.objects.create(codigo='P-2', barras='9900000012346', nombre='Segundo',
            presentacion='Frasco', categoria=self.producto.categoria, precio=5000, condicion='Venta directa')
        orden = self.orden(lineas=[dict(producto_id=self.producto.pk, cantidad=4, costo_unitario=1000),
            dict(producto_id=otro.pk, cantidad=6, costo_unitario=2000)])
        primera, segunda = list(orden.lineas.all())
        self.recibir(orden, partidas=[dict(linea_id=primera.pk, codigo='MULTI-A', vencimiento=self.fecha,
            ubicacion='bodega', cantidad=4)])
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'parcial')
        self.assertEqual(orden.total, 16000)
        self.recibir(orden, referencia='MULTI-2', partidas=[dict(linea_id=segunda.pk, codigo='MULTI-B',
            vencimiento=self.fecha, ubicacion='bodega', cantidad=6)])
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'completa')

    def test_csrf_obligatorio_en_recepcion(self):
        from django.test import Client
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        orden = self.orden()
        self.assertEqual(cliente.post(f'/compras/ordenes/{orden.pk}/recibir/', {}).status_code, 403)
        self.assertFalse(Recepcion.objects.exists())

    def test_historial_admin_sin_edicion_ni_borrado(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from compras.admin import EventoCompraAdmin
        registro = EventoCompraAdmin(EventoCompra, admin.site)
        request = RequestFactory().get('/administracion/')
        request.user = self.admin
        self.assertFalse(registro.has_add_permission(request))
        self.assertFalse(registro.has_change_permission(request))
        self.assertFalse(registro.has_delete_permission(request))
