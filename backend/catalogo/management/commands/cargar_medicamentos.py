from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from catalogo.medicamentos_referencia import FECHA_CONSULTA, MEDICAMENTOS
from catalogo.models import Categoria, EventoCatalogo, PrecioReferencia, Producto


class Command(BaseCommand):
    help = 'Añade seis medicamentos con precios referenciales y fuentes, sin sobrescribir productos existentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        categoria, _ = Categoria.objects.get_or_create(nombre='Medicamentos')
        actor, creado_actor = get_user_model().objects.get_or_create(username='sistema_carga_referencias',
            defaults={'is_active': False})
        if creado_actor:
            actor.set_unusable_password()
            actor.save(update_fields=['password'])
        creados = 0
        for datos in MEDICAMENTOS:
            campos = {k: datos[k] for k in ('barras', 'nombre', 'presentacion', 'precio', 'condicion')}
            producto, creado = Producto.objects.get_or_create(codigo=datos['codigo'], defaults={**campos, 'categoria': categoria})
            if creado:
                EventoCatalogo.objects.create(producto=producto, usuario=actor, accion='crear',
                    posterior={k: str(v) for k, v in campos.items()})
            PrecioReferencia.objects.get_or_create(producto=producto, fuente=datos['fuente'], consultado=FECHA_CONSULTA,
                defaults={k: datos[k] for k in ('precio', 'farmacia', 'tipo', 'nota')})
            creados += int(creado)
        self.stdout.write(self.style.SUCCESS(f'{creados} medicamentos añadidos; referencias del {FECHA_CONSULTA}.'))
