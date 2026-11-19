import uuid
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from catalogo.models import Producto
from operaciones.models import Existencia, Lote, Movimiento


class Command(BaseCommand):
    help = 'Añade lotes y stock ficticios una sola vez por operación; no repone lo vendido al repetir.'

    @transaction.atomic
    def handle(self, *args, **options):
        productos = list(Producto.objects.select_for_update().filter(codigo__startswith='MED-', activo=True))
        if not productos:
            raise CommandError('Primero ejecuta cargar_medicamentos.')
        actor, nuevo = get_user_model().objects.get_or_create(username='sistema_stock_demo', defaults={'is_active': False})
        if nuevo:
            actor.set_unusable_password()
            actor.save(update_fields=['password'])
        creados = 0
        for producto in productos:
            for sufijo, dias, ubicacion, cantidad in [('CERCANO', 45, 'vitrina', 8), ('LARGO', 180, 'vitrina', 12), ('LARGO', 180, 'bodega', 20), ('VENCIDO', -7, 'vitrina', 3)]:
                codigo = f'DEMO-{producto.codigo}-{sufijo}'
                clave = uuid.uuid5(uuid.NAMESPACE_URL, f'farmacia-demo-stock-v1/{producto.codigo}/{sufijo}/{ubicacion}')
                if Movimiento.objects.filter(clave=clave).exists():
                    continue
                lote, _ = Lote.objects.get_or_create(producto=producto, codigo=codigo,
                    defaults={'vencimiento': timezone.localdate() + timedelta(days=dias)})
                stock, _ = Existencia.objects.get_or_create(lote=lote, ubicacion=ubicacion)
                stock.cantidad += cantidad
                stock.save(update_fields=['cantidad'])
                Movimiento.objects.create(clave=clave, lote=lote, tipo='ingreso', destino=ubicacion, cantidad=cantidad, usuario=actor)
                creados += 1
        self.stdout.write(self.style.SUCCESS(f'{creados} ingresos ficticios añadidos. Los vencidos no pueden venderse.'))
