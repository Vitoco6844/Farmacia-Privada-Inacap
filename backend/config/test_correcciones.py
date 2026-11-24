"""Regresiones de las correcciones del 23/11/2026: RUT, errores 500, adjuntos, ingreso vencido, recetas,
reactivación, condición de venta, categorías, convenios y auditoría."""
import uuid
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from catalogo.models import Categoria, EventoCatalogo, Producto
from clinica.forms import PacienteForm, PrescriptorForm
from clinica.models import AdjuntoReceta, AsientoControlado, LineaReceta, Paciente, Prescriptor, Receta
from clinica.services import revisar_receta
from comercio.services import abrir_caja, confirmar_venta
from gestion.forms import CategoriaForm
from gestion.models import EventoGestion
from operaciones.forms import IngresoForm
from operaciones.models import Existencia, Lote

from .rut import formatear_rut, normalizar_rut


class RutTests(TestCase):
    def test_formatos_validos_se_normalizan(self):
        for valor in ['12.345.678-5', '12345678-5', '123456785', ' 12.345.678-5 ', '11.111.111-1', '76.123.456-0']:
            with self.subTest(valor=valor):
                self.assertRegex(normalizar_rut(valor), r'^\d{7,8}-[\dK]$')
        self.assertEqual(normalizar_rut('12.345.678-5'), '12345678-5')
        self.assertEqual(formatear_rut('123456785'), '12.345.678-5')

    def test_dv_k_y_cero(self):
        # 10.000.013-K y 10.000.004-0 tienen dígito verificador K y 0 respectivamente.
        from .rut import digito_verificador
        self.assertEqual(normalizar_rut(f'10000013-{digito_verificador(10000013)}'.lower()), f'10000013-{digito_verificador(10000013)}')
        for cuerpo in range(10000000, 10000100):
            dv = digito_verificador(cuerpo)
            self.assertEqual(normalizar_rut(f'{cuerpo}{dv.lower()}'), f'{cuerpo}-{dv}')

    def test_invalidos(self):
        for valor in ['', 'abc', '12345678-9', '1-9', '12.345.678', '123456789-0', '12345678-X']:
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                normalizar_rut(valor)

    def test_paciente_rut_o_documento_extranjero(self):
        form = PacienteForm({'identificador': '12.345.678-5', 'nombre': 'Paciente', 'telefono': '', 'activo': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().identificador, '12345678-5')
        self.assertFalse(PacienteForm({'identificador': '12345678-9', 'nombre': 'X', 'activo': 'on'}).is_valid())
        duplicado = PacienteForm({'identificador': '12345678-5', 'nombre': 'Otro', 'activo': 'on'})
        self.assertFalse(duplicado.is_valid())
        extranjero = PacienteForm({'identificador': 'ab123456', 'documento_extranjero': 'on', 'nombre': 'Turista', 'activo': 'on'})
        self.assertTrue(extranjero.is_valid(), extranjero.errors)
        self.assertEqual(extranjero.save().identificador, 'AB123456')
        self.assertTrue(PacienteForm(instance=Paciente.objects.get(identificador='AB123456')).initial['documento_extranjero'])

    def test_prescriptor_exige_rut(self):
        self.assertFalse(PrescriptorForm({'identificador': 'MED-1', 'nombre': 'Dra.', 'registro': 'R1', 'activo': 'on'}).is_valid())
        form = PrescriptorForm({'identificador': '11.111.111-1', 'nombre': 'Dra.', 'registro': 'R1', 'activo': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['identificador'], '11111111-1')


class FacturaRutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('cajero')
        self.user.user_permissions.set(Permission.objects.filter(codename__in=['add_venta', 'view_venta', 'operar_caja']))
        p = Producto.objects.create(codigo='P1', barras='12345678', nombre='P1', presentacion='Caja',
            categoria=Categoria.objects.create(nombre='General'), condicion=Producto.Condicion.DIRECTA, precio=1000)
        lote = Lote.objects.create(producto=p, codigo='L', vencimiento=timezone.localdate() + timedelta(days=30))
        Existencia.objects.create(lote=lote, ubicacion='vitrina', cantidad=5)
        self.p = p
        self.caja = abrir_caja(usuario=self.user, fondo=0)

    def vender(self, rut):
        return confirmar_venta(usuario=self.user, items=[{'producto_id': self.p.pk, 'cantidad': 1}], clave=uuid.uuid4(),
            caja_id=self.caja.pk, tipo_documento='factura', receptor='Empresa SpA', rut=rut)

    def test_factura_rechaza_rut_invalido_y_normaliza(self):
        with self.assertRaisesMessage(ValidationError, 'RUT del receptor'):
            self.vender('abc')
        self.assertEqual(self.vender('76.123.456-0').documento.rut, '76123456-0')


class ClinicaCorreccionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.qf = get_user_model().objects.create_user('qf')
        cls.qf.groups.add(Group.objects.get(name='Químico Farmacéutico'))
        cls.admin = get_user_model().objects.create_user('admin')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        prod = Producto.objects.create(codigo='T', barras='87654321', nombre='Prueba', presentacion='Caja',
            categoria=Categoria.objects.create(nombre='Prueba'), condicion='Receta simple', precio=100)
        cls.receta = Receta.objects.create(paciente=Paciente.objects.create(identificador='12345678-5', nombre='P'),
            prescriptor=Prescriptor.objects.create(identificador='11111111-1', nombre='M', registro='R'),
            emitida=timezone.localdate(), vence=timezone.localdate() + timedelta(days=10))
        LineaReceta.objects.create(receta=cls.receta, producto=prod, cantidad=2)

    def test_adjunto_rechazado_no_se_descarga(self):
        adjunto = AdjuntoReceta(receta=self.receta, nombre='r.pdf', tipo='application/pdf', sha256='0' * 64, usuario=self.qf)
        adjunto.archivo.save('r.pdf', ContentFile(b'%PDF-1.4\n%%EOF'), save=False)
        adjunto.save()
        self.client.force_login(self.qf)
        respuesta = self.client.get(f'/clinica/adjunto/{adjunto.pk}/')
        self.assertEqual(respuesta.status_code, 200)
        # Se consume el contenido sin close(): cerrar la respuesta dispara request_finished y cerraría la conexión
        # que sostiene la transacción del TestCase.
        self.assertEqual(b''.join(respuesta.streaming_content), b'%PDF-1.4\n%%EOF')
        adjunto.estado = 'rechazado'
        adjunto.save()
        self.assertEqual(self.client.get(f'/clinica/adjunto/{adjunto.pk}/').status_code, 404)
        self.assertNotContains(self.client.get(f'/clinica/receta/{self.receta.pk}/'), f'/clinica/adjunto/{adjunto.pk}/')
        adjunto.archivo.delete(save=False)

    def test_identificadores_no_numericos_no_provocan_500(self):
        self.client.force_login(self.admin)
        for url in ['/clinica/pacientes/?editar=abc', '/clinica/prescriptores/?editar=1x', '/comercio/convenios/?editar=abc']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.qf)
        respuesta = self.client.post('/clinica/controlados/', {'asiento': 'abc', 'motivo': 'x'}, follow=True)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Asiento inexistente.')
        self.assertEqual(AsientoControlado.objects.count(), 0)

    def test_revision_de_receta_controlada(self):
        revisar_receta(usuario=self.qf, receta=self.receta, aprobar=True)
        with self.assertRaisesMessage(ValidationError, 'ya está aprobada'):
            revisar_receta(usuario=self.qf, receta=self.receta, aprobar=True)
        with self.assertRaisesMessage(ValidationError, 'motivo'):
            revisar_receta(usuario=self.qf, receta=self.receta, aprobar=False, nota='  ')
        revisar_receta(usuario=self.qf, receta=self.receta, aprobar=False, nota='Dosis mal transcrita')
        self.receta.refresh_from_db()
        self.assertEqual(self.receta.estado, 'rechazada')
        for aprobar in (True, False):
            with self.assertRaisesMessage(ValidationError, 'ya fue rechazada'):
                revisar_receta(usuario=self.qf, receta=self.receta, aprobar=aprobar, nota='x')


class InventarioYCatalogoCorreccionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('admin')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.qf = get_user_model().objects.create_user('qf')
        cls.qf.groups.add(Group.objects.get(name='Químico Farmacéutico'))
        cls.categoria = Categoria.objects.create(nombre='Medicamentos')
        cls.producto = Producto.objects.create(codigo='P-1', barras='99000001', nombre='P', presentacion='Caja',
            categoria=cls.categoria, condicion=Producto.Condicion.DIRECTA, precio=100)

    def datos_ingreso(self, form_vacio, **cambios):
        return {'token': form_vacio.initial['token'], 'producto': self.producto.pk, 'codigo': 'L1',
                'vencimiento': (timezone.localdate() - timedelta(days=1)).isoformat(), 'ubicacion': 'bodega', 'cantidad': 3, **cambios}

    def test_ingreso_vencido_exige_confirmacion(self):
        vacio = IngresoForm(usuario=self.admin, tipo='ingreso')
        sin_confirmar = IngresoForm(self.datos_ingreso(vacio), usuario=self.admin, tipo='ingreso')
        self.assertFalse(sin_confirmar.is_valid())
        self.assertIn('vencimiento', sin_confirmar.errors)
        confirmado = IngresoForm(self.datos_ingreso(vacio, confirmar_vencido='on'), usuario=self.admin, tipo='ingreso')
        self.assertTrue(confirmado.is_valid(), confirmado.errors)
        vigente = IngresoForm(self.datos_ingreso(vacio, vencimiento=(timezone.localdate() + timedelta(days=5)).isoformat()),
                              usuario=self.admin, tipo='ingreso')
        self.assertTrue(vigente.is_valid(), vigente.errors)

    def test_reactivar_producto(self):
        self.client.force_login(self.admin)
        self.client.post(f'/productos/{self.producto.pk}/desactivar/')
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
        self.assertContains(self.client.get(f'/productos/{self.producto.pk}/'), 'Reactivar producto')
        self.client.post(f'/productos/{self.producto.pk}/reactivar/')
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)
        self.assertEqual(list(EventoCatalogo.objects.order_by('pk').values_list('accion', flat=True)), ['desactivar', 'reactivar'])
        self.assertEqual(self.client.get(f'/productos/{self.producto.pk}/reactivar/').status_code, 405)

    def test_condicion_al_crear_depende_del_qf(self):
        datos = {'codigo': 'N-1', 'barras': '99000002', 'nombre': 'Nuevo', 'presentacion': 'Caja', 'categoria': self.categoria.pk,
                 'condicion': Producto.Condicion.RETENIDA, 'precio': '500', 'stock_minimo': '1'}
        self.client.force_login(self.admin)
        self.client.post('/productos/nuevo/', datos)
        self.assertEqual(Producto.objects.get(codigo='N-1').condicion, Producto.Condicion.VERIFICAR)
        self.client.force_login(self.qf)
        self.qf.user_permissions.add(Permission.objects.get(codename='add_producto'))
        self.client.post('/productos/nuevo/', {**datos, 'codigo': 'N-2', 'barras': '99000003'})
        self.assertEqual(Producto.objects.get(codigo='N-2').condicion, Producto.Condicion.RETENIDA)

    def test_categoria_duplicada_sin_distinguir_mayusculas(self):
        self.assertFalse(CategoriaForm({'nombre': 'medicamentos'}).is_valid())
        self.assertFalse(CategoriaForm({'nombre': '  MEDICAMENTOS '}).is_valid())
        self.assertTrue(CategoriaForm({'nombre': 'Medicamentos'}, instance=self.categoria).is_valid())

    def test_convenio_fechas_mensaje_claro(self):
        self.client.force_login(self.admin)
        hoy = timezone.localdate()
        respuesta = self.client.post('/comercio/convenios/', {'nombre': 'C', 'inicio': hoy, 'fin': hoy - timedelta(days=1),
                                                              'porcentaje': '10', 'tope': '', 'activo': 'on'})
        self.assertContains(respuesta, 'La fecha de término no puede ser anterior a la de inicio.')
        self.assertNotContains(respuesta, 'convenio_fechas_validas')

    def test_auditoria_muestra_referencia_util(self):
        EventoCatalogo.objects.create(producto=self.producto, usuario=self.admin, accion='editar')
        EventoGestion.objects.create(usuario=self.admin, accion='Crear usuario', referencia='Usuario 99')
        self.client.force_login(self.admin)
        respuesta = self.client.get('/gestion/auditoria/')
        self.assertContains(respuesta, 'Producto P-1')
        self.assertContains(respuesta, 'Usuario 99')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CorreoLocalTests(TestCase):
    def test_backend_local_por_archivo(self):
        from importlib import reload
        import os
        from unittest import mock
        from config import settings as configuracion
        with mock.patch.dict(os.environ, {'DJANGO_DEBUG': 'true', 'EMAIL_BACKEND': '', 'EMAIL_HOST': ''}):
            reload(configuracion)
            self.assertEqual(configuracion.EMAIL_BACKEND, 'django.core.mail.backends.filebased.EmailBackend')
        with mock.patch.dict(os.environ, {'DJANGO_DEBUG': 'true', 'EMAIL_BACKEND': '', 'EMAIL_HOST': 'smtp.example.com'}):
            reload(configuracion)
            self.assertEqual(configuracion.EMAIL_BACKEND, 'django.core.mail.backends.smtp.EmailBackend')
        reload(configuracion)
        self.assertEqual(len(mail.outbox), 0)


