"""Expone flujos existentes a la interfaz independiente mediante rutas explícitas."""
from dataclasses import dataclass

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import Http404, JsonResponse
from django.urls import Resolver404, path, resolve
from django.views.decorators.cache import never_cache

from catalogo import views as catalogo
from clinica import views as clinica
from clinica.models import AdjuntoReceta
from comercio import views as comercio
from compras import views as compras
from gestion import views as gestion
from operaciones import ampliacion, vistas_reportes, views as operaciones
from . import ui_comercio as op, ui_gestion as ges
from .ui_datos import enlace, errores_form, formulario, formulario_django


def proyectar_formulario(request, contexto):
    return formulario_django(contexto)


@dataclass(frozen=True)
class Pantalla:
    titulo: str
    permiso: str
    vista: object
    proyectar: object = proyectar_formulario
    grupo: str = ''
    escribir: bool = False


def editar_producto(request, c):
    datos = formulario_django(c, 'Guardar producto')
    p = c['producto']
    if p and p.activo:
        datos['formularios'].append(formulario('Desactivar producto', [], ruta=f'producto-desactivar/{p.pk}',
                                             confirmar='¿Desactivar este producto?'))
    elif p:
        datos['formularios'].append(formulario('Reactivar producto', [], ruta=f'producto-reactivar/{p.pk}',
                                             confirmar='¿Reactivar este producto?'))
    return datos


def editar_usuario(request, c):
    datos = formulario_django(c, 'Guardar trabajador')
    u = c['form'].instance
    if u.pk and u.is_active and u.pk != request.user.pk:
        datos['formularios'].append(formulario('Desactivar cuenta', [], ruta=f'usuario-desactivar/{u.pk}',
                                             confirmar='¿Desactivar esta cuenta?'))
    return datos


def prescriptores(request):
    return clinica.personas(request, tipo='prescriptor')


def adjunto(request, pk):
    if not es_qf(request):
        raise PermissionDenied
    archivo = AdjuntoReceta.objects.get(pk=pk)
    if archivo.estado == 'rechazado':
        raise Http404
    return clinica.descargar(request, pk)


def buscar_pos(request):
    if len(request.GET.get('q', '')) > 100:
        raise ValidationError('La búsqueda admite hasta 100 caracteres.')
    return comercio.buscar(request)


