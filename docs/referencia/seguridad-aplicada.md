# Seguridad aplicada y límites actuales

Versión ampliada local, 20 de octubre de 2026. Descripción de controles implementados; no constituye una auditoría completa.

| Riesgo | Control presente | Límite o comprobación pendiente |
|---|---|---|
| Acceso indebido | Autenticación Django, contraseñas validadas, límites de intentos y cierre por inactividad. | Validar el entorno de despliegue y sus secretos. |
| Exceso de privilegios | Grupos/permisos y comprobaciones en vistas y servicios. | Revisión integral pendiente; el administrador no sustituye al rol farmacéutico. |
| Solicitudes o contenido malicioso | CSRF, autoescape, formularios y ORM. | No equivale a análisis completo de todas las entradas. |
| Adjuntos clínicos | Almacenamiento privado, descarga restringida, validación de PDF/JPG/PNG, límite de tamaño y estado de revisión. | No hay antivirus acreditado. La revisión del archivo no sustituye la revisión de la receta. |
| Duplicación o cambios parciales | Transacciones y claves de idempotencia en operaciones comerciales. | Las seis pruebas de concurrencia PostgreSQL siguen pendientes. |
| Alteración de históricos | Registros de eventos y datos históricos de ventas/entregas. | No se acredita almacenamiento externo inmutable de auditoría. |
| Pérdida de información | Persistencia local relacional y archivos privados. | Restauración de respaldos no acreditada. |

## Roles configurados

| Rol | Funciones principales |
|---|---|
| Administrador | Catálogo, inventario, compras, caja/ventas, convenios, usuarios, precios, alertas, auditoría y exportaciones. |
| Vendedor | Consulta de catálogo/existencias, caja/ventas/documentos y gestión clínica básica. |
| Técnico en Farmacia | Consulta de catálogo, inventario, recepción de compras y gestión clínica básica. |
| Químico Farmacéutico | Inventario/recepción, gestión clínica, revisión de recetas, autorización de controlados, adjuntos, libro, condiciones y alertas. |

La gestión clínica básica es común a los cuatro roles. La aprobación y autorización farmacéutica están separadas. Un usuario puede pertenecer a más de un grupo; la tabla resume la configuración y no reemplaza los permisos exactos de configurar_roles.py. No se debe usar una cuenta superusuario para demostrar las restricciones de un rol.

## Entorno y datos

La demo usa SQLite, HTTP de loopback y correo a archivos locales. No se acredita SMTP externo ni HTTPS de producción. Usar datos ficticios; excluir .env, entornos virtuales, bases locales, correos y adjuntos de una publicación. JSONField y archivos privados no constituyen por sí solos una base NoSQL independiente.

Antes de otro despliegue: revisar configuración de secretos, transporte, permisos de archivos, respaldos y resultados contra el motor elegido. Estas tareas no fueron ejecutadas en esta actualización.
