from pathlib import Path
import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Crea cuentas locales ficticias con claves aleatorias. No restablece cuentas existentes.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write('Solo se permite crear cuentas de demostración con DEBUG=true.')
            return
        cuentas = []
        with transaction.atomic():
            for nombre, rol in [
                ('admin_demo', 'Administrador'), ('vendedor_demo', 'Vendedor'),
                ('tecnico_demo', 'Técnico en Farmacia'), ('qf_demo', 'Químico Farmacéutico'),
            ]:
                grupo = Group.objects.get(name=rol)
                if not get_user_model().objects.filter(username=nombre).exists():
                    clave = secrets.token_urlsafe(18)
                    usuario = get_user_model().objects.create_user(username=nombre, password=clave)
                    usuario.groups.add(grupo)
                    cuentas.append(f'Usuario: {nombre}\nContraseña: {clave}\nRol: {rol}\n')
            if cuentas:
                destino = Path(settings.BASE_DIR) / 'work' / 'accesos-locales.txt'
                destino.parent.mkdir(parents=True, exist_ok=True)
                with destino.open('a', encoding='utf-8') as archivo:
                    archivo.write('\n'.join(cuentas))
        self.stdout.write('Cuentas listas. Las claves nuevas están en work/accesos-locales.txt (no versionado).')
