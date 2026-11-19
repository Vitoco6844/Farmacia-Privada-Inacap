# Matriz de alcance y aceptación

Las historias corresponden al informe técnico de Aqueveque y Durán. Los nombres de módulos indican dónde está la base reutilizable. Cada fila define una prueba de aceptación pendiente para la interfaz independiente con API y PostgreSQL. Las pruebas heredadas son referencias de código y deberán ejecutarse en el entorno correspondiente.

| HU | Pantalla y rol | Regla y caso esperado | Base reutilizable y brecha |
|---|---|---|---|
| HU01 | Usuarios y permisos · Administrador | Crear cuenta con rol y desactivarla. El acceso se bloquea y el historial permanece. Administrador sin rol QF no puede aprobar recetas. | `gestion` tiene formularios y pruebas de roles. Falta integrar por API. |
| HU02 | Ingreso y recuperación · Trabajador | Ingresar con cuenta activa, salir, comprobar vencimiento de sesión y solicitar recuperación sin revelar si existe la cuenta. | `seguridad` tiene login, bloqueo e inactividad. Falta probar el flujo separado y el correo del entorno. |
| HU03 | Productos y categorías · Administrador/QF | Buscar por nombre o código, rechazar duplicados y restringir el cambio de condición al perfil profesional. | `catalogo` y `gestion` contienen formularios y pruebas. Falta integrar. |
| HU04 | Precios · Administrador | Programar precio y comprobar antes y durante vigencia. Aplicar tope configurado y conservar el precio histórico. | `gestion` prueba fechas y límites. Falta integrar. |
| HU05 | Inventario · Técnico/QF | Registrar un ingreso con lote y vencimiento y trasladar entre ubicaciones. Conservar total y registrar movimientos. | `operaciones` tiene servicios y pruebas. Falta integrar. |
| HU06 | Inventario y venta · Técnico, vendedor/QF según acción | Consultar lotes y vender un producto con dos lotes aptos. Consumir primero el de vencimiento cercano y excluir bloqueados y vencidos. | `operaciones` y `comercio` contemplan FEFO. Falta comprobar el circuito integrado. |
| HU07 | Alertas · Administrador/QF | Configurar umbral por ubicación. Probar el stock bajo y un lote que vence hoy o dentro del horizonte. | `gestion` y `operaciones` tienen alertas. Revisar consistencia de la fecha límite con ventas. |
| HU08 | Punto de venta · Vendedor | Cobrar varios productos en caja abierta. Repetir confirmación y comprobar una sola venta y un solo descuento de stock. | `comercio` tiene pruebas de atomicidad e idempotencia. Falta integración y concurrencia en PostgreSQL. |
| HU09 | Caja · Vendedor | Abrir, registrar movimiento y cerrar. Separar medios de pago y exigir motivo si el efectivo difiere. | `comercio` tiene flujos y pruebas. Falta integrar. |
| HU10 | Recetas · Técnico/QF | Registrar receta, aprobarla con QF y rechazar dispensación si está pendiente, rechazada o vencida. | `clinica` y `comercio` tienen validaciones. Falta integrar. |
| HU11 | Detalle de receta · Técnico/QF | Entregar una parte, verificar saldo por producto y bloquear exceso. Distinguir saldo agotado de receta sin límite cuando aplique. | `clinica` tiene pruebas para ambos estados. Falta confirmar regla y recorrido por API. |
| HU12 | Retiro · Personal habilitado | Registrar tercero y relación. Sin autorización requerida, rechazar la entrega y mantener saldo y stock. | `clinica` exige referencia. Falta acordar cómo se verifica esa autorización en la demo. |
| HU13 | Libro de controlados · QF | Autorizar cantidad, impedir reutilización y registrar corrección que conserve el asiento original. Revisar el caso de descuadre. | `clinica` tiene autorización y compensación. Falta comprobar alerta de descuadre y datos del libro contra el informe. |
| HU14 | Documento académico · Vendedor | Emitir boleta/factura simulada. Ante fallo, reintentar manteniendo el mismo documento y sin duplicar venta. | `comercio` tiene simulación y pruebas. Falta acordar cómo demostrar respuesta incierta si es exigida. |
| HU15 | Convenios y venta · Administrador/Vendedor | Mostrar descuento, aporte y copago. Rechazar convenio vencido y distinguir una respuesta incierta si entra en la simulación. | `comercio` prueba topes y descuentos. Revisar estados del informe. |
| HU16 | Indicadores · Administrador | Conciliar totales con filtros y estados. Comprobar la hora de actualización y que un error se indique como tal. | `operaciones` tiene panel y filtros. Falta verificar fórmulas, anulaciones y objetivo de actualización. |
| HU17 | Reportes · Usuario autorizado | Descargar PDF y Excel de ventas, inventario y compras. Verificar filtros, fecha, totales y acceso por rol. | `operaciones` tiene exportaciones y pruebas. Falta validar privacidad y totales en el flujo independiente. |
| HU18 | Orden imprimible · Usuario autorizado | Reimprimir una orden de entrega con el mismo folio y detalle. Confirmar que no cambia stock, venta ni saldo. | `clinica` tiene vista imprimible y prueba de datos históricos. Falta trasladar el flujo a la nueva interfaz. |
| HU19 | Auditoría · Administrador autorizado | Filtrar un cambio y comprobar actor, fecha y referencia. Una cuenta operativa no puede editarlo. | `gestion` tiene auditoría de consulta. Falta revisar cobertura de eventos críticos e integrar. |
| HU20 | Adjuntos de receta · Técnico/QF | Validar tamaño y formato. Un adjunto rechazado o pendiente no está disponible para consulta normal. La aceptación del archivo no aprueba la receta. | `clinica` tiene almacenamiento privado y revisión. Falta verificar restricción por estado y precisar el flujo de cuarentena. |

**Compras como flujo transversal.** Vincular a HU05, HU06 y HU17. Crear una orden, recibir solo parte de la cantidad, comprobar lotes, stock y saldo pendiente, y verificar que un reenvío no duplique existencias. La base está en `compras` y sus pruebas.

Para cada caso registrar entorno, datos ficticios, esperado, observado, resultado y enlace a evidencia. Referencia del recorrido anterior en [checklist de demostración](referencia/checklist-demostracion.md).
