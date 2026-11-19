from django.core.management.base import BaseCommand
from compras.models import Proveedor


class Command(BaseCommand):
    help = 'Crea proveedores ficticios sin modificar proveedores existentes ni generar stock.'

    def handle(self, *args, **options):
        for codigo, nombre in [('PROV-DEMO-01', 'Distribuidora Académica Norte'),
                               ('PROV-DEMO-02', 'Abastecimiento Farmacéutico Demo')]:
            Proveedor.objects.get_or_create(codigo=codigo, defaults={
                'nombre': nombre, 'email': f'{codigo.lower()}@example.invalid'})
        self.stdout.write(self.style.SUCCESS('Proveedores ficticios preparados. Sin órdenes ni ingresos automáticos.'))
