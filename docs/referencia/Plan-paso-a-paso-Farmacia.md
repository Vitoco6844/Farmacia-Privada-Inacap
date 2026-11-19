# Plan paso a paso del sistema de farmacia

**Fecha:** 19 de noviembre de 2026  
**Equipo:** Ignacio Aqueveque y Vicente Durán  
**Objetivo:** preparar una demostración académica integrada, repetible y respaldada por pruebas, usando la versión Farmacia-PI-Ampliada como base.

## Qué se debe entregar

Sí, se necesitan interfaz, backend y base de datos. Ya hay una aplicación Django con los tres componentes: plantillas HTML/CSS/JS, lógica de negocio y modelos relacionales. PostgreSQL es el motor elegido. La demostración previa usa SQLite, así que queda ejecutar y documentar la versión ampliada en PostgreSQL. El backend también necesita un entorno de ejecución.

La foto anota **S3 para estáticos, imágenes, respaldos, CSS y fuentes**. S3 almacena archivos. En esta arquitectura Django ejecuta la lógica y PostgreSQL guarda los datos de negocio. El plan incluye preparar y comprobar el manejo de archivos y la recuperación en local. La foto sola no confirma que la evaluación exija un bucket real o un servidor remoto. Esa exigencia se debe confirmar con el docente antes de la entrega. [Documentación de Amazon S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/).

El informe describe una farmacia académica con datos ficticios. Mantener boletas, facturas y convenios como simulaciones. La presentación puede recorrer procesos completos del caso académico. El uso con pacientes reales y las integraciones externas requieren una etapa posterior con alcance propio.

## Punto de partida

La versión ampliada incluye acceso y roles, productos, inventario, compras, caja, punto de venta, convenios, documentos académicos, recetas, controlados, entregas, indicadores, reportes y auditoría. Es el inventario inicial de módulos, no una declaración de aceptación. En octubre se registraron 172 casos en SQLite, con 166 aprobados y 6 omitidos por requerir PostgreSQL. Esa evidencia es de una versión y un entorno anteriores a este plan.

Fuentes del plan: instrucciones y rúbrica de `coso.md`, informe técnico original de Aqueveque y Durán, foto de la pizarra y documentación/código de `Farmacia-PI-Ampliada`. El cuerpo del informe enumera HU01–HU20. Usar esa numeración en la matriz aunque el resumen agrupe el alcance en seis bloques.

## Orden de trabajo

### 1. Preparar la copia de trabajo y fijar el alcance

- [ ] Copiar el código reutilizable de Farmacia-PI-Ampliada a `Nueva carpeta\Farmacia`, con dependencias declaradas, migraciones, plantillas y documentación pertinente. Excluir credenciales, bases locales, adjuntos existentes y entornos virtuales.
- [ ] Armar `docs/matriz-alcance.md` con una fila por HU01–HU20: pantalla, rol, regla, caso de prueba, estado y evidencia. Registrar Compras como flujo ya existente y vincularlo a los requisitos aplicables.
- [ ] Enumerar y resolver los supuestos relevantes: reglas de anulación y retiro por terceros, diferencia entre receta sin límite y saldo agotado, convenios ante respuesta incierta y alcance de S3 y alojamiento.
- [ ] Organizar un tablero Kanban. Por cada tarea, anotar responsable, revisor, cambio y evidencia. Propuesta: Vicente lidera interfaz y demostración e Ignacio entorno y datos, con revisión cruzada y aportes reales de ambos.

**Salida:** copia local separada, alcance trazable y lista priorizada de brechas.

### 2. Levantar el entorno con PostgreSQL local

- [ ] Documentar instalación, entorno virtual, dependencias, creación de base y usuario de aplicación, variables de entorno y comandos de arranque. Usar `.env.example` como plantilla y guardar valores locales en `.env` fuera de los archivos compartidos.
- [ ] Ejecutar las migraciones en una base vacía de PostgreSQL, configurar roles y cargar datos ficticios repetibles. Preparar una base separada para pruebas.
- [ ] Verificar acceso, conexión Django–PostgreSQL y los flujos mínimos de consulta y escritura. Repetir la preparación desde una carpeta limpia.

