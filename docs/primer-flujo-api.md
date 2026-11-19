# Primer flujo del frontend

El frontend es HTML, CSS y JavaScript en `frontend/`. Django ejecuta la API y lee los productos en PostgreSQL. El servidor Node de desarrollo atiende la interfaz y reenvía las llamadas de la API a Django por el mismo origen para conservar cookies y protección CSRF.

Con PostgreSQL iniciado, abrir dos terminales desde la carpeta Farmacia:

```powershell
cd backend
& "C:\Users\vimat\Documents\ChatGPT\Proyecto Integrado\.venv-pi\Scripts\python.exe" -B manage.py runserver 127.0.0.1:8014 --settings=config.settings
```

```powershell
cd frontend
node servidor-local.mjs
```

Abrir [Farmacia local](http://127.0.0.1:8015/). Usar una de las cuentas ficticias de `backend/work/accesos-locales.txt`. El catálogo muestra hasta doce productos por página y permite buscar por nombre, código o código de barras. El precio mostrado es el precio base del catálogo. Cerrar sesión bloquea las nuevas consultas hasta volver a autenticarse.

| Método y ruta | Comportamiento |
|---|---|
| GET `/api/v1/sesion/` | Devuelve usuario actual o valor nulo, más el token CSRF. |
| POST `/api/v1/sesion/ingresar/` | Recibe `username` y `password` como formulario. Devuelve sesión, 401 por credenciales inválidas o 429 ante límite de intentos. |
| POST `/api/v1/sesion/salir/` | Cierra la sesión. |
| GET `/api/v1/productos/?q=texto&pagina=1` | Devuelve resultados paginados. Responde 401 sin sesión y 403 sin permiso de catálogo. |

Enviar `X-CSRFToken` en las operaciones POST y usar el token devuelto después de ingresar. El servidor Node es para desarrollo en loopback. La configuración del proxy de despliegue se definirá en la etapa AWS.
