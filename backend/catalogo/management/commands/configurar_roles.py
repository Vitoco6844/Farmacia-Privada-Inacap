from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Configura los cuatro roles de catálogo, inventario, ventas, reportes y compras.'

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {
            'Administrador': ['catalogo.view_producto', 'catalogo.add_producto', 'catalogo.change_producto',
                'catalogo.view_eventocatalogo', 'catalogo.view_categoria', 'catalogo.add_categoria', 'catalogo.change_categoria'],
            'Vendedor': ['catalogo.view_producto'],
            'Técnico en Farmacia': ['catalogo.view_producto'],
            'Químico Farmacéutico': ['catalogo.view_producto'],
        }
        consulta = ['operaciones.view_existencia']
        inventario = ['operaciones.view_lote', 'operaciones.add_lote', 'operaciones.change_existencia', 'operaciones.view_movimiento']
        venta = ['operaciones.add_venta', 'operaciones.view_venta']
        roles['Administrador'] += consulta + inventario + venta
        roles['Vendedor'] += consulta + venta
        roles['Técnico en Farmacia'] += consulta + inventario
        roles['Químico Farmacéutico'] += consulta + inventario
        roles['Administrador'] += ['operaciones.exportar_ventas', 'operaciones.exportar_inventario', 'operaciones.view_eventoreporte']
        roles['Químico Farmacéutico'] += ['operaciones.exportar_inventario']
        recepcion = ['compras.view_ordencompra', 'compras.view_recepcion', 'compras.add_recepcion']
        roles['Administrador'] += recepcion + ['compras.add_ordencompra', 'compras.anular_ordencompra',
            'compras.view_proveedor', 'compras.add_proveedor', 'compras.change_proveedor',
            'compras.view_eventocompra', 'compras.view_eventoproveedor']
        roles['Técnico en Farmacia'] += recepcion
        roles['Químico Farmacéutico'] += recepcion
        clinica = ['clinica.gestionar_clinica', 'clinica.view_receta', 'clinica.view_entrega']
        for rol in roles:
            roles[rol] += clinica
        roles['Químico Farmacéutico'] += ['clinica.revisar_receta', 'clinica.autorizar_controlado',
            'clinica.descargar_adjunto', 'clinica.view_asientocontrolado', 'gestion.revisar_condicion']
        roles['Administrador'] += ['gestion.administrar_usuarios', 'gestion.administrar_precios',
            'gestion.configurar_alertas', 'gestion.ver_auditoria', 'compras.exportar_compras',
            'comercio.add_convenio', 'comercio.change_convenio', 'comercio.view_convenio']
        roles['Químico Farmacéutico'] += ['gestion.configurar_alertas']
        for rol in ('Administrador', 'Vendedor'):
            roles[rol] += ['comercio.operar_caja', 'comercio.view_caja', 'comercio.emitir_documento', 'comercio.view_documento', 'comercio.view_convenio']
        for nombre, codigos in roles.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = []
            for codigo in codigos:
                app, codename = codigo.split('.')
                permisos.append(Permission.objects.get(content_type__app_label=app, codename=codename))
            grupo.permissions.set(permisos)
        self.stdout.write(self.style.SUCCESS('Roles de catálogo, inventario, venta, reportes y compras configurados. No se crearon cuentas.'))