**Salida:** `README.md` reproducible y evidencia de un arranque real con PostgreSQL.

### 3. Comprobar el esquema y su rendimiento

- [ ] Revisar claves, relaciones, restricciones, obligatoriedad y unicidad. Priorizar producto–lote–existencia, orden–recepción, caja–venta–pago y receta–entrega.
- [ ] Revisar normalización y justificar los valores históricos que se congelan, como el precio aplicado. Actualizar diagrama y diccionario según las migraciones ejecutadas.
- [ ] Medir consultas de búsqueda, filtros, indicadores y reportes con datos sintéticos. Revisar planes antes de añadir índices. Registrar la comparación si se optimiza una consulta.

**Salida:** esquema comprobado en PostgreSQL, diccionario, diagrama y evidencia de las decisiones de optimización.

### 4. Completar y validar los flujos de negocio

Trabajar por flujo vertical. Para cada uno revisar primero la matriz, corregir la brecha mínima en interfaz y backend, ejecutar su caso de aceptación y guardar evidencia antes de pasar al siguiente.

| Orden | Flujo | Demostración mínima |
|---|---|---|
| 4.1 | Acceso y usuarios (HU01–02) | Iniciar sesión, aplicar roles, bloquear cuentas inactivas y comprobar recuperación. |
| 4.2 | Catálogo, precios e inventario (HU03–07) | Buscar por nombre/código, comprobar precio vigente, recibir una compra parcial, revisar lotes, trasladar existencias y mostrar alertas. |
| 4.3 | Caja, ventas, documentos y convenios (HU08–09, HU14–15) | Abrir caja, vender, verificar salida por FEFO, mostrar copago y reintento sin duplicación, cerrar con diferencias justificadas. Revisar vigencia y estados de convenio exigidos por el informe. |
| 4.4 | Recetas, controlados y adjuntos (HU10–13, HU20) | Registrar y revisar, entregar parcialmente, bloquear saldo agotado, validar retiro por tercero y autorización QF de un solo uso. Comprobar descuadres y compensación de asientos según el alcance validado. |
| 4.5 | Indicadores, reportes, órdenes y auditoría (HU16–19) | Contrastar totales, filtros, estados y exportaciones. Reimprimir con el mismo folio. Verificar trazabilidad y que un error de consulta no se muestre como stock cero. |

- [ ] Revisar etiquetas, búsquedas, mensajes, navegación por teclado y pantallas en móvil y escritorio. Usar la guía de botones y la checklist existentes. Guardar evidencia de las correcciones que se hagan.
- [ ] Comprobar que alta, modificación y consulta aplican los permisos y validaciones del servidor. Usar los roles reales del sistema y los escenarios de la matriz.

**Salida:** flujos demostrables y brechas cerradas o identificadas con su siguiente acción.

### 5. Cerrar seguridad, archivos y recuperación

- [ ] Revisar autenticación, sesiones, CSRF, permisos por rol, protección de secretos, manejo de datos sensibles, auditoría y transacciones. Verificar con pruebas defensivas que las operaciones reservadas sean rechazadas para roles sin permiso. Documentar HTTPS, cifrado y el estado del segundo factor contemplado en el informe.
- [ ] Verificar el circuito de adjuntos en `clinica/views.py` y `clinica/services.py`. El informe exige impedir consultas a archivos pendientes o rechazados. La vista de descarga existente verifica el permiso, pero en esta revisión no se observó un filtro de estado. Probar esa regla y definir cómo revisará el QF un archivo en cuarentena mediante un flujo controlado.
- [ ] Preparar estáticos locales con `collectstatic` y verificar CSS, fuentes e imágenes en el entorno de demostración. Mantener adjuntos y respaldos privados. Documentar los destinos y políticas que se usarían en S3, con permisos por función y retención definida.
- [ ] Crear un respaldo local de PostgreSQL y de los archivos privados de prueba. Restaurar ambos en un entorno aislado y verificar relaciones y lectura autorizada de un adjunto restaurado. Registrar duración y antigüedad de la copia. El informe propone respaldo diario, pérdida máxima de 24 horas y recuperación en hasta cuatro horas.

