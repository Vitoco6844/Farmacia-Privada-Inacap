import uuid
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from catalogo.models import Categoria, Producto
from operaciones.forms import IngresoForm, VentaForm
from operaciones.models import DetalleVenta, Existencia, Lote, Movimiento, Venta
from operaciones.services import confirmar_venta, registrar_ingreso, transferir


class OperacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('admin_operaciones')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.vendedor = get_user_model().objects.create_user('vendedor_operaciones')
        cls.vendedor.groups.add(Group.objects.get(name='Vendedor'))
        cls.tecnico = get_user_model().objects.create_user('tecnico_operaciones')
        cls.tecnico.groups.add(Group.objects.get(name='Técnico en Farmacia'))
        cls.categoria = Categoria.objects.create(nombre='Medicamentos')
        cls.producto = Producto.objects.create(codigo='TEST-001', barras='9900000011111', nombre='Prueba',
            presentacion='Envase ficticio', categoria=cls.categoria, condicion='Venta directa', precio=1000)
        hoy = timezone.localdate()
        cls.cercano = Lote.objects.create(producto=cls.producto, codigo='CERCANO', vencimiento=hoy + timedelta(days=10))
        cls.largo = Lote.objects.create(producto=cls.producto, codigo='LARGO', vencimiento=hoy + timedelta(days=180))
        cls.vencido = Lote.objects.create(producto=cls.producto, codigo='VENCIDO', vencimiento=hoy - timedelta(days=1))
        cls.hoy = Lote.objects.create(producto=cls.producto, codigo='HOY', vencimiento=hoy)
        cls.bloqueado = Lote.objects.create(producto=cls.producto, codigo='BLOQUEADO', vencimiento=hoy + timedelta(days=2), bloqueado=True)
        for lote, ubicacion, cantidad in [(cls.cercano, 'vitrina', 3), (cls.largo, 'vitrina', 10),
                (cls.largo, 'bodega', 20), (cls.vencido, 'vitrina', 40), (cls.hoy, 'vitrina', 40), (cls.bloqueado, 'vitrina', 40)]:
            Existencia.objects.create(lote=lote, ubicacion=ubicacion, cantidad=cantidad)

    def venta(self, **datos):
        return confirmar_venta(**{'usuario': self.vendedor, 'producto_id': self.producto.pk,
            'cantidad': 5, 'clave': uuid.uuid4(), **datos})

    def ingreso(self, **datos):
        return registrar_ingreso(**{'usuario': self.admin, 'producto_id': self.producto.pk,
            'codigo': 'NUEVO', 'vencimiento': timezone.localdate() + timedelta(days=90),
            'ubicacion': 'bodega', 'cantidad': 4, 'clave': uuid.uuid4(), **datos})

    def traslado(self, **datos):
        return transferir(**{'usuario': self.tecnico, 'lote_id': self.largo.pk,
            'origen': 'bodega', 'destino': 'vitrina', 'cantidad': 5, 'clave': uuid.uuid4(), **datos})

    def test_fefo_reparte_y_excluye_vencidos_hoy_bloqueados_bodega(self):
        venta = self.venta()
        detalle = venta.detalles.get()
        asignaciones = dict(detalle.asignaciones.values_list('lote__codigo', 'cantidad'))
        self.assertEqual(asignaciones, {'CERCANO': 3, 'LARGO': 2})
        self.assertEqual(venta.total, Decimal('5000'))
        self.assertEqual(Existencia.objects.get(lote=self.largo, ubicacion='bodega').cantidad, 20)
        for lote in [self.vencido, self.hoy, self.bloqueado]:
            self.assertEqual(Existencia.objects.get(lote=lote, ubicacion='vitrina').cantidad, 40)

    def test_reintento_venta_no_duplica_ni_actualiza_precio_historico(self):
        clave = uuid.uuid4()
        a = self.venta(clave=clave)
        Producto.objects.filter(pk=self.producto.pk).update(precio=2000, nombre='Nombre cambiado')
        b = self.venta(clave=clave)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(Venta.objects.count(), 1)
        detalle = b.detalles.get()
        self.assertEqual(detalle.nombre, 'Prueba')
        self.assertEqual(detalle.precio_unitario, 1000)
        self.assertEqual(detalle.asignaciones.count(), 2)

    def test_reintento_con_cantidad_distinta_se_rechaza(self):
        clave = uuid.uuid4()
        self.venta(clave=clave)
        with self.assertRaises(ValidationError):
            self.venta(clave=clave, cantidad=1)
        self.assertEqual(Venta.objects.count(), 1)

    def test_sin_stock_no_hay_venta_ni_descuento(self):
        with self.assertRaises(ValidationError):
            self.venta(cantidad=14)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(Existencia.objects.get(lote=self.cercano, ubicacion='vitrina').cantidad, 3)

    def test_cantidades_invalidas(self):
        for cantidad in [0, -1, 1.5, True, 1000001]:
            with self.subTest(cantidad=cantidad), self.assertRaises(ValidationError):
                self.venta(cantidad=cantidad)

    def test_importe_fuera_de_limite_se_rechaza(self):
        Producto.objects.filter(pk=self.producto.pk).update(precio=999999999999)
        with self.assertRaises(ValidationError):
            self.venta(cantidad=1000000)
        self.assertEqual(Venta.objects.count(), 0)

    def test_receta_y_condicion_pendiente_no_se_venden(self):
        for condicion in ['Receta simple', 'Receta retenida', 'Por verificar']:
            Producto.objects.filter(pk=self.producto.pk).update(condicion=condicion)
            with self.subTest(condicion=condicion), self.assertRaises(ValidationError):
                self.venta()

    def test_producto_inactivo_no_se_vende(self):
        Producto.objects.filter(pk=self.producto.pk).update(activo=False)
        with self.assertRaises(ValidationError):
            self.venta()

    def test_fallo_movimiento_revierte_venta_y_stock(self):
        with patch('operaciones.services.Movimiento.objects.create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                self.venta()
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(DetalleVenta.objects.count(), 0)
        self.assertEqual(Existencia.objects.get(lote=self.cercano, ubicacion='vitrina').cantidad, 3)

    def test_traslado_conserva_total_y_es_idempotente(self):
        clave = uuid.uuid4()
        a = self.traslado(clave=clave)
        b = self.traslado(clave=clave)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(Existencia.objects.get(lote=self.largo, ubicacion='bodega').cantidad, 15)
        self.assertEqual(Existencia.objects.get(lote=self.largo, ubicacion='vitrina').cantidad, 15)
        self.assertEqual(Movimiento.objects.count(), 1)

    def test_traslado_insuficiente_o_mismo_destino(self):
        for datos in [{'cantidad': 21}, {'destino': 'bodega'}, {'origen': 'desconocido'}, {'lote_id': self.vencido.pk}]:
            with self.subTest(datos=datos), self.assertRaises(ValidationError):
                self.traslado(**datos)
        self.assertEqual(Movimiento.objects.count(), 0)

    def test_ingreso_normaliza_lote_y_no_duplica(self):
        clave = uuid.uuid4()
        a = self.ingreso(clave=clave, codigo=' nuevo ')
        b = self.ingreso(clave=clave)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(a.lote.codigo, 'NUEVO')
        self.assertEqual(Existencia.objects.get(lote=a.lote, ubicacion='bodega').cantidad, 4)

    def test_lote_existente_no_admite_otro_vencimiento(self):
        with self.assertRaises(ValidationError):
            self.ingreso(codigo='LARGO')

    def test_reintento_ingreso_no_acepta_otros_datos(self):
        clave = uuid.uuid4()
        self.ingreso(clave=clave)
        with self.assertRaises(ValidationError):
            self.ingreso(clave=clave, cantidad=8)

    def test_base_protege_cantidades_y_ubicaciones(self):
        for cambios in [{'cantidad': -1}, {'ubicacion': 'inventada'}]:
            with self.subTest(cambios=cambios), self.assertRaises(IntegrityError), transaction.atomic():
                Existencia.objects.filter(lote=self.cercano).update(**cambios)

    def test_servicios_comprueban_permisos(self):
        with self.assertRaises(PermissionDenied):
            self.ingreso(usuario=self.vendedor)
        with self.assertRaises(PermissionDenied):
            self.traslado(usuario=self.vendedor)
        with self.assertRaises(PermissionDenied):
            self.venta(usuario=self.tecnico)

    def test_actor_desactivado_no_opera(self):
        get_user_model().objects.filter(pk=self.vendedor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.venta()

    def test_formulario_firmado_por_usuario_tipo_y_contenido(self):
        token = VentaForm(usuario=self.vendedor, tipo='venta').initial['token']
        datos = {'producto': self.producto.pk, 'cantidad': 1, 'token': token}
        self.assertTrue(VentaForm(datos, usuario=self.vendedor, tipo='venta').is_valid())
        self.assertFalse(VentaForm(datos, usuario=self.admin, tipo='venta').is_valid())
        self.assertFalse(IngresoForm(datos, usuario=self.vendedor, tipo='ingreso').is_valid())
        self.assertFalse(VentaForm({**datos, 'token': token + 'x'}, usuario=self.vendedor, tipo='venta').is_valid())

    def test_post_venta_y_reintento_por_http(self):
        import json
        from comercio.services import abrir_caja
        self.client.force_login(self.vendedor)
        caja = abrir_caja(usuario=self.vendedor, fondo=0)
        url = reverse('operaciones:nueva_venta')
        clave = str(self.client.get(url).context['clave'])
        datos = {'items': json.dumps([{'producto_id': self.producto.pk, 'cantidad': 2}]),
                 'clave': clave, 'caja_id': caja.pk, 'medio': 'efectivo', 'precio': '1'}
        r = self.client.post(url, datos)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.post(url, datos).url, r.url)
        venta = Venta.objects.get()
        self.assertEqual(venta.total, 2000)
        self.assertContains(self.client.get(r.url), 'SIN VALIDEZ TRIBUTARIA')

    def test_errores_sin_perder_datos_en_venta(self):
        import json
        from comercio.services import abrir_caja
        self.client.force_login(self.vendedor)
        caja = abrir_caja(usuario=self.vendedor, fondo=0)
        url = reverse('operaciones:nueva_venta')
        clave = str(self.client.get(url).context['clave'])
        items = json.dumps([{'producto_id': self.producto.pk, 'cantidad': 100}])
        r = self.client.post(url, {'items': items, 'clave': clave, 'caja_id': caja.pk, 'medio': 'efectivo'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'stock vigente insuficiente')
        self.assertEqual(r.context['items_iniciales'], items)
        self.assertEqual(Venta.objects.count(), 0)

    def test_vistas_por_permiso_y_anonimo(self):
        self.assertEqual(self.client.get(reverse('operaciones:inventario')).status_code, 302)
        self.client.force_login(self.vendedor)
        for name in ['inventario', 'ventas', 'nueva_venta']:
            self.assertEqual(self.client.get(reverse(f'operaciones:{name}')).status_code, 200)
        for name in ['ingreso', 'traslado', 'movimientos']:
            self.assertEqual(self.client.get(reverse(f'operaciones:{name}')).status_code, 403)
        self.client.force_login(self.tecnico)
        self.assertEqual(self.client.get(reverse('operaciones:nueva_venta')).status_code, 403)

    def test_filtros_inventario_y_pantallas_admin(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('operaciones:inventario'), {'q': self.producto.codigo, 'ubicacion': 'vitrina', 'estado': 'disponible'})
        self.assertEqual(r.context['pagina'].paginator.count, 2)
        self.assertEqual(r.context['total'], 13)
        for name in ['ingreso', 'traslado', 'movimientos']:
            self.assertEqual(self.client.get(reverse(f'operaciones:{name}')).status_code, 200)

    def test_csrf_impide_confirmar_venta(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.vendedor)
        token = VentaForm(usuario=self.vendedor, tipo='venta').initial['token']
        r = client.post(reverse('operaciones:nueva_venta'), {'producto': self.producto.pk, 'cantidad': 1, 'token': token})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Venta.objects.count(), 0)
