from django.contrib import admin
from .models import EventoReporte


@admin.register(EventoReporte)
class EventoReporteAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'usuario', 'tipo', 'formato', 'filas', 'total']
    list_filter = ['tipo', 'formato']
    readonly_fields = ['fecha', 'usuario', 'tipo', 'formato', 'filtros', 'filas', 'total']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