**Salida:** registro de verificaciones de seguridad, esquema de almacenamiento y evidencia de restauración. Las copias privadas se planifican con bloqueo de acceso público. [Guía de AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html).

### 6. Ejecutar el protocolo y analizar resultados

- [ ] Preparar `docs/plan-pruebas.md` antes de ejecutar. Por caso registrar ID/HU, entorno, datos, pasos, resultado esperado, resultado observado, estado y archivo de evidencia. Cubrir casos normales, bordes, errores, roles, concurrencia, estrés y restauración.
- [ ] Ejecutar pruebas unitarias e integración en entornos aislados. Probar las seis de concurrencia omitidas anteriormente en SQLite y añadir escenarios del POS ampliado si la matriz revela vacíos.
- [ ] Ejecutar pruebas manuales por rol y medir rendimiento. Usar como referencia del informe su escenario de 20 usuarios concurrentes y 10.000 productos. Acordar criterios medibles antes de correr la carga y guardar tiempos, errores, datos y condiciones del ensayo. La disponibilidad mensual se evalúa aparte.
- [ ] Comparar esperado y observado por caso. Para cada diferencia registrar impacto, causa confirmada o hipótesis, acción recomendada y nueva prueba después de corregir. Marcar bloqueadas y omitidas con su motivo.

**Salida:** matriz y resultados con archivos seleccionados, análisis de diferencias y recomendaciones priorizadas.

### 7. Preparar el informe final y ensayar la presentación

- [ ] Confirmar la plantilla final del docente. Completar portada, alcance, requisitos, diseño, arquitectura, base de datos, implementación, trabajo del equipo, entorno, protocolo, resultados, discrepancias, recomendaciones, conclusiones y anexos según el formato solicitado. Mantener los resultados observados separados de metas y propuestas.
- [ ] Ensayar con datos ficticios desde una instalación limpia. Mostrar acceso por rol, flujo compra–stock–venta–caja, flujo receta–entrega, esquema de PostgreSQL, evidencia de pruebas y restauración. Repartir la explicación entre los dos integrantes.
- [ ] Revisar que cada requisito y criterio tenga evidencia local enlazada. Registrar qué demostrará el equipo y qué limitaciones se explicarán al presentar.

**Salida:** aplicación local demostrable, informe final en el formato solicitado y evidencias pertinentes.

## Correspondencia con la rúbrica

| Criterio | Paso y evidencia |
|---|---|
| Coherencia entre interfaz y negocio | 1 y 4 · matriz HU y aceptación por flujo. |
| Lineamientos estéticos y funcionales | 4 · comprobación por rol y tamaño de pantalla. |
| Estructura de base de datos | 2 y 3 · migraciones, esquema y restricciones. |
| Optimización y normalización | 3 · decisiones del modelo, consultas y mediciones. |
| Patrones de seguridad | 5 y 6 · controles y resultados defensivos. |
| Colaboración en equipo | 1 y 7 · tablero, revisiones y aportes verificables. |
| Entorno de trabajo | 2 · instalación repetida y arranque con PostgreSQL. |
| Documentación de implementación | 2 a 5 y 7 · README, diseño, manual y recuperación. |
| Cobertura del plan de pruebas | 6 · cruce de HU, bordes y escenarios de estrés. |
| Ejecución del protocolo | 6 · resultados por caso y evidencia. |
| Validación de resultados | 6 · análisis, repetición y revisión. |
| Comparación de esperado y observado | 6 · matriz de resultados y discrepancias. |
| Recomendaciones | 6 y 7 · acciones ligadas a hallazgos e impacto. |
| Informe final | 7 · revisión contra la plantilla oficial. |

El primer paso de implementación será preparar la copia local y la matriz de alcance. Los pasos de este documento describen trabajo por realizar.
