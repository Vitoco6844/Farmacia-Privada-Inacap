"""Documenta el esquema real y mide consultas en una base temporal PostgreSQL."""
import json
import math
import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from uuid import uuid4


def documentar(connection, apps, salida):
    modulos = {'catalogo', 'clinica', 'comercio', 'compras', 'gestion', 'operaciones', 'seguridad'}
    tablas = sorted(m._meta.db_table for m in apps.get_models() if m._meta.app_label in modulos)
    texto = ['# Diccionario del esquema PostgreSQL', '',
             'Tipos y restricciones consultados en la base migrada. Incluye los módulos del proyecto.', '']
    resumen = dict.fromkeys(('tablas', 'pk', 'fk', 'unique', 'check', 'indices'), 0)
    sin_indice = []
    with connection.cursor() as c:
        resumen['tablas_totales'] = len(connection.introspection.table_names(c))
        for tabla in tablas:
            restricciones = connection.introspection.get_constraints(c, tabla)
            c.execute("""SELECT attname, format_type(atttypid, atttypmod), attnotnull
                         FROM pg_attribute WHERE attrelid = %s::regclass AND attnum > 0
                         AND NOT attisdropped ORDER BY attnum""", [tabla])
            texto += [f'## {tabla}', '', '| Columna | Tipo PostgreSQL | Admite nulo |',
                      '|---|---|---|']
            for campo, tipo, obligatorio in c.fetchall():
                texto.append(f"| `{campo}` | `{tipo}` | {'No' if obligatorio else 'Sí'} |")
            texto.append('')
            c.execute("""SELECT conname, pg_get_constraintdef(oid)
                         FROM pg_constraint WHERE conrelid = %s::regclass ORDER BY conname""", [tabla])
            for nombre, definicion in c.fetchall():
                texto.append(f'- `{nombre}`: `{definicion}`')
            c.execute("""SELECT indexname, indexdef FROM pg_indexes
                         WHERE schemaname = current_schema() AND tablename = %s ORDER BY indexname""", [tabla])
            indices = c.fetchall()
            for nombre, definicion in indices:
                texto.append(f'- Índice `{nombre}`: `{definicion}`')
            texto.append('')
            resumen['tablas'] += 1
            resumen['indices'] += len(indices)
            assert any(r['primary_key'] for r in restricciones.values()), tabla
            for restriccion in restricciones.values():
                for clave, atributo in (('pk', 'primary_key'), ('fk', 'foreign_key'),
                                        ('unique', 'unique'), ('check', 'check')):
                    if restriccion[atributo] and not (clave == 'unique' and
                            (restriccion['primary_key'] or restriccion['index'])):
                        resumen[clave] += 1
                if restriccion['foreign_key']:
                    assert len(restriccion['columns']) == 1, tabla
                    columna = restriccion['columns'][0]
                    c.execute("""SELECT EXISTS (SELECT 1 FROM pg_index i
                                 JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=i.indkey[0]
                                 WHERE i.indrelid=%s::regclass AND a.attname=%s AND i.indisvalid
                                 AND i.indpred IS NULL)""", [tabla, columna])
                    if not c.fetchone()[0]:
                        sin_indice.append(f'{tabla}.{columna}')
        resumen['fk_sin_indice_inicial'] = sin_indice
    (salida / 'diccionario-postgresql.md').write_text('\n'.join(texto), encoding='utf-8')
    return resumen


