from django.core.management.base import BaseCommand
from django.db import transaction
from catalogo.datos_demo import PRODUCTOS
from catalogo.models import Categoria, Producto


class Command(BaseCommand):
    help = 'Crea productos ficticios faltantes sin sobrescribir los existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        creados = 0
        for demo in PRODUCTOS:
            categoria, _ = Categoria.objects.get_or_create(nombre=demo['categoria'])
            datos = {k: v for k, v in demo.items() if k not in ('codigo', 'categoria', 'iniciales')}
            _, nuevo = Producto.objects.get_or_create(codigo=demo['codigo'], defaults={**datos, 'categoria': categoria})
            creados += int(nuevo)
        self.stdout.write(self.style.SUCCESS(f'{creados} productos ficticios creados.'))
