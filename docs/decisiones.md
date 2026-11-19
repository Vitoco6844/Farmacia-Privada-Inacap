# Decisiones y preguntas del alcance

| Tema | Decisión o supuesto | Resolución y prueba |
|---|---|---|
| Arquitectura | Frontend web independiente en `frontend/` y backend Django en `backend/`. Reutilizar servicios, modelos y migraciones. El frontend consumirá una API. | Definir contrato por flujo, autenticación, permisos y formato de errores antes de conectarlo. Seleccionar herramienta de frontend al implementar el primer flujo. |
| Base de datos | PostgreSQL local desde el arranque de la nueva entrega, con una base de pruebas separada. | Paso 2. Migrar desde cero y validar consultas y escrituras con datos ficticios. |
| Anulaciones | Acordar qué operaciones permiten corrección y cómo se reflejan en stock, caja, documentos e indicadores. | Revisar con el docente/cliente académico y probar el efecto de cada operación permitida. |
| Recetas | Distinguir saldo agotado de ausencia de límite. El retiro por terceros requiere definir qué respaldo se acepta. | Confirmar tipos y respaldo esperado. Probar exceso, retiro sin respaldo y retiro autorizado. |
| Convenios y documentos | Integraciones simuladas para el caso académico. | Confirmar estados requeridos, incluida respuesta incierta. Probar vigencia, tope y reintento. |
| Adjuntos | Acceso privado y revisión de estados según la matriz. | Acordar cómo el QF revisa un archivo en cuarentena y cuándo se permite la consulta general. |
| AWS y S3 | Desarrollo y validación local primero. Despliegue AWS posterior para la presentación al cliente. S3 previsto para estáticos, imágenes y respaldos, con accesos separados para material privado. | Confirmar entorno, servicios, presupuesto y acceso antes del despliegue. Comprobar carga de archivos, acceso autorizado y restauración antes de la entrega en AWS. |

La documentación de referencia describe la versión anterior. La matriz y el tablero describen la nueva entrega.
