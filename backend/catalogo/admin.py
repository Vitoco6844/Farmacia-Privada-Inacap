from django.contrib import admin
from .models import Categoria, EventoCatalogo

admin.site.register(Categoria)


@admin.register(EventoCatalogo)
class EventoCatalogoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'accion', 'producto']
    list_filter = ['accion']
    readonly_fields = ['producto', 'usuario', 'accion', 'fecha', 'anterior', 'posterior']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