class AlertasUnificadasTests(TestCase):
    """El panel y «Productos bajo mínimo» usan el mínimo total del producto y los umbrales por ubicación."""

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre='Alertas')
        cls.producto = Producto.objects.create(codigo='AL-1', barras='99000077', nombre='Con alerta', presentacion='Caja',
            categoria=cls.categoria, condicion=Producto.Condicion.DIRECTA, precio=100, stock_minimo=5)
        lote = Lote.objects.create(producto=cls.producto, codigo='L1', vencimiento=timezone.localdate() + timedelta(days=80))
        Existencia.objects.create(lote=lote, ubicacion='vitrina', cantidad=3)
        Existencia.objects.create(lote=lote, ubicacion='bodega', cantidad=20)
        cls.lote = lote

    def test_umbral_por_ubicacion_entra_en_la_lista_unica(self):
        from gestion.models import ConfiguracionAlerta
        from operaciones.indicadores import productos_bajo_minimo
        self.assertFalse(productos_bajo_minimo().filter(pk=self.producto.pk).exists())  # total 23 > mínimo 5
        ConfiguracionAlerta.objects.create(producto=self.producto, ubicacion='vitrina', stock_minimo=4, dias_vencimiento=30)
        fila = productos_bajo_minimo().get(pk=self.producto.pk)
        self.assertEqual((fila.disponible, fila.disponible_vitrina, fila.umbral_vitrina), (23, 3, 4))
        self.assertEqual(fila.motivo, 'Vitrina bajo su umbral')
        Producto.objects.filter(pk=self.producto.pk).update(stock_minimo=30)
        self.assertEqual(productos_bajo_minimo().get(pk=self.producto.pk).motivo, 'Total bajo el mínimo del producto')

    def test_aviso_de_vencimiento_usa_plazo_configurado(self):
        from gestion.models import ConfiguracionAlerta
        from operaciones.indicadores import construir_panel
        self.assertEqual(construir_panel(ver_comercial=False)['proximos_total'], 0)  # vence en 80 días > 60
        ConfiguracionAlerta.objects.create(producto=self.producto, ubicacion='bodega', stock_minimo=0, dias_vencimiento=90)
        panel = construir_panel(ver_comercial=False)
        self.assertEqual(panel['proximos_total'], 1)
        self.assertEqual(panel['proximos'][0].pk, self.lote.pk)
