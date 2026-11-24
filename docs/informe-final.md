# Informe final · Farmacia Privada INACAP

**Integrantes** · Ignacio Aqueveque y Vicente Durán  
**Período de trabajo** · 6 al 23 de noviembre de 2026  
**Entorno de entrega** · Aplicación web de uso interno, ejecutada localmente con datos ficticios.

## 1. Contexto y objetivo

El proyecto reúne en una aplicación las operaciones de abastecimiento, inventario, venta y dispensación de una farmacia. Su objetivo es mantener la trazabilidad del producto desde que llega del proveedor hasta que se vende o se dispensa, con permisos diferenciados para el personal y registros consultables en cada etapa.

## 2. Alcance funcional

| Área | Funciones implementadas |
|---|---|
| Catálogo y precios | Búsqueda por nombre o código, filtros, categorías, condición de venta, precios vigentes y límites de descuento. |
| Compras e inventario | Proveedores, órdenes, recepciones parciales, existencias por lote y ubicación, traslados, historial de movimientos y alertas. La recepción actualiza lo recibido y conserva el saldo pendiente de la orden. |
| Caja y ventas | Apertura, movimientos y cierre de caja. Búsqueda y cobro en punto de venta, convenios y comprobantes académicos con reintento de emisión. |
| Dispensación | Registro y revisión de recetas, entregas parciales, orden imprimible con folio y autorización de un solo uso para productos controlados. |
| Gestión y seguimiento | Usuarios y roles, auditoría, panel del turno y exportación de reportes a PDF y Excel. La interfaz incluye modo nocturno con preferencia guardada en el navegador. |

## 3. Arquitectura y decisiones técnicas

| Componente | Implementación y propósito |
|---|---|
| Frontend | HTML, CSS y JavaScript. Consume la API y presenta los formularios, filtros y resultados. Node.js sirve la interfaz y conecta las solicitudes con Django durante la demostración local. |
| Backend | Python 3.12 y Django 5.2. La API HTTP entrega datos en JSON y reutiliza los servicios que validan stock, recetas, permisos y montos. |
| Base de datos | PostgreSQL 17.11 en un servidor local. El esquema se reproduce mediante migraciones. Emplea claves primarias y foráneas, restricciones e índices para conservar relaciones válidas y facilitar las consultas. |
| Integridad de las operaciones | La venta y la recepción usan transacciones para revertir cambios parciales, bloqueos de filas para coordinar escrituras simultáneas y claves de idempotencia para reconocer reenvíos. |
| Acceso y validación | Django comprueba permisos del lado del servidor, protege las solicitudes con sesión mediante CSRF y valida el RUT chileno en los formularios correspondientes. Los adjuntos clínicos se consultan mediante rutas autorizadas según su estado. |

En el punto de venta, el backend calcula el importe definitivo con los precios vigentes. Para descontar existencias usa FEFO, consumiendo primero el lote apto de Vitrina con vencimiento más próximo. Los detalles de venta guardan el precio aplicado y vinculan los movimientos de stock con la operación.

## 4. Metodología y validación

Se organizó el trabajo mediante Kanban. Se prepararon PostgreSQL y los contratos de acceso y catálogo antes de conectar la interfaz. Los flujos operativos se integraron en el orden en que dependen de los datos. La recepción generó el stock necesario para validar traslados y ventas. La aprobación farmacéutica precedió a la entrega.

| Comprobación | Resultado registrado |
|---|---|
| Esquema en PostgreSQL | 50 tablas en total, incluidas 40 de los módulos del proyecto y 63 claves foráneas en esos módulos. |
| Regresión registrada | 177 pruebas aprobadas en la ejecución documentada en PostgreSQL. |
| Compra, traslado y venta | Se recibieron 4 de 10 unidades, se trasladaron 2 a Vitrina, se vendió 1 y el cierre de caja coincidió con el efectivo esperado. |
| Receta y comprobante | Se bloqueó la entrega con revisión pendiente. Tras aprobar la receta, se registraron 2 de 3 unidades. El reintento del comprobante conservó el saldo de inventario. |
| Reportes | El recorrido automatizado en navegador comprobó la descarga de inventario en PDF y Excel. |

## 5. Conclusión y trabajo pendiente

La entrega permite demostrar el recorrido desde la orden de compra hasta la venta, comprobar el saldo por ubicación y consultar la trazabilidad de operaciones. Los comprobantes y convenios son de uso académico. El despliegue en AWS, la comprobación de restauración de respaldos y la revisión de los avisos de SonarQube quedan para una etapa posterior.

**Evidencias** · [Kanban](kanban.md) · [Recorrido en navegador](validacion-navegador.md) · [Registro de pruebas](regresion-postgresql-verificada.txt) · [Esquema de PostgreSQL](esquema/revision-postgresql.md) · [Checklist de demostración](checklist-demostracion-profesor.md).