RUTAS = {
    'panel': Pantalla('Turno de hoy', 'operaciones.view_existencia', operaciones.panel, op.panel, 'Turno'),
    'proveedores': Pantalla('Proveedores', 'compras.view_proveedor', compras.proveedores, op.proveedores, 'Compras e inventario'),
    'proveedor-nuevo': Pantalla('Nuevo proveedor', 'compras.add_proveedor', compras.nuevo_proveedor, escribir=True),
    'proveedor-editar/<int:pk>': Pantalla('Editar proveedor', 'compras.change_proveedor', compras.editar_proveedor, escribir=True),
    'anular/<int:pk>': Pantalla('Anular orden de compra', 'compras.anular_ordencompra', op.anular, op.formulario_anular, escribir=True),
    'traslado': Pantalla('Trasladar stock', 'operaciones.change_existencia', operaciones.traslado, proyectar_formulario, 'Compras e inventario', True),
    'ingreso': Pantalla('Registrar ingreso de stock', 'operaciones.add_lote', operaciones.ingreso, proyectar_formulario, 'Compras e inventario', True),
    'movimientos': Pantalla('Movimientos de stock', 'operaciones.view_movimiento', operaciones.movimientos, op.movimientos, 'Compras e inventario'),
    'stock-bajo': Pantalla('Alertas de stock mínimo', 'operaciones.view_existencia', operaciones.alertas_stock, op.alertas_stock, 'Compras e inventario'),
    'alertas': Pantalla('Alertas por ubicación', 'gestion.configurar_alertas', gestion.alertas, ges.alertas, 'Compras e inventario'),
    'alerta-nueva': Pantalla('Configurar alerta', 'gestion.configurar_alertas', gestion.alerta_editar, escribir=True),
    'alerta-editar/<int:pk>': Pantalla('Editar alerta', 'gestion.configurar_alertas', gestion.alerta_editar, escribir=True),
    'caja': Pantalla('Caja', 'comercio.operar_caja', comercio.caja, op.caja, 'Caja y ventas', True),
    'pos': Pantalla('Punto de venta', 'operaciones.add_venta', comercio.pos, op.pos, 'Caja y ventas', True),
    'pos-buscar': Pantalla('Buscar producto para venta', 'operaciones.add_venta', buscar_pos),
    'ventas': Pantalla('Ventas registradas', 'operaciones.view_venta', operaciones.ventas, op.ventas, 'Caja y ventas'),
    'venta/<int:pk>': Pantalla('Detalle de venta', 'operaciones.view_venta', operaciones.venta_detalle, op.venta),
    'documento/<int:pk>': Pantalla('Documento de venta', 'operaciones.view_venta', comercio.documento, op.documento, escribir=True),
    'convenios': Pantalla('Convenios', 'comercio.view_convenio', comercio.convenios, op.convenios, 'Caja y ventas', True),
    'recetas': Pantalla('Recetas', 'clinica.view_receta', clinica.recetas, ges.recetas, 'Clínica'),
    'receta-nueva': Pantalla('Registrar receta', 'clinica.gestionar_clinica', clinica.receta_crear, ges.receta_nueva, escribir=True),
    'receta/<int:pk>': Pantalla('Detalle de receta', 'clinica.view_receta', clinica.receta_detalle, ges.receta, escribir=True),
    'pacientes': Pantalla('Pacientes y retirantes', 'clinica.gestionar_clinica', clinica.personas, ges.personas, 'Clínica', True),
    'prescriptores': Pantalla('Prescriptores', 'clinica.gestionar_clinica', prescriptores, ges.personas, 'Clínica', True),
    'controlados': Pantalla('Libro de controlados', 'clinica.view_asientocontrolado', clinica.controlados, ges.controlados, 'Clínica', True),
    'adjunto/<int:pk>': Pantalla('Adjunto privado', 'clinica.descargar_adjunto', adjunto),
    'entrega/<int:pk>': Pantalla('Orden imprimible de entrega', 'clinica.view_entrega', clinica.imprimir, ges.entrega),
    'producto-nuevo': Pantalla('Nuevo producto', 'catalogo.add_producto', catalogo.crear, editar_producto, escribir=True),
    'producto-editar/<int:pk>': Pantalla('Editar producto', 'catalogo.change_producto', catalogo.editar, editar_producto, escribir=True),
    'producto-desactivar/<int:pk>': Pantalla('Desactivar producto', 'catalogo.change_producto', catalogo.desactivar, escribir=True),
    'producto-reactivar/<int:pk>': Pantalla('Reactivar producto', 'catalogo.change_producto', catalogo.reactivar, escribir=True),
    'categorias': Pantalla('Categorías', 'catalogo.view_categoria', gestion.categorias, ges.categorias, 'Administración'),
    'categoria-nueva': Pantalla('Nueva categoría', 'catalogo.add_categoria', gestion.categoria_editar, escribir=True),
    'categoria-editar/<int:pk>': Pantalla('Editar categoría', 'catalogo.change_categoria', gestion.categoria_editar, escribir=True),
    'usuarios': Pantalla('Usuarios y permisos', 'gestion.administrar_usuarios', gestion.usuarios, ges.usuarios, 'Administración'),
    'usuario-nuevo': Pantalla('Nuevo trabajador', 'gestion.administrar_usuarios', gestion.usuario_editar, editar_usuario, escribir=True),
    'usuario-editar/<int:pk>': Pantalla('Editar trabajador', 'gestion.administrar_usuarios', gestion.usuario_editar, editar_usuario, escribir=True),
    'usuario-desactivar/<int:pk>': Pantalla('Desactivar cuenta', 'gestion.administrar_usuarios', gestion.usuario_desactivar, escribir=True),
    'precios': Pantalla('Precios y descuentos', 'gestion.administrar_precios', gestion.precios, ges.precios, 'Administración'),
    'precio-nuevo': Pantalla('Programar precio', 'gestion.administrar_precios', gestion.precio_crear, escribir=True),
    'precio-limites/<int:pk>': Pantalla('Configurar límites de precio', 'gestion.administrar_precios', gestion.politica_editar, escribir=True),
    'condiciones': Pantalla('Revisar condición de venta', 'gestion.revisar_condicion', gestion.condiciones, proyectar_formulario, 'Administración', True),
    'indicadores': Pantalla('Indicadores', 'operaciones.exportar_ventas', ampliacion.analisis, ges.indicadores, 'Reportes y auditoría'),
    'reporte-ventas': Pantalla('Reporte de ventas', 'operaciones.exportar_ventas', vistas_reportes.ventas, ges.reportes, 'Reportes y auditoría'),
    'reporte-inventario': Pantalla('Reporte de inventario', 'operaciones.exportar_inventario', vistas_reportes.inventario, ges.reportes, 'Reportes y auditoría'),
    'reporte-compras': Pantalla('Reporte de compras', 'compras.exportar_compras', ampliacion.compras, ges.reportes, 'Reportes y auditoría'),
    'auditoria': Pantalla('Auditoría', 'gestion.ver_auditoria', gestion.auditoria, ges.auditoria, 'Reportes y auditoría'),
}

