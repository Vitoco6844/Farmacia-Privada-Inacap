"""Medición reproducible en una base de pruebas descartable, nunca en la base de uso."""
import argparse
from datetime import timedelta
from io import StringIO
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter
import uuid

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def medir(nombre, funcion, repeticiones, objetivo_ms):
    funcion()  # Calentamiento excluido de las estadísticas.
    muestras = []
    for _ in range(repeticiones):
        inicio = perf_counter()
        funcion()
        muestras.append(round((perf_counter() - inicio) * 1000, 3))
    p95 = sorted(muestras)[math.ceil(len(muestras) * .95) - 1]
    return {'caso': nombre, 'repeticiones': repeticiones, 'muestras_ms': muestras,
        'mediana_ms': round(statistics.median(muestras), 3), 'p95_ms': p95,
        'max_ms': max(muestras), 'objetivo_p95_ms': objetivo_ms, 'cumple_objetivo': p95 <= objetivo_ms}


def ejecutar(salida, sqlite_temporal=False):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    if sqlite_temporal:
        settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
    else:
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
            raise RuntimeError('Se requiere PostgreSQL o --sqlite-temporal explícito.')
        settings.DATABASES['default']['TEST'] = {'NAME': 'test_farmacia_rend_' + uuid.uuid4().hex[:12]}
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.core.management import call_command
    from django.test import Client
    from django.test.runner import DiscoverRunner
    from django.utils import timezone
    from catalogo.models import Categoria, Producto
    from compras.models import Proveedor, OrdenCompra, Recepcion
    from compras.services import crear_orden, recibir_orden
    from operaciones.models import Lote, Existencia, Venta, DetalleVenta

    runner = DiscoverRunner(verbosity=0, interactive=False)
    runner.setup_test_environment()
    configuracion = None
    try:
        configuracion = runner.setup_databases()
        call_command('configurar_roles', stdout=StringIO())
        usuario = get_user_model().objects.create_user('evaluacion_rendimiento')
        usuario.groups.add(Group.objects.get(name='Administrador'))
        categoria = Categoria.objects.create(nombre='Datos sintéticos de rendimiento')
        productos = Producto.objects.bulk_create([Producto(codigo=f'REND-{i:04}', barras=f'990{i:010}',
            nombre=f'Medicamento sintético {i:04}', presentacion='Caja de ensayo', categoria=categoria,
            condicion='Venta directa', precio=1500 + i, stock_minimo=10) for i in range(500)])
        fecha = timezone.localdate() + timedelta(days=30)
        lotes = Lote.objects.bulk_create([Lote(producto=p, codigo=f'LOTE-{j}', vencimiento=fecha + timedelta(days=j * 60))
            for p in productos for j in range(2)])
        Existencia.objects.bulk_create([Existencia(lote=lote, ubicacion=ubicacion, cantidad=20)
            for lote in lotes for ubicacion in ['bodega', 'vitrina']])
        ventas = Venta.objects.bulk_create([Venta(usuario=usuario, total=productos[i].precio * 2) for i in range(300)])
        DetalleVenta.objects.bulk_create([DetalleVenta(venta=venta, producto=productos[i], codigo=productos[i].codigo,
            nombre=productos[i].nombre, precio_unitario=productos[i].precio, cantidad=2) for i, venta in enumerate(ventas)])
        proveedor = Proveedor.objects.create(codigo='REND', nombre='Proveedor sintético')

        def comprar_y_recibir():
            orden = crear_orden(usuario=usuario, proveedor_id=proveedor.pk, clave=uuid.uuid4(), observaciones='Ensayo',
                lineas=[{'producto_id': productos[0].pk, 'cantidad': 2, 'costo_unitario': 1000}])
            recibir_orden(usuario=usuario, orden_id=orden.pk, referencia=f'REND-{orden.pk}', clave=uuid.uuid4(),
                partidas=[{'linea_id': orden.lineas.get().pk, 'codigo': 'REND-RECIBIDO', 'vencimiento': fecha,
                    'ubicacion': 'bodega', 'cantidad': 2}])
            orden.refresh_from_db()
            if orden.estado != 'completa':
                raise AssertionError('La escritura no completó la orden.')

        for _ in range(40):
            comprar_y_recibir()
        cliente = Client()
        cliente.force_login(usuario)

        def consultar(ruta, firma=None):
            respuesta = cliente.get(ruta)
            if respuesta.status_code != 200:
                raise AssertionError(f'{ruta}: HTTP {respuesta.status_code}')
            if firma and not respuesta.content.startswith(firma):
                raise AssertionError(f'{ruta}: formato de archivo inesperado')

        iniciales = {'productos': Producto.objects.count(), 'lotes': Lote.objects.count(),
            'existencias': Existencia.objects.count(), 'ventas': Venta.objects.count(),
            'ordenes': OrdenCompra.objects.count(), 'recepciones': Recepcion.objects.count()}
        resultados = []
        for nombre, ruta in [('Catálogo', '/productos/'), ('Inventario', '/inventario/'),
                ('Panel', '/inicio/'), ('Compras', '/compras/'), ('Reporte inventario HTML', '/reportes/inventario/')]:
            resultados.append(medir(nombre, lambda ruta=ruta: consultar(ruta), 20, 1000))
        resultados.append(medir('Orden y recepción transaccional', comprar_y_recibir, 10, 1000))
        resultados.append(medir('Inventario PDF completo', lambda: consultar('/reportes/inventario/?formato=pdf', b'%PDF'), 5, 5000))
        resultados.append(medir('Inventario Excel completo', lambda: consultar('/reportes/inventario/?formato=xlsx', b'PK'), 5, 5000))
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
        cambios = subprocess.run(['git', 'status', '--porcelain'], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
        informe = {'fecha': timezone.now().isoformat(), 'commit_base': commit, 'incluye_cambios_locales': bool(cambios.strip()),
            'python': platform.python_version(), 'django': django.get_version(), 'sistema': platform.system(),
            'base': 'SQLite temporal en memoria' if sqlite_temporal else 'PostgreSQL de pruebas descartable',
            'volumen_inicial': iniciales, 'clientes_simultaneos': 1,
            'metodo': 'Cliente HTTP de pruebas Django, sin red ni navegador; una ejecución de calentamiento por caso; p95 por rango más próximo.',
            'limites': ['No mide latencia de red, CSS/JavaScript ni experiencia visual.',
                'Ensayo secuencial; no acredita carga concurrente ni capacidad de producción.',
                'Las ventas de la carga sintética no representan una conciliación de movimientos.',
                'Objetivos internos de evaluación, no SLA acordado con docente ni garantía de servicio.',
                'SQLite no acredita rendimiento ni bloqueos de PostgreSQL.'] if sqlite_temporal else [
                'No mide red, renderizado visual ni carga concurrente.', 'Objetivos internos, sin garantía de producción.',
                'Las ventas sintéticas no representan una conciliación de movimientos.'],
            'resultados': resultados}
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Evidencia: {salida}')
        for fila in resultados:
            print(f"{fila['caso']}: p95 {fila['p95_ms']} ms; objetivo {fila['objetivo_p95_ms']} ms; {'CUMPLE' if fila['cumple_objetivo'] else 'REVISAR'}")
    finally:
        if configuracion is not None:
            runner.teardown_databases(configuracion)
        runner.teardown_test_environment()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite-temporal', action='store_true', help='Solo ensayo auxiliar; no valida PostgreSQL.')
    parser.add_argument('--salida', type=Path, default=RAIZ / 'docs/evaluacion/evidencias/rendimiento-postgresql.json')
    argumentos = parser.parse_args()
    ejecutar(argumentos.salida, argumentos.sqlite_temporal)
