# Pruebas de la versión ampliada

Actualizado el 20 de octubre de 2026. Esta actualización documental reutiliza la ejecución guardada; no se ha vuelto a ejecutar la suite.

| Comprobación | Resultado registrado | Alcance |
|---|---|---|
| Runner Django | 172 casos: 166 aprobados, 6 omitidos; cero fallos y errores | Base temporal SQLite; las seis pruebas de concurrencia requieren PostgreSQL. |
| Migraciones | `No changes detected` | Modelos sin cambios pendientes de generar; no demuestra despliegue PostgreSQL. |
| Esquema local | 40 modelos/tablas de negocio, 63 relaciones FK/uno a uno, 33 restricciones Meta | Introspección SQLite; no incluye las tablas estándar de Django en ese recuento. |
| Navegador | Apertura de caja, búsqueda, venta ficticia y emisión académica observadas | Muestreo; no todas las interacciones de todas las pantallas. |
| Menú | 16 enlaces con estructura uniforme tras corregir el espaciado | Revalidación visual local; no matriz completa de dispositivos. |

Evidencia: [salida del runner](../revision-actual/pruebas.txt), [esquema](../revision-actual/resumen-esquema.txt) y [captura del menú](../revision-actual/menu-corregido.png).

## Ejecución manual pendiente

Usar la [checklist de demostración](checklist-demostracion.md). Marcar únicamente lo observado y registrar cualquier incidencia. La existencia de una vista, un formulario o un test no acredita que se haya realizado la demostración en navegador.

## Reproducir la suite cuando sea necesario

Desde la raíz del proyecto, con el entorno Python del proyecto activado:

```powershell
python -B manage.py test --settings=config.demo_settings --noinput
python -B manage.py makemigrations --check --dry-run --settings=config.demo_settings
```

El primer comando crea y destruye una base de pruebas separada. Para acreditar concurrencia se necesita una ejecución completa contra PostgreSQL configurado y revisar que no se omitan esos casos.

La [medición de rendimiento](rendimiento.md) es histórica, secuencial y del alcance anterior. No acredita el rendimiento actual ni carga concurrente. Las salidas anteriores permanecen en evidencias y la versión previa de este documento en historico-2026-10-19.