DESTINOS = {
    'catalogo:detalle': 'producto-editar/{pk}',
    'compras:proveedores': 'proveedores',
    'operaciones:inventario': '@inventario',
    'comercio:caja': 'caja',
    'comercio:convenios': 'convenios',
    'comercio:documento': 'documento/{pk}',
    'clinica:receta_detalle': 'receta/{pk}',
    'clinica:controlados': 'controlados',
    'gestion:usuarios': 'usuarios',
    'gestion:categorias': 'categorias',
    'gestion:precios': 'precios',
    'gestion:condiciones': 'condiciones',
    'gestion:alertas': 'alertas',
}


def menu(usuario):
    return [{**enlace(p.titulo, ruta), 'grupo': p.grupo} for ruta, p in RUTAS.items()
            if p.grupo and usuario.has_perm(p.permiso)]


def es_qf(request):
    return request.user.groups.filter(name='Químico Farmacéutico').exists()


def proteger_accion(request, ruta):
    if ruta == 'receta/<int:pk>' and request.method == 'POST':
        accion = request.POST.get('accion')
        profesional = {'revisar': 'clinica.revisar_receta', 'autorizar': 'clinica.autorizar_controlado',
                       'revisar_adjunto': 'clinica.revisar_receta'}
        if accion in profesional:
            if not (es_qf(request) and request.user.has_perm(profesional[accion])):
                raise PermissionDenied
            if accion != 'autorizar' and request.POST.get('decision') not in ('aprobar', 'rechazar'):
                raise ValidationError('Selecciona una decisión válida.')
        elif accion != 'adjunto' or not request.user.has_perm('clinica.gestionar_clinica'):
            raise PermissionDenied


def notificaciones(request):
    avisos = list(messages.get_messages(request))
    return ([str(m) for m in avisos if m.level >= messages.ERROR],
            [str(m) for m in avisos if m.level < messages.ERROR])


def respuesta(datos, status=200):
    return JsonResponse(datos, status=status)


def publicar(ruta, pantalla):
    @never_cache
    def atender(request, **kwargs):
        if request.method not in (('GET', 'POST') if pantalla.escribir else ('GET',)):
            return respuesta({'error': 'Método no permitido.'}, 405)
        if not request.user.is_authenticated:
            return respuesta({'error': 'Inicia sesión para continuar.'}, 401)
        if not request.user.has_perm(pantalla.permiso):
            return respuesta({'error': 'Tu cuenta no tiene permiso para esta operación.'}, 403)
        try:
            proteger_accion(request, ruta)
            if request.GET.get('editar') and not (
                    request.GET['editar'].isascii() and request.GET['editar'].isdigit()
                    and len(request.GET['editar']) <= 18):
                raise ValidationError('Identificador de edición inválido.')
            request.respuesta_api_ruta = ruta

            def proyectar(contexto, status):
                errores, avisos = notificaciones(request)
                errores.extend(errores_form(contexto))
                if errores or status >= 400:
                    return respuesta({'error': ' '.join(errores) or 'No se pudo consultar esta pantalla.'},
                                     max(status, 400))
                if request.method == 'POST':
                    if not contexto.get('guardado'):
                        return respuesta({'error': 'Revisa los datos antes de guardar.'}, 400)
                    return respuesta({'mensaje': 'Operación registrada.', 'destino': '@compras'})
                return respuesta({'titulo': pantalla.titulo, 'avisos': avisos,
                                  **pantalla.proyectar(request, contexto)})

            request.respuesta_api = proyectar
            resultado = pantalla.vista(request, **kwargs)
            if 300 <= resultado.status_code < 400:
                errores, avisos = notificaciones(request)
                if errores:
                    return respuesta({'error': ' '.join(errores)}, 400)
                destino = None
                try:
                    resuelta = resolve(resultado['Location'].split('?')[0])
                    patron = DESTINOS.get(resuelta.view_name)
                    if patron:
                        destino = patron.format(**resuelta.kwargs)
                except Resolver404:
                    pass
                return respuesta({'mensaje': ' '.join(avisos) or 'Operación registrada.', 'destino': destino})
            return resultado
        except (Http404, ObjectDoesNotExist):
            return respuesta({'error': 'El registro solicitado no está disponible.'}, 404)
        except PermissionDenied:
            return respuesta({'error': 'Tu cuenta no tiene permiso para esta operación.'}, 403)
        except ValidationError as exc:
            return respuesta({'error': ' '.join(exc.messages)}, 400)
        except IntegrityError:
            return respuesta({'error': 'No se pudo guardar por una restricción de datos. Revisa los campos.'}, 409)

    return atender


urlpatterns = [path(ruta + '/', publicar(ruta, pantalla)) for ruta, pantalla in RUTAS.items()]
