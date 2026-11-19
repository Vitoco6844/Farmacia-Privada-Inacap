import uuid
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from catalogo.models import Producto, Categoria
from operaciones.models import Lote, Existencia, Venta, Movimiento
from .models import Caja, Convenio, Documento
from .services import abrir_caja, cerrar_caja, mover_caja, confirmar_venta, emitir_documento, resumen_caja

class ComercioTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('cajero')
        self.user.user_permissions.set(Permission.objects.filter(codename__in=['add_venta','view_venta','operar_caja','emitir_documento']))
        self.cat=Categoria.objects.create(nombre='General')
        self.p=self.producto('P1',1000)
        self.p2=self.producto('P2',500)
        self.caja=abrir_caja(usuario=self.user,fondo=10000)
    def producto(self,codigo,precio):
        p=Producto.objects.create(codigo=codigo,barras='12345678'+codigo[-1],nombre=codigo,presentacion='Caja',categoria=self.cat,condicion=Producto.Condicion.DIRECTA,precio=precio)
        for indice,dias in enumerate([10,30]):
            lote=Lote.objects.create(producto=p,codigo=str(indice),vencimiento=timezone.localdate()+timedelta(days=dias))
            Existencia.objects.create(lote=lote,ubicacion='vitrina',cantidad=5)
        return p
    def venta(self,**kwargs):
        args=dict(usuario=self.user,items=[{'producto_id':self.p.pk,'cantidad':2}],clave=uuid.uuid4(),caja_id=self.caja.pk)
        args.update(kwargs)
        return confirmar_venta(**args)
    def test_multiproducto_fefo_historico(self):
        venta=self.venta(items=[{'producto_id':self.p.pk,'cantidad':7},{'producto_id':self.p2.pk,'cantidad':3}])
        self.assertEqual(venta.total,8500)
        self.assertEqual(list(Existencia.objects.filter(lote__producto=self.p).order_by('lote__vencimiento').values_list('cantidad',flat=True)),[0,3])
        self.p.precio=9999;self.p.save()
        self.assertEqual(venta.detalles.get(producto=self.p).precio_unitario,1000)
        self.assertEqual(Movimiento.objects.count(),3)
    def test_stock_insuficiente_revierte_todo(self):
        with self.assertRaises(ValidationError): self.venta(items=[{'producto_id':self.p.pk,'cantidad':2},{'producto_id':self.p2.pk,'cantidad':11}])
        self.assertEqual(Venta.objects.count(),0)
        self.assertEqual(sum(Existencia.objects.values_list('cantidad',flat=True)),20)
    def test_receta_faltante_revierte(self):
        self.p2.condicion=Producto.Condicion.SIMPLE;self.p2.save()
        with self.assertRaises(ValidationError): self.venta(items=[{'producto_id':self.p.pk,'cantidad':2},{'producto_id':self.p2.pk,'cantidad':1}])
        self.assertFalse(Venta.objects.exists());self.assertFalse(Movimiento.objects.exists())
    def test_idempotencia_despues_cierre_precio_y_cambio_rechazado(self):
        clave=uuid.uuid4();venta=self.venta(clave=clave)
        cerrar_caja(usuario=self.user,caja_id=self.caja.pk,contado=12000)
        self.p.precio=6000;self.p.save()
        self.assertEqual(self.venta(clave=clave).pk,venta.pk)
        with self.assertRaises(ValidationError):self.venta(clave=clave,medio='tarjeta')
        self.assertEqual(Venta.objects.count(),1)
    def test_convenio_tope_copago_y_no_acumular(self):
        c=Convenio.objects.create(nombre='Bienestar',inicio=timezone.localdate(),fin=timezone.localdate(),porcentaje=50,tope=300)
        venta=self.venta(convenio_id=c.pk)
        self.assertEqual(venta.total,1700);self.assertEqual(venta.cobro.beneficio,300)
        with self.assertRaises(ValidationError):self.venta(convenio_id=c.pk,descuento=1)
        c.inicio=timezone.localdate()-timedelta(days=2);c.fin=timezone.localdate()-timedelta(days=1);c.save()
        with self.assertRaises(ValidationError):self.venta(convenio_id=c.pk)
    def test_medios_separados_diferencia_obligatoria(self):
        self.venta();self.venta(medio='tarjeta');self.venta(medio='transferencia')
        resumen=resumen_caja(self.caja)
        self.assertEqual(resumen['esperado'],12000);self.assertEqual(resumen['tarjeta'],2000);self.assertEqual(resumen['transferencia'],2000)
        with self.assertRaises(ValidationError):cerrar_caja(usuario=self.user,caja_id=self.caja.pk,contado=11900)
        caja=cerrar_caja(usuario=self.user,caja_id=self.caja.pk,contado=11900,motivo='Diferencia de conteo')
        self.assertEqual(caja.esperado_cierre,12000)
        with self.assertRaises(ValidationError):self.venta()
    def test_caja_ajena_y_permiso(self):
        other=get_user_model().objects.create_user('otro')
        with self.assertRaises(PermissionDenied):self.venta(usuario=other)
        other.user_permissions.set(self.user.user_permissions.all())
        with self.assertRaises(PermissionDenied):self.venta(usuario=other)
        with self.assertRaises(PermissionDenied):cerrar_caja(usuario=other,caja_id=self.caja.pk,contado=10000)
    def test_doble_apertura_movimiento_idempotente_retiro(self):
        with self.assertRaises(ValidationError):abrir_caja(usuario=self.user,fondo=0)
        args=dict(usuario=self.user,caja_id=self.caja.pk,tipo='retiro',monto=100,motivo='Depósito',clave=uuid.uuid4())
        primero=mover_caja(**args);self.assertEqual(mover_caja(**args).pk,primero.pk)
        self.assertEqual(resumen_caja(self.caja)['esperado'],9900)
        with self.assertRaises(ValidationError):mover_caja(**{**args,'clave':uuid.uuid4(),'monto':10001})
    def test_documento_fallo_reintento_sin_duplicar(self):
        venta=self.venta(tipo_documento='factura',receptor='Empresa ficticia',rut='12345678-9')
        doc=emitir_documento(usuario=self.user,documento_id=venta.documento.pk,simular_error=True)
        self.assertEqual(doc.estado,'error')
        doc=emitir_documento(usuario=self.user,documento_id=doc.pk)
        self.assertEqual(doc.estado,'emitido');self.assertEqual(doc.intentos,2)
        doc=emitir_documento(usuario=self.user,documento_id=doc.pk)
        self.assertEqual(doc.intentos,2);self.assertEqual(Venta.objects.count(),1);self.assertEqual(Movimiento.objects.count(),1)
    def test_excluye_vencidos_bloqueados_inactivos(self):
        Lote.objects.filter(producto=self.p).update(bloqueado=True)
        with self.assertRaises(ValidationError):self.venta()
        Lote.objects.filter(producto=self.p).update(bloqueado=False,vencimiento=timezone.localdate())
        with self.assertRaises(ValidationError):self.venta()
        self.p2.activo=False;self.p2.save()
        with self.assertRaises(ValidationError):self.venta(items=[{'producto_id':self.p2.pk,'cantidad':1}])
    def test_descuento_no_autorizado(self):
        with self.assertRaises(ValidationError):self.venta(descuento=5)
    def test_documento_factura_requiere_receptor(self):
        with self.assertRaises(ValidationError):self.venta(tipo_documento='factura')
    def test_clinica_aprobada_entrega_unica_y_saldo(self):
        from clinica.models import Paciente, Prescriptor, Receta, LineaReceta, Entrega
        self.p.condicion=Producto.Condicion.SIMPLE;self.p.save()
        paciente=Paciente.objects.create(identificador='P-TEST',nombre='Paciente')
        medico=Prescriptor.objects.create(identificador='M-TEST',nombre='Médico',registro='REG-1')
        receta=Receta.objects.create(paciente=paciente,prescriptor=medico,emitida=timezone.localdate(),vence=timezone.localdate()+timedelta(days=10))
        linea=LineaReceta.objects.create(receta=receta,producto=self.p,cantidad=3)
        with self.assertRaises(ValidationError):self.venta(receta_id=receta.pk)
        self.assertFalse(Venta.objects.exists());self.assertFalse(Movimiento.objects.exists())
        receta.estado='aprobada';receta.save()
        clave=uuid.uuid4();venta=self.venta(receta_id=receta.pk,clave=clave)
        self.assertEqual(self.venta(receta_id=receta.pk,clave=clave).pk,venta.pk)
        linea.refresh_from_db();self.assertEqual(linea.entregada,2)
        self.assertEqual(Entrega.objects.count(),1)
        with self.assertRaises(ValidationError):self.venta(receta_id=receta.pk)
        self.assertEqual(Venta.objects.count(),1)
        self.assertEqual(sum(Existencia.objects.filter(lote__producto=self.p).values_list('cantidad',flat=True)),8)

    def test_descuento_permitido_y_precio_programado(self):
        from gestion.models import PoliticaPrecio, PrecioProgramado
        PoliticaPrecio.objects.create(producto=self.p,descuento_maximo=10,fuente='Demo')
        PrecioProgramado.objects.create(producto=self.p,precio=800,desde=timezone.localdate(),fuente='Demo',usuario=self.user)
        v=self.venta(descuento=10)
        self.assertEqual(v.cobro.bruto,1600);self.assertEqual(v.cobro.descuento,160);self.assertEqual(v.total,1440)

    def test_pantallas_busqueda_y_permiso_emision(self):
        from django.urls import reverse
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label='comercio'))
        self.client.force_login(self.user)
        for name in ['pos','caja','convenios']:
            self.assertEqual(self.client.get(reverse('comercio:'+name)).status_code,200,name)
        response=self.client.get(reverse('comercio:buscar'),{'q':self.p.barras})
        self.assertEqual(response.json()['productos'][0]['id'],self.p.pk)
        v=self.venta()
        self.assertEqual(self.client.get(reverse('comercio:documento',args=[v.documento.pk])).status_code,200)
        other=get_user_model().objects.create_user('sinpermiso')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('comercio:pos')).status_code,403)
        with self.assertRaises(PermissionDenied):emitir_documento(usuario=other,documento_id=v.documento.pk)

    def test_convenio_auditable(self):
        from .services import guardar_convenio
        from .models import EventoComercial
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=['add_convenio','change_convenio']))
        datos=dict(nombre='Prueba',inicio=timezone.localdate(),fin=timezone.localdate(),porcentaje=20,tope=None,activo=True)
        convenio=guardar_convenio(usuario=self.user,datos=datos)
        guardar_convenio(usuario=self.user,convenio_id=convenio.pk,datos={**datos,'porcentaje':30})
        self.assertEqual(EventoComercial.objects.count(),2)
        self.assertEqual(EventoComercial.objects.first().detalle['anterior']['porcentaje'],'20.00')
