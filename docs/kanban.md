# Kanban de la entrega

**Inicio del cronograma:** 06/11/2026.  
**Último cambio previsto:** 23/11/2026. La fecha efectiva se registra al verificar el cambio.

Estados de trabajo: Pendiente → En curso → En revisión → Validado. Una tarea activa por integrante. La revisión cruzada verifica el resultado y su evidencia. El reparto es el acordado como propuesta para la entrega. Los aportes efectivamente realizados se acreditarán con sus archivos, cambios o resultados.

| ID | Tarea | Responsable / revisor | Depende de | Estado y evidencia esperada |
|---|---|---|---|---|
| K01 | Preparar copia local, matriz y decisiones | Vicente + Ignacio | — | En revisión · estructura y documentos del paso 1. |
| K02 | Configurar PostgreSQL local, migrar y documentar | Ignacio / Vicente | K01 | En revisión · PostgreSQL 17.11, 50 tablas y 29 pruebas aprobadas. [Evidencia](evidencia-postgresql-local.txt). |
| K03 | Definir API y adaptar backend por flujo | Ignacio / Vicente | K02 | En revisión · acceso, catálogo y [flujos operativos conectados](flujos-operativos.md). |
| K04 | Construir frontend independiente por flujo | Vicente / Ignacio | K02, contrato del flujo en K03 | En revisión · acceso, catálogo y [flujos operativos conectados](flujos-operativos.md). |
| K05 | Comprobar esquema, índices y consultas | Ignacio / Vicente | K02 | En revisión · [esquema e índices comprobados](esquema/revision-postgresql.md). |
| K06 | Cerrar seguridad, estáticos y respaldo/restauración | Ignacio / Vicente | K02, K03 | Pendiente · controles comprobados y restauración documentada. |
| K07 | Ejecutar protocolo de pruebas y clasificar diferencias | Vicente + Ignacio | K03–K06 | Pendiente · casos observados, correcciones y recomendaciones. |
| K08 | Cerrar documentos y ensayar presentación | Vicente / Ignacio | K07 | Pendiente · informe final y evidencia de demostración. |
| K09 | Preparar y desplegar en AWS para el cliente | Ignacio + Vicente | K08 y entorno AWS acordado | Etapa posterior · configuración y verificación del despliegue. |

## Registro de contribuciones

Por cada aporte añadir fecha efectiva, integrante, ID de tarea, cambio realizado, archivo o evidencia y quién revisó. Actualizar el tablero cuando exista un resultado comprobable.
