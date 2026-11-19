from django.contrib import admin
from .models import EventoCompra, EventoProveedor


class HistorialAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoCompra)
class EventoCompraAdmin(HistorialAdmin):
    list_display = ['fecha', 'orden', 'usuario', 'accion']
    list_filter = ['accion']
    readonly_fields = ['fecha', 'orden', 'usuario', 'accion', 'motivo']


@admin.register(EventoProveedor)
class EventoProveedorAdmin(HistorialAdmin):
    list_display = ['fecha', 'proveedor', 'usuario']
    readonly_fields = ['fecha', 'proveedor', 'usuario', 'anterior', 'posterior']
