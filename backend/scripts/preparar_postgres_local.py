"""Instancia PostgreSQL de desarrollo aislada, en work/, sin modificar servicios existentes."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess

import psycopg
from psycopg import sql
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pg-bin', type=Path, default=Path('C:/Program Files/PostgreSQL/18/bin'))
    args = parser.parse_args()
    data = ROOT / 'work' / 'postgres'
    secret_file = ROOT / 'work' / 'postgres-bootstrap.secret'
    env_file = ROOT / '.env'
    pgctl = args.pg_bin / 'pg_ctl.exe'
    if not pgctl.exists():
        parser.error('Indica --pg-bin con la carpeta bin de PostgreSQL instalado.')
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    def run(*command, check=True):
        return subprocess.run([str(x) for x in command], check=check, creationflags=flags)

    if not (data / 'PG_VERSION').exists():
        if env_file.exists():
            parser.error('Ya existe .env. No se reemplazará una configuración existente; configura tu servidor manualmente.')
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        secret_file.write_text(secrets.token_urlsafe(32), encoding='utf-8')
        run(args.pg_bin / 'initdb.exe', '-D', data, '-U', 'farmacia_bootstrap',
            '--pwfile', secret_file, '-A', 'scram-sha-256', '--encoding=UTF8', '--locale=C')
    if not secret_file.exists():
        parser.error('Falta la clave local de inicialización; no se modificará la instancia.')
    status = subprocess.run([str(pgctl), '-D', str(data), 'status'], capture_output=True, creationflags=flags)
    if status.returncode != 0:
        run(pgctl, '-D', data, '-l', ROOT / 'work' / 'postgres.log', '-o', '-h 127.0.0.1 -p 55432', '-w', 'start')
    if not env_file.exists():
        env_file.write_text(
            f'DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}\nDJANGO_DEBUG=true\n'
            'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,[::1]\nPOSTGRES_DB=farmacia\n'
            f'POSTGRES_USER=farmacia_app\nPOSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n'
            'POSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT=55432\n', encoding='utf-8')
    env = dotenv_values(env_file)
    if env.get('POSTGRES_HOST') != '127.0.0.1' or env.get('POSTGRES_PORT') != '55432':
        parser.error('El .env no corresponde a esta instancia aislada; no se modificarán sus credenciales.')
    with psycopg.connect(host='127.0.0.1', port=55432, dbname='postgres', user='farmacia_bootstrap',
            password=secret_file.read_text(encoding='utf-8').strip(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [env['POSTGRES_USER']])
            if not cur.fetchone():
                # CREATEDB se necesita exclusivamente para la base descartable de pruebas de Django.
                cur.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER CREATEDB PASSWORD {}').format(
                    sql.Identifier(env['POSTGRES_USER']), sql.Literal(env['POSTGRES_PASSWORD'])))
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', [env['POSTGRES_DB']])
            if not cur.fetchone():
                cur.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(
                    sql.Identifier(env['POSTGRES_DB']), sql.Identifier(env['POSTGRES_USER'])))
    print('PostgreSQL local listo en 127.0.0.1:55432. Credenciales guardadas en .env, excluido de Git.')


if __name__ == '__main__':
    main()
