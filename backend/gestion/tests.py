from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError, PermissionDenied
from catalogo.models import Categoria, Producto
from .models import PrecioProgramado, PoliticaPrecio
from .services import precio_vigente, limite_descuento, guardar_usuario, revisar_condicion
from .models import EventoGestion, ConfiguracionAlerta
from django.urls import reverse
from django.utils import timezone


class GestionTests(TestCase):
    def setUp(self):
        self.p = Producto.objects.create(codigo='A', barras='12345678', nombre='Ejemplo',
            presentacion='Caja', categoria=Categoria.objects.create(nombre='General'),
            condicion=Producto.Condicion.DIRECTA, precio=1000)
        self.admin = get_user_model().objects.create_user('admin', password='X-segura-123')
        self.rol, _ = Group.objects.get_or_create(name='Administrador')
        self.rol.permissions.add(Permission.objects.get(codename='administrar_usuarios'))
        self.admin.groups.add(self.rol)

    def test_precio_fechas_inclusivas_y_fallback(self):
        PrecioProgramado.objects.create(producto=self.p, precio=800, desde=date(2026,1,2),
            hasta=date(2026,1,3), fuente='Lista proveedor', usuario=self.admin)
        self.assertEqual(precio_vigente(self.p, date(2026,1,1)), Decimal(1000))
        self.assertEqual(precio_vigente(self.p, date(2026,1,2)), Decimal(800))
        self.assertEqual(precio_vigente(self.p, date(2026,1,3)), Decimal(800))
        self.assertEqual(precio_vigente(self.p, date(2026,1,4)), Decimal(1000))

    def test_cenabast_y_descuento(self):
        PoliticaPrecio.objects.create(producto=self.p, aplica_cenabast=True, precio_maximo=600,
            descuento_maximo=10, fuente='Resolución demo')
        self.assertEqual(precio_vigente(self.p), 600)
        self.assertEqual(limite_descuento(self.p), 10)

    def test_admin_no_es_qf(self):
        with self.assertRaises(PermissionDenied):
            revisar_condicion(self.admin, self.p.pk, Producto.Condicion.SIMPLE, 'Revisión')

    def test_no_autocambio_roles(self):
        with self.assertRaises(ValidationError):
            guardar_usuario(self.admin, self.admin, {}, [], {})

    def test_no_ultimo_administrador(self):
        otro = get_user_model().objects.create_user('operador')
        otro.user_permissions.add(Permission.objects.get(codename='administrar_usuarios'))
        # El actor se desactiva para no contar como administrador disponible.
        otro.is_active = False
        otro.save()
        with self.assertRaises(PermissionDenied):
            guardar_usuario(otro, self.admin, {'is_active': False}, [self.rol], {})

    def test_vista_rechaza_sin_permiso(self):
        u = get_user_model().objects.create_user('sinpermiso')
        self.client.force_login(u)
        self.assertEqual(self.client.get('/gestion/usuarios/').status_code, 403)

    def test_superusuario_sin_rol_no_revisa(self):
        self.admin.is_superuser = True
        self.admin.save()
        with self.assertRaises(PermissionDenied):
            revisar_condicion(self.admin, self.p.pk, Producto.Condicion.SIMPLE, 'Fundamento')

    def test_revision_profesional_auditada(self):
        qf, _ = Group.objects.get_or_create(name='Químico Farmacéutico')
        qf.permissions.add(Permission.objects.get(codename='revisar_condicion'))
        self.admin.groups.add(qf)
        revisar_condicion(self.admin, self.p.pk, Producto.Condicion.SIMPLE, 'Fuente revisada')
        self.p.refresh_from_db()
        self.assertEqual(self.p.condicion, Producto.Condicion.SIMPLE)
        self.assertTrue(EventoGestion.objects.filter(accion='Revisar condición de venta').exists())

    def test_programa_mas_reciente_y_empate(self):
        for precio, desde in [(900, date(2026,1,1)), (700, date(2026,1,2)), (650, date(2026,1,2))]:
            PrecioProgramado.objects.create(producto=self.p, precio=precio, desde=desde, fuente='Lista', usuario=self.admin)
        self.assertEqual(precio_vigente(self.p, date(2026,1,5)), 650)
        self.assertEqual(precio_vigente(self.p, date(2026,1,1)), 900)

    def test_programacion_invertida_rechazada(self):
        p = PrecioProgramado(producto=self.p, precio=500, desde=date(2026,2,1),
            hasta=date(2026,1,1), fuente='Lista', usuario=self.admin)
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_politica_requiere_tope_y_descuento_valido(self):
        for datos in [{'aplica_cenabast': True}, {'descuento_maximo': 101}, {'precio_maximo': -1}]:
            with self.assertRaises(ValidationError):
                PoliticaPrecio(producto=self.p, fuente='Fuente', **datos).full_clean()

    def test_crear_desactivar_sin_borrar_historial_ni_secretos(self):
        u = guardar_usuario(self.admin, get_user_model()(), {'username': 'trabajador',
            'first_name': 'Ana', 'last_name': 'Ejemplo'}, [], {'rut': '12345678-5', 'telefono': '912345678'}, 'Segura*98765.x')
        guardar_usuario(self.admin, u, {'is_active': False}, [], {})
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertEqual(u.trabajador.rut, '12345678-5')
        self.assertNotIn('Segura', str(list(EventoGestion.objects.values())))
        self.assertTrue(u.check_password('Segura*98765.x'))

    def test_no_gestion_superusuario(self):
        u = get_user_model().objects.create_superuser('root', password='Segura*98765.x')
        with self.assertRaises(PermissionDenied):
            guardar_usuario(self.admin, u, {'is_active': False}, [], {})

    def test_no_grupo_ajeno(self):
        g = Group.objects.create(name='Privilegios arbitrarios')
        with self.assertRaises(ValidationError):
            guardar_usuario(self.admin, get_user_model()(), {'username': 'otra'}, [g], {})

    def test_rechaza_clave_debil_en_servicio(self):
        with self.assertRaises(ValidationError):
            guardar_usuario(self.admin, get_user_model()(), {'username': 'otra'}, [], {}, '123')

    def test_formulario_usuario_y_auditoria_solo_lectura(self):
        self.admin.user_permissions.add(Permission.objects.get(codename='ver_auditoria'))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('gestion:usuario_crear')).status_code, 200)
        response = self.client.post(reverse('gestion:usuario_crear'), {
            'username': 'ana', 'first_name': 'Ana', 'last_name': 'Prueba', 'email': 'ana@example.test',
            'is_active': 'on', 'rut': '12345678-5', 'telefono': '912345678', 'nueva_clave': 'Segura*98765.x'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='ana').exists())
        self.assertEqual(self.client.get(reverse('gestion:auditoria')).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion:usuarios')).status_code, 200)

    def test_alerta_stock_por_ubicacion(self):
        from operaciones.models import Lote, Existencia
        self.admin.user_permissions.add(Permission.objects.get(codename='configurar_alertas'))
        ConfiguracionAlerta.objects.create(producto=self.p, ubicacion='vitrina', stock_minimo=3, dias_vencimiento=90)
        lote = Lote.objects.create(producto=self.p, codigo='DEMO', vencimiento=timezone.localdate() + timedelta(days=1))
        Existencia.objects.create(lote=lote, ubicacion='vitrina', cantidad=2)
        Existencia.objects.create(lote=lote, ubicacion='bodega', cantidad=50)
        vence_hoy = Lote.objects.create(producto=self.p, codigo='HOY', vencimiento=timezone.localdate())
        Existencia.objects.create(lote=vence_hoy, ubicacion='vitrina', cantidad=5)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('gestion:alertas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['estados'][0]['disponible'], 2)
        self.assertTrue(response.context['estados'][0]['bajo'])
        self.assertIn('HOY', [e.lote.codigo for e in response.context['estados'][0]['vencimientos']])

    def test_pantallas_comerciales(self):
        self.admin.user_permissions.add(Permission.objects.get(codename='administrar_precios'))
        self.client.force_login(self.admin)
        for nombre, args in [('precios', []), ('precio_crear', []), ('politica_editar', [self.p.pk])]:
            self.assertEqual(self.client.get(reverse('gestion:'+nombre, args=args)).status_code, 200)
