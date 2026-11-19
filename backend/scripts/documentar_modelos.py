"""Genera el diccionario desde los modelos, sin conectarse a la base de datos."""
import os
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.apps import apps


def celda(valor):
    return str(valor).replace('|', '\\|').replace('\n', ' ')


def generar():
    lineas = ['# Diccionario de datos implementado', '',
        'Generado por `scripts/documentar_modelos.py` desde los modelos Django. No consulta registros ni expone credenciales.', '',
        'La base elegida es PostgreSQL. Los campos JSON de auditoría pertenecen a la misma base relacional. '
        'Los FK tienen índice implícito salvo indicación del modelo; PK y UNIQUE crean sus índices. '
        'No se proponen índices adicionales sin medición. Las reglas entre varias filas se completan en los servicios transaccionales.', '']
    for etiqueta in ['auth', 'catalogo', 'operaciones', 'seguridad', 'compras']:
        for modelo in apps.get_app_config(etiqueta).get_models():
            lineas += [f'## {modelo._meta.label}', '', f'Tabla: `{modelo._meta.db_table}`.', '',
                '| Campo | Tipo Django | Nulo | Claves / relación |', '| --- | --- | --- | --- |']
            for campo in modelo._meta.local_fields:
                claves = []
                if campo.primary_key:
                    claves.append('PK')
                elif campo.unique:
                    claves.append('UNIQUE')
                if campo.is_relation:
                    claves.append(f'FK → {campo.related_model._meta.label}; {campo.remote_field.on_delete.__name__}')
                elif campo.db_index:
                    claves.append('índice')
                tipo = campo.get_internal_type()
                if hasattr(campo, 'max_digits'):
                    tipo += f'({campo.max_digits},{campo.decimal_places})'
                elif campo.max_length:
                    tipo += f'({campo.max_length})'
                lineas.append(f'| {campo.name} | {tipo} | {"Sí" if campo.null else "No"} | {celda("; ".join(claves) or "—")} |')
            for campo in modelo._meta.local_many_to_many:
                lineas += ['', f'Relación N:M `{campo.name}` → `{campo.related_model._meta.label}` mediante `{campo.remote_field.through._meta.db_table}`.']
            for campos in modelo._meta.unique_together:
                lineas += ['', f'Unicidad compuesta: `{", ".join(campos)}`.']
            for campo in modelo._meta.local_fields:
                if campo.choices:
                    lineas += ['', f'Valores permitidos en formulario/modelo para `{campo.name}`: ' +
                        '; '.join(f'`{celda(valor)}` ({celda(etiqueta)})' for valor, etiqueta in campo.flatchoices) + '.']
            if modelo._meta.constraints:
                lineas += ['', 'Restricciones declaradas:']
                lineas.extend(f'- `{celda(restriccion)}`' for restriccion in modelo._meta.constraints)
            if modelo._meta.indexes:
                lineas += ['', 'Índices explícitos:']
                lineas.extend(f'- `{celda(indice)}`' for indice in modelo._meta.indexes)
            lineas += ['']
    lineas += ['## Reglas de negocio complementarias', '',
        '- Stock: los servicios bloquean usuario/producto y registran cantidades y movimientos en una transacción.',
        '- Compra: recibida ≤ solicitada por línea; suma de partidas ≤ saldo; referencia normalizada única por orden; la recepción enlaza línea y movimiento de esa orden.',
        '- Venta: FEFO desde vitrina y solo condición de venta directa; precios y nombres históricos en el detalle.',
        '- Auditoría: sin interfaz operativa de edición/borrado; las FK históricas usan PROTECT. Un administrador de la base mantiene capacidad técnica de modificación.',
        '- Acceso: contraseñas almacenadas como hash Django; límites de cuenta/origen mediante HMAC, sin contraseña ni IP en claro en esos eventos.', '']
    destino = RAIZ / 'docs/evaluacion/diccionario-datos.md'
    destino.write_text('\n'.join(lineas), encoding='utf-8')
    print(destino)


if __name__ == '__main__':
    generar()
