from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from catalogo.models import Categoria, Producto
from operaciones.models import Venta
from clinica.models import Paciente, Prescriptor, Receta, LineaReceta, AutorizacionControlado, Entrega
from clinica.services import procesar_entrega, revisar_receta, autorizar_controlado

class EntregaTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_user('qf')
        self.u.groups.add(Group.objects.get_or_create(name='Químico Farmacéutico')[0])
        self.u.user_permissions.add(*Permission.objects.filter(codename__in=['revisar_receta','autorizar_controlado','add_venta','gestionar_clinica']))
        self.p = Paciente.objects.create(identificador='PAC-1', nombre='Paciente ficticio')
        self.med = Prescriptor.objects.create(identificador='MED-1', nombre='Profesional ficticio', registro='REG-1')
        self.prod = Producto.objects.create(codigo='TEST', barras='12345678', nombre='Prueba', presentacion='Caja', categoria=Categoria.objects.create(nombre='Prueba'), condicion='Receta simple', precio=100)
        self.r = Receta.objects.create(paciente=self.p, prescriptor=self.med, emitida=timezone.localdate(), vence=timezone.localdate()+timedelta(days=10))
        self.line = LineaReceta.objects.create(receta=self.r, producto=self.prod, cantidad=5)
        self.v = Venta.objects.create(usuario=self.u, total=100)
    def entregar(self, cantidad):
        return procesar_entrega(usuario=self.u, receta_id=self.r.pk, items=[{'producto_id':self.prod.pk,'cantidad':cantidad}], venta=self.v)
    def test_no_entrega_sin_revision(self):
        with self.assertRaises(ValidationError): self.entregar(1)
    def test_parcial_saldo_y_exceso(self):
        revisar_receta(usuario=self.u, receta=self.r, aprobar=True)
        self.entregar(2)
        self.line.refresh_from_db()
        self.assertEqual(self.line.entregada,2)
        self.v=Venta.objects.create(usuario=self.u,total=100)
        with self.assertRaises(ValidationError): self.entregar(4)
        self.assertEqual(Entrega.objects.count(),1)
    def test_admin_no_es_qf(self):
        admin=get_user_model().objects.create_superuser('admin','admin@example.com','secret')
        with self.assertRaises(ValidationError): revisar_receta(usuario=admin,receta=self.r,aprobar=True)
    def test_controlado_autorizacion_un_solo_uso(self):
        self.prod.condicion='Receta retenida'; self.prod.save()
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        with self.assertRaises(ValidationError): self.entregar(1)
        autorizar_controlado(usuario=self.u,receta=self.r,producto=self.prod,cantidad=1)
        self.entregar(1)
        self.v=Venta.objects.create(usuario=self.u,total=100)
        with self.assertRaises(ValidationError): self.entregar(1)
    def test_tercero_necesita_autorizacion(self):
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        otro=Paciente.objects.create(identificador='PAC-2',nombre='Retirante')
        with self.assertRaises(ValidationError): procesar_entrega(usuario=self.u,receta_id=self.r.pk,items=[{'producto_id':self.prod.pk,'cantidad':1}],venta=self.v,retirante_id=otro.pk)


    def test_vencida_rechaza_sin_cambiar_saldo(self):
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        Receta.objects.filter(pk=self.r.pk).update(vence=timezone.localdate()-timedelta(days=1))
        with self.assertRaises(ValidationError): self.entregar(1)
        self.line.refresh_from_db(); self.assertEqual(self.line.entregada,0)

    def test_productos_duplicados_se_acumulan(self):
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        with self.assertRaises(ValidationError):
            procesar_entrega(usuario=self.u,receta_id=self.r.pk,items=[{'producto_id':self.prod.pk,'cantidad':3}]*2,venta=self.v)
        self.assertEqual(Entrega.objects.count(),0)

    def test_compensacion_conserva_original_y_saldo(self):
        from clinica.models import AsientoControlado
        from clinica.services import compensar_asiento
        self.prod.condicion='Receta retenida'; self.prod.save()
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        autorizar_controlado(usuario=self.u,receta=self.r,producto=self.prod,cantidad=2)
        self.entregar(2)
        asiento=AsientoControlado.objects.get()
        compensacion=compensar_asiento(usuario=self.u,asiento_id=asiento.pk,motivo='Error de registro en libro')
        self.assertEqual(compensacion.cantidad,-2)
        asiento.refresh_from_db(); self.assertEqual(asiento.cantidad,2)
        self.line.refresh_from_db(); self.assertEqual(self.line.entregada,2)
        with self.assertRaises(ValidationError): compensar_asiento(usuario=self.u,asiento_id=asiento.pk,motivo='Duplicado')

    def test_adjunto_cuarentena_no_aprueba(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.files.storage import InMemoryStorage
        from clinica.services import subir_adjunto
        from clinica.models import AdjuntoReceta
        field=AdjuntoReceta._meta.get_field('archivo'); original=field.storage
        field.storage=InMemoryStorage()
        try:
            adjunto=subir_adjunto(usuario=self.u,receta=self.r,archivo=SimpleUploadedFile('receta.pdf',b'%PDF-1.4\ncontenido\n%%EOF'))
            self.assertEqual(adjunto.estado,'cuarentena')
            self.r.refresh_from_db(); self.assertEqual(self.r.estado,'pendiente')
            with self.assertRaises(ValidationError): subir_adjunto(usuario=self.u,receta=self.r,archivo=SimpleUploadedFile('falso.png',b'<script>bad</script>'))
            with self.assertRaises(ValidationError): subir_adjunto(usuario=self.u,receta=self.r,archivo=SimpleUploadedFile('grande.pdf',b'x'*(10*1024*1024+1)))
        finally: field.storage=original

    def test_impresion_usa_datos_congelados(self):
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        entrega=self.entregar(1)
        self.p.nombre='Nombre nuevo'; self.p.save()
        self.assertIn('Paciente ficticio',entrega.instantanea['paciente'])

    def test_pantallas_y_descarga_privada(self):
        from django.urls import reverse
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='clinica'))
        self.client.force_login(self.u)
        for nombre,args in [('recetas',[]),('pacientes',[]),('prescriptores',[]),('controlados',[]),('receta_crear',[]),('receta_detalle',[self.r.pk])]:
            self.assertEqual(self.client.get(reverse('clinica:'+nombre,args=args)).status_code,200,nombre)

    def test_sin_saldo_definido_se_registra_expresamente(self):
        self.line.sin_limite=True; self.line.cantidad=None; self.line.save()
        revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
        self.entregar(9)
        self.line.refresh_from_db()
        self.assertIsNone(self.line.saldo)
        self.assertEqual(self.line.entregada,9)

    def test_descarga_exige_permiso_aunque_conozca_id(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.core.files.storage import InMemoryStorage
        from clinica.services import subir_adjunto
        from clinica.models import AdjuntoReceta
        from django.urls import reverse
        field=AdjuntoReceta._meta.get_field('archivo'); original=field.storage; field.storage=InMemoryStorage()
        try:
            adjunto=subir_adjunto(usuario=self.u,receta=self.r,archivo=SimpleUploadedFile('receta.pdf',b'%PDF-1.4\n%%EOF'))
            self.client.force_login(self.u)
            self.assertEqual(self.client.get(reverse('clinica:descargar',args=[adjunto.pk])).status_code,403)
            self.u.user_permissions.add(Permission.objects.get(codename='descargar_adjunto'))
            response=self.client.get(reverse('clinica:descargar',args=[adjunto.pk]))
            self.assertEqual(response.status_code,200)
            self.assertIn('attachment',response['Content-Disposition'])
            # Consumir el stream deja que el cliente de pruebas cierre la respuesta
            # sin cerrar la conexión que sostiene la transacción del TestCase.
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4\n%%EOF')
        finally: field.storage=original

    def test_qf_sin_permiso_no_revisa(self):
        self.u.user_permissions.clear()
        with self.assertRaises(ValidationError): revisar_receta(usuario=self.u,receta=self.r,aprobar=True)
