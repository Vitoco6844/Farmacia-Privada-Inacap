from django.conf import settings
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from .forms import ProductoForm
from .models import Categoria, EventoCatalogo, Producto


class CatalogoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('configurar_roles', stdout=StringIO())
        call_command('cargar_demo', stdout=StringIO())
        User = get_user_model()
        cls.admin = User.objects.create_user('administrador_prueba', password='ClavePrueba-SoloTests-123')
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.vendedor = User.objects.create_user('vendedor_prueba', password='ClavePrueba-SoloTests-123')
        cls.vendedor.groups.add(Group.objects.get(name='Vendedor'))
        cls.sin_rol = User.objects.create_user('sin_rol_prueba', password='ClavePrueba-SoloTests-123')
        cls.producto = Producto.objects.get(codigo='PRD-001')

    def datos(self, **cambios):
        return {
            'codigo': 'PRD-100', 'barras': '9900000000100', 'nombre': 'Producto de prueba',
            'presentacion': 'Caja ficticia', 'categoria': self.producto.categoria_id,
            'condicion': Producto.Condicion.DIRECTA, 'precio': '2500', 'stock_minimo': '10', **cambios,
        }

    def test_anonimo_debe_ingresar(self):
        for url in [reverse('catalogo:lista'), reverse('catalogo:crear'), reverse('catalogo:detalle', args=[self.producto.pk])]:
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f'{reverse("login")}?next={url}')

    def test_vendedor_consulta_sin_controles_de_edicion(self):
        self.client.force_login(self.vendedor)
        r = self.client.get(reverse('catalogo:lista'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total'], 8)
        self.assertEqual(len(r.context['pagina']), 6)
        self.assertNotContains(r, 'Agregar producto')
        self.assertNotContains(r, reverse('catalogo:editar', args=[self.producto.pk]))
        self.assertContains(r, reverse('catalogo:detalle', args=[self.producto.pk]))

    def test_vendedor_no_puede_mutar_por_url_ni_post(self):
        self.client.force_login(self.vendedor)
        urls = [reverse('catalogo:crear'), reverse('catalogo:editar', args=[self.producto.pk]),
                reverse('catalogo:desactivar', args=[self.producto.pk])]
        for url in urls:
            for method in [self.client.get, self.client.post]:
                with self.subTest(url=url, method=method.__name__):
                    self.assertEqual(method(url, self.datos() if method == self.client.post else {}).status_code, 403)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)
        self.assertEqual(Producto.objects.count(), 8)
        self.assertEqual(EventoCatalogo.objects.count(), 0)

    def test_cuenta_sin_rol_denegada(self):
        self.client.force_login(self.sin_rol)
        self.assertEqual(self.client.get(reverse('catalogo:lista')).status_code, 403)

    def test_credenciales_invalidas_no_crean_sesion(self):
        r = self.client.post(reverse('login'), {'username': self.admin.username, 'password': 'incorrecta'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(r, 'No pudimos iniciar sesión')

    def test_cuenta_inactiva_no_ingresa(self):
        self.admin.is_active = False
        self.admin.save()
        self.client.post(reverse('login'), {'username': self.admin.username, 'password': 'ClavePrueba-SoloTests-123'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_ingreso_valido_y_expiracion(self):
        r = self.client.post(reverse('login'), {'username': self.admin.username, 'password': 'ClavePrueba-SoloTests-123'})
        self.assertRedirects(r, reverse('operaciones:panel'))
        self.assertLessEqual(self.client.session.get_expiry_age(), 900)

    def test_no_redirige_a_sitio_externo_al_ingresar(self):
        r = self.client.post(reverse('login'), {'username': self.admin.username,
            'password': 'ClavePrueba-SoloTests-123', 'next': 'https://example.org/'})
        self.assertRedirects(r, reverse('operaciones:panel'))

    def test_salir_requiere_post_y_revoca_sesion(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('catalogo:lista')).status_code, 302)

    def test_administrador_crea_y_registra_actor(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('catalogo:crear'), self.datos(codigo=' prd-100 '))
        nuevo = Producto.objects.get(codigo='PRD-100')
        self.assertRedirects(r, reverse('catalogo:detalle', args=[nuevo.pk]))
        self.assertEqual(nuevo.precio, Decimal('2500'))
        evento = nuevo.eventos.get()
        self.assertEqual(evento.usuario, self.admin)
        self.assertEqual(evento.accion, 'crear')
        self.assertEqual(evento.anterior, {})
        self.assertEqual(evento.posterior['codigo'], 'PRD-100')

    def test_codigo_y_barras_duplicados_rechazados(self):
        self.client.force_login(self.admin)
        for datos in [self.datos(codigo=self.producto.codigo), self.datos(barras=self.producto.barras)]:
            with self.subTest(datos=datos):
                r = self.client.post(reverse('catalogo:crear'), datos)
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.context['form'].errors)
        self.assertEqual(Producto.objects.count(), 8)
        self.assertEqual(EventoCatalogo.objects.count(), 0)

    def test_datos_invalidos_rechazados(self):
        for datos in [self.datos(precio='-1'), self.datos(precio='1.5'), self.datos(barras='abc'),
                      self.datos(nombre=''), self.datos(condicion='Libre inventada'), self.datos(categoria='999999')]:
            with self.subTest(datos=datos):
                self.assertFalse(ProductoForm(datos).is_valid())

    def test_base_impide_precio_negativo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.filter(pk=self.producto.pk).update(precio=-1)

    def test_base_impide_condicion_invalida(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.filter(pk=self.producto.pk).update(condicion='Inválida')

    def test_edicion_persistente_con_historial_y_condicion_preservada(self):
        self.client.force_login(self.admin)
        datos = self.datos(codigo=self.producto.codigo, barras=self.producto.barras,
            precio='3000', condicion=Producto.Condicion.DIRECTA)
        r = self.client.post(reverse('catalogo:editar', args=[self.producto.pk]), datos)
        self.assertEqual(r.status_code, 302)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal('3000'))
        self.assertEqual(self.producto.condicion, Producto.Condicion.SIMPLE)
        evento = self.producto.eventos.get()
        self.assertEqual(evento.anterior['precio'], '2490')
        self.assertEqual(evento.posterior['precio'], '3000')

    def test_desactivacion_post_idempotente_con_historial(self):
        self.client.force_login(self.admin)
        url = reverse('catalogo:desactivar', args=[self.producto.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)
        self.client.post(url)
        self.client.post(url)
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
        self.assertEqual(self.producto.eventos.filter(accion='desactivar').count(), 1)
        self.assertEqual(Producto.objects.count(), 8)

    def test_error_de_auditoria_revierte_producto(self):
        self.client.force_login(self.admin)
        with patch('catalogo.views.EventoCatalogo.objects.create', side_effect=IntegrityError):
            r = self.client.post(reverse('catalogo:crear'), self.datos())
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Producto.objects.filter(codigo='PRD-100').exists())

    def test_historial_impide_borrado_de_producto_o_actor(self):
        EventoCatalogo.objects.create(producto=self.producto, usuario=self.admin, accion='crear')
        with self.assertRaises(ProtectedError):
            self.producto.delete()
        with self.assertRaises(ProtectedError):
            self.admin.delete()

    def test_csrf_en_creacion_y_salida(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        self.assertEqual(cliente.post(reverse('catalogo:crear'), self.datos()).status_code, 403)
        self.assertEqual(cliente.post(reverse('logout')).status_code, 403)
        cliente.get(reverse('catalogo:crear'))
        token = cliente.cookies[settings.CSRF_COOKIE_NAME].value
        r = cliente.post(reverse('catalogo:crear'), {**self.datos(), 'csrfmiddlewaretoken': token})
        self.assertEqual(r.status_code, 302)

    def test_filtros_busqueda_y_paginacion(self):
        self.client.force_login(self.vendedor)
        for q, codigo in [('PRD-008', 'PRD-008'), ('9900000000035', 'PRD-003'), ('Gasas', 'PRD-003')]:
            r = self.client.get(reverse('catalogo:lista'), {'q': q})
            self.assertEqual([p.codigo for p in r.context['pagina']], [codigo])
        r = self.client.get(reverse('catalogo:lista'), {'categoria': 'Medicamentos', 'condicion': 'Receta retenida', 'estado': 'inactivo'})
        self.assertEqual([p.codigo for p in r.context['pagina']], ['PRD-007'])
        r = self.client.get(reverse('catalogo:lista'), {'pagina': 2})
        self.assertEqual(len(r.context['pagina']), 2)
        r = self.client.get(reverse('catalogo:lista'), {'pagina': 'invalida'})
        self.assertEqual(r.context['pagina'].number, 1)

    def test_sin_resultados_y_escape(self):
        self.client.force_login(self.vendedor)
        payload = '<script>alert(1)</script>'
        r = self.client.get(reverse('catalogo:lista'), {'q': payload})
        self.assertContains(r, 'No encontramos productos')
        self.assertNotContains(r, payload)
        self.assertContains(r, '&lt;script&gt;')

    def test_detalle_inexistente(self):
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(reverse('catalogo:detalle', args=[999999])).status_code, 404)

    def test_semilla_no_sobrescribe_y_roles_no_escalan(self):
        self.producto.nombre = 'Nombre editado'
        self.producto.save()
        call_command('cargar_demo', stdout=StringIO())
        call_command('configurar_roles', stdout=StringIO())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, 'Nombre editado')
        self.assertEqual(Producto.objects.count(), 8)
        self.assertFalse(self.admin.has_perm('auth.change_user'))
        self.assertFalse(self.admin.has_perm('catalogo.delete_producto'))
        self.assertFalse(self.vendedor.has_perm('catalogo.change_producto'))
