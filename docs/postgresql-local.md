# PostgreSQL local para Farmacia

La instancia de desarrollo usa la base `farmacia`, el usuario `farmacia_app` y la dirección `127.0.0.1:55432`. La preparación genera las contraseñas en `backend/.env` y en `backend/work/`. Para las pruebas, Django crea y elimina una base separada llamada `test_farmacia`.

## Preparar en Windows

Ejecutar desde `Farmacia/backend` en PowerShell. La preparación se verificó con Python 3.12 y PostgreSQL 17.11 de 64 bits. El script busca los binarios en `work/herramientas/pgsql/bin`. Para usar una instalación existente, pasar `-PgBin` con su carpeta `bin`. En este equipo la instancia tiene sus propios datos y usa una copia de los binarios de la evaluación anterior. [Descargas para Windows](https://www.postgresql.org/download/windows/).

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\scripts\configurar_entorno_local.ps1" -Verificar
```

El script inicializa PostgreSQL, aplica las migraciones, configura los grupos y carga datos ficticios. `-Verificar` comprueba migraciones, ejecuta pruebas de catálogo y concurrencia, y muestra el motor, la base y los recuentos. Si ya existe un entorno Python con las dependencias de `requirements.txt`, se puede pasar su ejecutable con `-Python`.

## Resultado local

El 19/11/2026 se aplicaron las migraciones a PostgreSQL 17.11. La base `farmacia` contiene 50 tablas, incluidos los componentes propios de Django, cuatro grupos y 14 productos de demostración. Se ejecutaron 29 pruebas de catálogo y concurrencia en `test_farmacia`. Pasaron las 29, incluidas las seis de concurrencia omitidas anteriormente en SQLite. [Registro de la ejecución](evidencia-postgresql-local.txt).

## Iniciar Django

Con PostgreSQL iniciado, desde la misma carpeta:

```powershell
& ".\.venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8014 --settings=config.settings
```

Abrir [http://127.0.0.1:8014/](http://127.0.0.1:8014/). Este acceso sirve para comprobar el backend mediante sus pantallas de referencia. Las cuentas ficticias iniciales se generan en `work/accesos-locales.txt`.

En el equipo donde se hizo esta preparación, también se puede iniciar desde el backend con el entorno Python ya disponible:

```powershell
& "C:\Users\vimat\Documents\ChatGPT\Proyecto Integrado\.venv-pi\Scripts\python.exe" manage.py runserver 127.0.0.1:8014 --settings=config.settings
```

## Consultar tablas y detener la instancia

Para ver la base en un visor como pgAdmin, usar servidor `127.0.0.1`, puerto `55432`, base `farmacia`, usuario `farmacia_app` y la contraseña local de `POSTGRES_PASSWORD` del archivo `.env`.

Detener Django con Ctrl+C. Si se usaron los binarios portátiles, detener PostgreSQL así:

```powershell
& ".\work\herramientas\pgsql\bin\pg_ctl.exe" -D ".\work\postgres" -m fast stop
```

Para volver a iniciar PostgreSQL, ejecutar otra vez `configurar_entorno_local.ps1`. El script conserva la configuración y vuelve a aplicar las tareas de preparación.