def medir(connection):
    from django.contrib.auth import get_user_model
    from django.db.models import F, Q, Sum
    from django.utils import timezone
    from catalogo.models import Categoria, Producto
    from operaciones.models import Venta, DetalleVenta

    usuario = get_user_model().objects.create_user('ensayo_esquema')
    categoria = Categoria.objects.create(nombre='Datos de ensayo')
    productos = Producto.objects.bulk_create([
        Producto(codigo=f'ENS-{i:05}', barras=f'990{i:010}', nombre=f'Producto sintético {i:05}',
                 presentacion='Caja', categoria=categoria, condicion=Producto.Condicion.DIRECTA, precio=1000)
        for i in range(10000)
    ])
    ventas = Venta.objects.bulk_create([Venta(usuario=usuario, total=1000) for _ in productos])
    hoy = timezone.localdate()
    zona = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(hoy, time.min), zona)
    fin = timezone.make_aware(datetime.combine(hoy + timedelta(days=1), time.min), zona)
    for semanas in range(10):
        lote = ventas[semanas * 1000:(semanas + 1) * 1000]
        Venta.objects.filter(id__gte=lote[0].id, id__lte=lote[-1].id).update(
            fecha=inicio + timedelta(hours=12, weeks=-semanas))
    DetalleVenta.objects.bulk_create([
        DetalleVenta(venta=v, producto=p, codigo=p.codigo, nombre=p.nombre, precio_unitario=1000, cantidad=1)
        for p, v in zip(productos, ventas)
    ])
    with connection.cursor() as c:
        c.execute('ANALYZE')
    clave = '09999'
    detalle = DetalleVenta.objects.all()
    por_fecha = detalle.filter(venta__fecha__date__gte=hoy, venta__fecha__date__lte=hoy)
    por_rango = detalle.filter(venta__fecha__gte=inicio, venta__fecha__lt=fin)
    assert (por_fecha.aggregate(total=Sum(F('precio_unitario') * F('cantidad')))
            == por_rango.aggregate(total=Sum(F('precio_unitario') * F('cantidad')))
            == {'total': 1000000})

    consultas = {
        'catalogo_parcial': Producto.objects.select_related('categoria').filter(
            Q(nombre__icontains=clave) | Q(codigo__icontains=clave) | Q(barras__icontains=clave))[:6],
        'barras_exactas': Producto.objects.filter(barras=productos[-1].barras),
        'indicador_por_fecha': por_fecha.order_by().values('producto_id').annotate(total=Sum('cantidad')),
        'indicador_por_rango': por_rango.order_by().values('producto_id').annotate(total=Sum('cantidad')),
    }
    resultados = {}
    for nombre, consulta in consultas.items():
        consulta.explain(analyze=True, buffers=True)
        ejecuciones = [json.loads(consulta.explain(analyze=True, buffers=True, format='json'))[0]
                       for _ in range(20)]
        tiempos = sorted(p['Execution Time'] for p in ejecuciones)
        resultados[nombre] = {'p95_ms': tiempos[math.ceil(.95 * len(tiempos)) - 1],
                              'muestras_ms': tiempos, 'plan': ejecuciones[-1]}
    return resultados


def main(backend, salida):
    sys.path.insert(0, str(backend))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    import django
    django.setup()
    from django.apps import apps
    from django.conf import settings
    from django.db import connection
    from django.test.runner import DiscoverRunner

    d = connection.settings_dict
    assert (connection.vendor, d['HOST'], str(d['PORT']), d['NAME']) == (
        'postgresql', '127.0.0.1', '55432', 'farmacia')
    salida.mkdir(parents=True, exist_ok=True)
    resultado = {'version': connection.pg_version, 'esquema': documentar(connection, apps, salida),
                 'ensayo': {'productos': 10000, 'ventas': 10000, 'detalles': 10000,
                            'ventas_filtradas': 1000, 'clientes': 1, 'muestras_por_consulta': 20}}
    settings.DATABASES['default']['TEST']['NAME'] = f"test_farmacia_esquema_{uuid4().hex[:12]}"
    runner = DiscoverRunner(verbosity=0, interactive=False)
    bases = runner.setup_databases()
    try:
        assert connection.settings_dict['NAME'].startswith('test_farmacia_esquema_')
        resultado['consultas'] = medir(connection)
    finally:
        runner.teardown_databases(bases)
    (salida / 'medicion-postgresql.json').write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({**resultado['esquema'], 'p95_ms': {
        k: v['p95_ms'] for k, v in resultado['consultas'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
