"""Ejecuta la suite en una base descartable y conserva salida y resumen verificables."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def ejecucion_completa(descubiertos, resultado):
    return resultado.testsRun == descubiertos and not resultado.shouldStop


def ejecutar(salida, sqlite_temporal):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    if sqlite_temporal:
        settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
    else:
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
            raise RuntimeError('La suite final requiere PostgreSQL o --sqlite-temporal explícito.')
        settings.DATABASES['default']['TEST'] = {'NAME': 'test_farmacia_eval_' + uuid.uuid4().hex[:12]}
    import django
    django.setup()
    from django.test.runner import DiscoverRunner
    from django.utils import timezone

    class RegistroRunner(DiscoverRunner):
        resultado = None
        descubiertos = 0

        def run_suite(self, suite, **kwargs):
            self.descubiertos = suite.countTestCases()
            self.resultado = super().run_suite(suite, **kwargs)
            return self.resultado

    runner = RegistroRunner(verbosity=2, interactive=False)
    captura = StringIO()
    with redirect_stdout(captura), redirect_stderr(captura):
        fallos = runner.run_tests(['catalogo', 'operaciones', 'seguridad', 'compras'])
    resultado = runner.resultado
    if resultado is None:
        raise RuntimeError('La suite no llegó a producir resultados.')
    completa = ejecucion_completa(runner.descubiertos, resultado)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
    informe = {'fecha': timezone.now().isoformat(), 'commit_base': commit,
        'version': 'Árbol de trabajo con cambios locales; revisar git status antes del commit final.',
        'base': 'SQLite temporal en memoria' if sqlite_temporal else 'PostgreSQL de pruebas descartable',
        'python': sys.version.split()[0], 'django': django.get_version(),
        'descubiertos': runner.descubiertos, 'ejecucion_completa': completa,
        'ejecutados_incluyendo_omitidos': resultado.testsRun,
        'fallos': len(resultado.failures), 'errores': len(resultado.errors),
        'omitidos': [{'caso': str(caso), 'motivo': motivo} for caso, motivo in resultado.skipped],
        'aprobados': resultado.testsRun - len(resultado.failures) - len(resultado.errors) - len(resultado.skipped),
        'resultado': 'INCOMPLETO' if not completa else ('OK' if not fallos else 'FALLO'),
        'limite': 'Una base sin bloqueos no verifica concurrencia PostgreSQL; consultar los casos omitidos.'}
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.with_suffix('.txt').write_text(captura.getvalue(), encoding='utf-8')
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{informe['resultado']}: {informe['aprobados']} aprobados, {len(resultado.skipped)} omitidos, {len(resultado.failures)} fallos, {len(resultado.errors)} errores.")
    print(f'Evidencias: {salida} y {salida.with_suffix(".txt")}')
    return bool(fallos) or not completa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite-temporal', action='store_true')
    parser.add_argument('--salida', type=Path, default=RAIZ / 'docs/evaluacion/evidencias/pruebas-postgresql.json')
    args = parser.parse_args()
    sys.exit(ejecutar(args.salida, args.sqlite_temporal))
