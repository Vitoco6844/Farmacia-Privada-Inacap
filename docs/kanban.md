# Kanban de la entrega

**Período de trabajo:** 06/11/2026–23/11/2026.  
**Cierre del cronograma:** 23/11/2026, con el modo nocturno, los gráficos del panel del turno y las correcciones de los flujos existentes.

Las fechas corresponden al cronograma de la entrega. Los rangos intermedios ordenan el trabajo por dependencias y las evidencias conservan sus propias fechas. El tablero indica el reparto de responsables y revisores del equipo.

| ID | Tarea | Responsable / revisor | Depende de | Estado y evidencia |
|---|---|---|---|---|
| K01 | Preparar copia local, matriz y decisiones | Vicente + Ignacio | — | En revisión · [matriz de alcance](matriz-alcance.md). |
| K02 | Configurar PostgreSQL local, migrar y documentar | Ignacio / Vicente | K01 | En revisión · [evidencia de PostgreSQL local](evidencia-postgresql-local.txt). |
| K03 | Definir la API y adaptar el backend por flujo | Ignacio / Vicente | K02 | En revisión · [primer flujo de API](primer-flujo-api.md) y [flujos operativos](flujos-operativos.md). |
| K04 | Construir el frontend independiente por flujo | Vicente / Ignacio | K02 y contrato del flujo en K03 | En revisión · [compras e inventario](flujo-compras-inventario.md) y [flujos operativos](flujos-operativos.md). |
| K05 | Comprobar esquema, índices y consultas | Ignacio / Vicente | K02 | En revisión · [revisión de PostgreSQL](esquema/revision-postgresql.md). |
| K06 | Cerrar seguridad, estáticos y respaldo/restauración | Ignacio / Vicente | K02, K03 | Pendiente · revisión final de seguridad, avisos de SonarQube y comprobación de restauración. |
| K07 | Ejecutar pruebas y clasificar diferencias | Vicente + Ignacio | K03–K05 para recorridos locales y K06 para el cierre de seguridad | Realizada · [recorrido local documentado](validacion-navegador.md). |
| K08 | Actualizar documentos y preparar la demostración | Vicente / Ignacio | Resultados de K07 | En curso · [checklist para el profesor](checklist-demostracion-profesor.md). |
| K09 | Preparar y desplegar en AWS para el cliente | Ignacio + Vicente | K06, K08 y entorno AWS acordado | Etapa posterior. |

## Cronograma por semana

| Fecha | Tareas | Trabajo y orden de integración |
|---|---|---|
| 06–08/11/2026 | K01 | Vicente e Ignacio organizaron el alcance, las pantallas y el orden de trabajo. |
| 09–13/11/2026 | K02–K05 | Ignacio se encargó de PostgreSQL y del contrato de acceso y catálogo. Vicente se encargó de conectar la interfaz de esos dos flujos una vez definido el contrato. Con las tablas migradas se pudo revisar el esquema y sus índices. |
| 16–19/11/2026 | K03, K04, K07 | Se integraron compras y recepción antes de probar el traslado de los lotes recibidos. Con el inventario y la caja preparados se pudo probar el punto de venta, su comprobante y el cierre. En clínica, el registro de la receta precedió a la revisión del QF y a la entrega. Con esos movimientos registrados se revisaron indicadores y reportes. |
| 20–22/11/2026 | K07, K08 | Se ordenaron los casos de revisión y el guion de la demostración a partir del recorrido local. |
| 23/11/2026 | K03, K04, K07 | Cierre de la ronda de cambios. Se incorporaron el modo nocturno con preferencia persistente y los gráficos sobre los datos del turno. También se incorporó la validación unificada de RUT en formularios existentes y se corrigieron flujos y duplicados. [Registro de cambios](../CAMBIOS.md). |
