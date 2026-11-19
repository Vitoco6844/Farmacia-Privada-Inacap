from django.contrib import admin
from .models import EventoAcceso


@admin.register(EventoAcceso)
class EventoAccesoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'resultado', 'cuenta', 'origen']
    list_filter = ['resultado']
    readonly_fields = ['fecha', 'resultado', 'cuenta', 'origen']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
