# Diccionario del esquema PostgreSQL

Tipos y restricciones consultados en la base migrada. Incluye los módulos del proyecto.

## catalogo_categoria

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `nombre` | `character varying(80)` | No |

- `catalogo_categoria_nombre_key`: `UNIQUE (nombre)`
- `catalogo_categoria_pkey`: `PRIMARY KEY (id)`
- Índice `catalogo_categoria_nombre_42478c50_like`: `CREATE INDEX catalogo_categoria_nombre_42478c50_like ON public.catalogo_categoria USING btree (nombre varchar_pattern_ops)`
- Índice `catalogo_categoria_nombre_key`: `CREATE UNIQUE INDEX catalogo_categoria_nombre_key ON public.catalogo_categoria USING btree (nombre)`
- Índice `catalogo_categoria_pkey`: `CREATE UNIQUE INDEX catalogo_categoria_pkey ON public.catalogo_categoria USING btree (id)`

## catalogo_eventocatalogo

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `accion` | `character varying(20)` | No |
| `fecha` | `timestamp with time zone` | No |
| `anterior` | `jsonb` | No |
| `posterior` | `jsonb` | No |
| `usuario_id` | `integer` | No |
| `producto_id` | `bigint` | No |

- `catalogo_eventocatal_producto_id_881e8ee8_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `catalogo_eventocatalogo_pkey`: `PRIMARY KEY (id)`
- `catalogo_eventocatalogo_usuario_id_95177e9f_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `catalogo_eventocatalogo_pkey`: `CREATE UNIQUE INDEX catalogo_eventocatalogo_pkey ON public.catalogo_eventocatalogo USING btree (id)`
- Índice `catalogo_eventocatalogo_producto_id_881e8ee8`: `CREATE INDEX catalogo_eventocatalogo_producto_id_881e8ee8 ON public.catalogo_eventocatalogo USING btree (producto_id)`
- Índice `catalogo_eventocatalogo_usuario_id_95177e9f`: `CREATE INDEX catalogo_eventocatalogo_usuario_id_95177e9f ON public.catalogo_eventocatalogo USING btree (usuario_id)`

## catalogo_precioreferencia

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `precio` | `numeric(12,0)` | No |
| `farmacia` | `character varying(80)` | No |
| `tipo` | `character varying(80)` | No |
| `fuente` | `character varying(500)` | No |
| `consultado` | `date` | No |
| `nota` | `character varying(300)` | No |
| `producto_id` | `bigint` | No |

- `catalogo_preciorefer_producto_id_cd138f13_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `catalogo_precioreferencia_pkey`: `PRIMARY KEY (id)`
- `referencia_precio_no_negativo`: `CHECK ((precio >= (0)::numeric))`
- `referencia_producto_fuente_fecha`: `UNIQUE (producto_id, fuente, consultado)`
- Índice `catalogo_precioreferencia_pkey`: `CREATE UNIQUE INDEX catalogo_precioreferencia_pkey ON public.catalogo_precioreferencia USING btree (id)`
- Índice `catalogo_precioreferencia_producto_id_cd138f13`: `CREATE INDEX catalogo_precioreferencia_producto_id_cd138f13 ON public.catalogo_precioreferencia USING btree (producto_id)`
- Índice `referencia_producto_fuente_fecha`: `CREATE UNIQUE INDEX referencia_producto_fuente_fecha ON public.catalogo_precioreferencia USING btree (producto_id, fuente, consultado)`

## catalogo_producto

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `codigo` | `character varying(30)` | No |
| `barras` | `character varying(14)` | No |
| `nombre` | `character varying(160)` | No |
| `presentacion` | `character varying(180)` | No |
| `condicion` | `character varying(30)` | No |
| `precio` | `numeric(12,0)` | No |
| `activo` | `boolean` | No |
| `creado` | `timestamp with time zone` | No |
| `actualizado` | `timestamp with time zone` | No |
| `categoria_id` | `bigint` | No |
| `stock_minimo` | `integer` | No |

- `catalogo_producto_barras_key`: `UNIQUE (barras)`
- `catalogo_producto_categoria_id_19eecf17_fk_catalogo_`: `FOREIGN KEY (categoria_id) REFERENCES catalogo_categoria(id) DEFERRABLE INITIALLY DEFERRED`
- `catalogo_producto_codigo_key`: `UNIQUE (codigo)`
- `catalogo_producto_pkey`: `PRIMARY KEY (id)`
- `catalogo_producto_stock_minimo_check`: `CHECK ((stock_minimo >= 0))`
- `producto_condicion_valida`: `CHECK (((condicion)::text = ANY ((ARRAY['Venta directa'::character varying, 'Receta simple'::character varying, 'Receta retenida'::character varying, 'Por verificar'::character varying])::text[])))`
- `producto_precio_no_negativo`: `CHECK ((precio >= (0)::numeric))`
- Índice `catalogo_producto_barras_b04ea20d_like`: `CREATE INDEX catalogo_producto_barras_b04ea20d_like ON public.catalogo_producto USING btree (barras varchar_pattern_ops)`
- Índice `catalogo_producto_barras_key`: `CREATE UNIQUE INDEX catalogo_producto_barras_key ON public.catalogo_producto USING btree (barras)`
- Índice `catalogo_producto_categoria_id_19eecf17`: `CREATE INDEX catalogo_producto_categoria_id_19eecf17 ON public.catalogo_producto USING btree (categoria_id)`
- Índice `catalogo_producto_codigo_2e653f9d_like`: `CREATE INDEX catalogo_producto_codigo_2e653f9d_like ON public.catalogo_producto USING btree (codigo varchar_pattern_ops)`
- Índice `catalogo_producto_codigo_key`: `CREATE UNIQUE INDEX catalogo_producto_codigo_key ON public.catalogo_producto USING btree (codigo)`
- Índice `catalogo_producto_pkey`: `CREATE UNIQUE INDEX catalogo_producto_pkey ON public.catalogo_producto USING btree (id)`

## clinica_adjuntoreceta

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `archivo` | `character varying(100)` | No |
| `nombre` | `character varying(200)` | No |
| `tipo` | `character varying(40)` | No |
| `sha256` | `character varying(64)` | No |
| `estado` | `character varying(15)` | No |
| `fecha` | `timestamp with time zone` | No |
| `revisado_por_id` | `integer` | Sí |
| `usuario_id` | `integer` | No |
| `receta_id` | `bigint` | No |

- `clinica_adjuntoreceta_pkey`: `PRIMARY KEY (id)`
- `clinica_adjuntoreceta_receta_id_2ac0ede2_fk_clinica_receta_id`: `FOREIGN KEY (receta_id) REFERENCES clinica_receta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_adjuntoreceta_revisado_por_id_ca0314c9_fk_auth_user_id`: `FOREIGN KEY (revisado_por_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_adjuntoreceta_usuario_id_e448ba4e_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `clinica_adjuntoreceta_pkey`: `CREATE UNIQUE INDEX clinica_adjuntoreceta_pkey ON public.clinica_adjuntoreceta USING btree (id)`
- Índice `clinica_adjuntoreceta_receta_id_2ac0ede2`: `CREATE INDEX clinica_adjuntoreceta_receta_id_2ac0ede2 ON public.clinica_adjuntoreceta USING btree (receta_id)`
- Índice `clinica_adjuntoreceta_revisado_por_id_ca0314c9`: `CREATE INDEX clinica_adjuntoreceta_revisado_por_id_ca0314c9 ON public.clinica_adjuntoreceta USING btree (revisado_por_id)`
- Índice `clinica_adjuntoreceta_usuario_id_e448ba4e`: `CREATE INDEX clinica_adjuntoreceta_usuario_id_e448ba4e ON public.clinica_adjuntoreceta USING btree (usuario_id)`

## clinica_asientocontrolado

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `cantidad` | `integer` | No |
| `fecha` | `timestamp with time zone` | No |
| `motivo` | `text` | No |
| `compensa_id` | `bigint` | Sí |
| `producto_id` | `bigint` | No |
| `profesional_id` | `integer` | No |
| `entrega_id` | `bigint` | No |

- `clinica_asientocontr_compensa_id_5e4547d6_fk_clinica_a`: `FOREIGN KEY (compensa_id) REFERENCES clinica_asientocontrolado(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_asientocontr_entrega_id_e3518f41_fk_clinica_e`: `FOREIGN KEY (entrega_id) REFERENCES clinica_entrega(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_asientocontr_producto_id_c89c1183_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_asientocontr_profesional_id_58984001_fk_auth_user`: `FOREIGN KEY (profesional_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_asientocontrolado_compensa_id_key`: `UNIQUE (compensa_id)`
- `clinica_asientocontrolado_pkey`: `PRIMARY KEY (id)`
- Índice `clinica_asientocontrolado_compensa_id_key`: `CREATE UNIQUE INDEX clinica_asientocontrolado_compensa_id_key ON public.clinica_asientocontrolado USING btree (compensa_id)`
- Índice `clinica_asientocontrolado_entrega_id_e3518f41`: `CREATE INDEX clinica_asientocontrolado_entrega_id_e3518f41 ON public.clinica_asientocontrolado USING btree (entrega_id)`
- Índice `clinica_asientocontrolado_pkey`: `CREATE UNIQUE INDEX clinica_asientocontrolado_pkey ON public.clinica_asientocontrolado USING btree (id)`
- Índice `clinica_asientocontrolado_producto_id_c89c1183`: `CREATE INDEX clinica_asientocontrolado_producto_id_c89c1183 ON public.clinica_asientocontrolado USING btree (producto_id)`
- Índice `clinica_asientocontrolado_profesional_id_58984001`: `CREATE INDEX clinica_asientocontrolado_profesional_id_58984001 ON public.clinica_asientocontrolado USING btree (profesional_id)`

## clinica_autorizacioncontrolado

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `cantidad` | `integer` | No |
| `fecha` | `timestamp with time zone` | No |
| `producto_id` | `bigint` | No |
| `profesional_id` | `integer` | No |
| `entrega_id` | `bigint` | Sí |
| `receta_id` | `bigint` | No |

- `clinica_autorizacion_entrega_id_d78aa56b_fk_clinica_e`: `FOREIGN KEY (entrega_id) REFERENCES clinica_entrega(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_autorizacion_producto_id_9be056e9_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_autorizacion_profesional_id_df0b9b6d_fk_auth_user`: `FOREIGN KEY (profesional_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_autorizacion_receta_id_554e078d_fk_clinica_r`: `FOREIGN KEY (receta_id) REFERENCES clinica_receta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_autorizacioncontrolado_cantidad_check`: `CHECK ((cantidad >= 0))`
- `clinica_autorizacioncontrolado_pkey`: `PRIMARY KEY (id)`
- Índice `clinica_autorizacioncontrolado_entrega_id_d78aa56b`: `CREATE INDEX clinica_autorizacioncontrolado_entrega_id_d78aa56b ON public.clinica_autorizacioncontrolado USING btree (entrega_id)`
- Índice `clinica_autorizacioncontrolado_pkey`: `CREATE UNIQUE INDEX clinica_autorizacioncontrolado_pkey ON public.clinica_autorizacioncontrolado USING btree (id)`
- Índice `clinica_autorizacioncontrolado_producto_id_9be056e9`: `CREATE INDEX clinica_autorizacioncontrolado_producto_id_9be056e9 ON public.clinica_autorizacioncontrolado USING btree (producto_id)`
- Índice `clinica_autorizacioncontrolado_profesional_id_df0b9b6d`: `CREATE INDEX clinica_autorizacioncontrolado_profesional_id_df0b9b6d ON public.clinica_autorizacioncontrolado USING btree (profesional_id)`
- Índice `clinica_autorizacioncontrolado_receta_id_554e078d`: `CREATE INDEX clinica_autorizacioncontrolado_receta_id_554e078d ON public.clinica_autorizacioncontrolado USING btree (receta_id)`

## clinica_detalleentrega

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `cantidad` | `integer` | No |
| `entrega_id` | `bigint` | No |
| `linea_receta_id` | `bigint` | No |

- `clinica_detalleentre_entrega_id_2f7d9a68_fk_clinica_e`: `FOREIGN KEY (entrega_id) REFERENCES clinica_entrega(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_detalleentre_linea_receta_id_f4f81586_fk_clinica_l`: `FOREIGN KEY (linea_receta_id) REFERENCES clinica_lineareceta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_detalleentrega_cantidad_check`: `CHECK ((cantidad >= 0))`
- `clinica_detalleentrega_pkey`: `PRIMARY KEY (id)`
- Índice `clinica_detalleentrega_entrega_id_2f7d9a68`: `CREATE INDEX clinica_detalleentrega_entrega_id_2f7d9a68 ON public.clinica_detalleentrega USING btree (entrega_id)`
- Índice `clinica_detalleentrega_linea_receta_id_f4f81586`: `CREATE INDEX clinica_detalleentrega_linea_receta_id_f4f81586 ON public.clinica_detalleentrega USING btree (linea_receta_id)`
- Índice `clinica_detalleentrega_pkey`: `CREATE UNIQUE INDEX clinica_detalleentrega_pkey ON public.clinica_detalleentrega USING btree (id)`

## clinica_entrega

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `folio` | `uuid` | No |
| `autorizacion_retiro` | `text` | No |
| `instantanea` | `jsonb` | No |
| `fecha` | `timestamp with time zone` | No |
| `usuario_id` | `integer` | No |
| `venta_id` | `bigint` | No |
| `retirante_id` | `bigint` | No |
| `receta_id` | `bigint` | No |

- `clinica_entrega_folio_key`: `UNIQUE (folio)`
- `clinica_entrega_pkey`: `PRIMARY KEY (id)`
- `clinica_entrega_receta_id_e9e6cb14_fk_clinica_receta_id`: `FOREIGN KEY (receta_id) REFERENCES clinica_receta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_entrega_retirante_id_42cd6a34_fk_clinica_paciente_id`: `FOREIGN KEY (retirante_id) REFERENCES clinica_paciente(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_entrega_usuario_id_12e50fdf_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_entrega_venta_id_72d5c96c_fk_operaciones_venta_id`: `FOREIGN KEY (venta_id) REFERENCES operaciones_venta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_entrega_venta_id_key`: `UNIQUE (venta_id)`
- Índice `clinica_entrega_folio_key`: `CREATE UNIQUE INDEX clinica_entrega_folio_key ON public.clinica_entrega USING btree (folio)`
- Índice `clinica_entrega_pkey`: `CREATE UNIQUE INDEX clinica_entrega_pkey ON public.clinica_entrega USING btree (id)`
- Índice `clinica_entrega_receta_id_e9e6cb14`: `CREATE INDEX clinica_entrega_receta_id_e9e6cb14 ON public.clinica_entrega USING btree (receta_id)`
- Índice `clinica_entrega_retirante_id_42cd6a34`: `CREATE INDEX clinica_entrega_retirante_id_42cd6a34 ON public.clinica_entrega USING btree (retirante_id)`
- Índice `clinica_entrega_usuario_id_12e50fdf`: `CREATE INDEX clinica_entrega_usuario_id_12e50fdf ON public.clinica_entrega USING btree (usuario_id)`
- Índice `clinica_entrega_venta_id_key`: `CREATE UNIQUE INDEX clinica_entrega_venta_id_key ON public.clinica_entrega USING btree (venta_id)`

## clinica_eventoclinico

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `accion` | `character varying(30)` | No |
| `detalle` | `jsonb` | No |
| `fecha` | `timestamp with time zone` | No |
| `usuario_id` | `integer` | No |
| `receta_id` | `bigint` | No |

- `clinica_eventoclinico_pkey`: `PRIMARY KEY (id)`
- `clinica_eventoclinico_receta_id_774ffbe7_fk_clinica_receta_id`: `FOREIGN KEY (receta_id) REFERENCES clinica_receta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_eventoclinico_usuario_id_65887737_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `clinica_eventoclinico_pkey`: `CREATE UNIQUE INDEX clinica_eventoclinico_pkey ON public.clinica_eventoclinico USING btree (id)`
- Índice `clinica_eventoclinico_receta_id_774ffbe7`: `CREATE INDEX clinica_eventoclinico_receta_id_774ffbe7 ON public.clinica_eventoclinico USING btree (receta_id)`
- Índice `clinica_eventoclinico_usuario_id_65887737`: `CREATE INDEX clinica_eventoclinico_usuario_id_65887737 ON public.clinica_eventoclinico USING btree (usuario_id)`

## clinica_lineareceta

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `sin_limite` | `boolean` | No |
| `cantidad` | `integer` | Sí |
| `entregada` | `integer` | No |
| `producto_id` | `bigint` | No |
| `receta_id` | `bigint` | No |

- `clinica_lineareceta_cantidad_check`: `CHECK ((cantidad >= 0))`
- `clinica_lineareceta_entregada_check`: `CHECK ((entregada >= 0))`
- `clinica_lineareceta_pkey`: `PRIMARY KEY (id)`
- `clinica_lineareceta_producto_id_c5006339_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_lineareceta_receta_id_6d78d4ee_fk_clinica_receta_id`: `FOREIGN KEY (receta_id) REFERENCES clinica_receta(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_receta_producto`: `UNIQUE (receta_id, producto_id)`
- `clinica_saldo_coherente`: `CHECK ((((cantidad IS NULL) AND sin_limite) OR ((cantidad > 0) AND (cantidad >= entregada) AND (cantidad IS NOT NULL) AND (NOT sin_limite))))`
- Índice `clinica_lineareceta_pkey`: `CREATE UNIQUE INDEX clinica_lineareceta_pkey ON public.clinica_lineareceta USING btree (id)`
- Índice `clinica_lineareceta_producto_id_c5006339`: `CREATE INDEX clinica_lineareceta_producto_id_c5006339 ON public.clinica_lineareceta USING btree (producto_id)`
- Índice `clinica_lineareceta_receta_id_6d78d4ee`: `CREATE INDEX clinica_lineareceta_receta_id_6d78d4ee ON public.clinica_lineareceta USING btree (receta_id)`
- Índice `clinica_receta_producto`: `CREATE UNIQUE INDEX clinica_receta_producto ON public.clinica_lineareceta USING btree (receta_id, producto_id)`

## clinica_paciente

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `identificador` | `character varying(40)` | No |
| `nombre` | `character varying(160)` | No |
| `telefono` | `character varying(40)` | No |
| `activo` | `boolean` | No |

- `clinica_paciente_identificador_key`: `UNIQUE (identificador)`
- `clinica_paciente_pkey`: `PRIMARY KEY (id)`
- Índice `clinica_paciente_identificador_3b84ba19_like`: `CREATE INDEX clinica_paciente_identificador_3b84ba19_like ON public.clinica_paciente USING btree (identificador varchar_pattern_ops)`
- Índice `clinica_paciente_identificador_key`: `CREATE UNIQUE INDEX clinica_paciente_identificador_key ON public.clinica_paciente USING btree (identificador)`
- Índice `clinica_paciente_pkey`: `CREATE UNIQUE INDEX clinica_paciente_pkey ON public.clinica_paciente USING btree (id)`

## clinica_prescriptor

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `identificador` | `character varying(40)` | No |
| `nombre` | `character varying(160)` | No |
| `registro` | `character varying(80)` | No |
| `activo` | `boolean` | No |

- `clinica_prescriptor_identificador_key`: `UNIQUE (identificador)`
- `clinica_prescriptor_pkey`: `PRIMARY KEY (id)`
- Índice `clinica_prescriptor_identificador_f4157ccf_like`: `CREATE INDEX clinica_prescriptor_identificador_f4157ccf_like ON public.clinica_prescriptor USING btree (identificador varchar_pattern_ops)`
- Índice `clinica_prescriptor_identificador_key`: `CREATE UNIQUE INDEX clinica_prescriptor_identificador_key ON public.clinica_prescriptor USING btree (identificador)`
- Índice `clinica_prescriptor_pkey`: `CREATE UNIQUE INDEX clinica_prescriptor_pkey ON public.clinica_prescriptor USING btree (id)`

## clinica_receta

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `emitida` | `date` | No |
| `vence` | `date` | No |
| `estado` | `character varying(15)` | No |
| `revisada_el` | `timestamp with time zone` | Sí |
| `nota_revision` | `text` | No |
| `creada` | `timestamp with time zone` | No |
| `paciente_id` | `bigint` | No |
| `prescriptor_id` | `bigint` | No |
| `revisada_por_id` | `integer` | Sí |

- `clinica_receta_paciente_id_b9b47c51_fk_clinica_paciente_id`: `FOREIGN KEY (paciente_id) REFERENCES clinica_paciente(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_receta_pkey`: `PRIMARY KEY (id)`
- `clinica_receta_prescriptor_id_e63f0513_fk_clinica_p`: `FOREIGN KEY (prescriptor_id) REFERENCES clinica_prescriptor(id) DEFERRABLE INITIALLY DEFERRED`
- `clinica_receta_revisada_por_id_0399ad05_fk_auth_user_id`: `FOREIGN KEY (revisada_por_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `clinica_receta_paciente_id_b9b47c51`: `CREATE INDEX clinica_receta_paciente_id_b9b47c51 ON public.clinica_receta USING btree (paciente_id)`
- Índice `clinica_receta_pkey`: `CREATE UNIQUE INDEX clinica_receta_pkey ON public.clinica_receta USING btree (id)`
- Índice `clinica_receta_prescriptor_id_e63f0513`: `CREATE INDEX clinica_receta_prescriptor_id_e63f0513 ON public.clinica_receta USING btree (prescriptor_id)`
- Índice `clinica_receta_revisada_por_id_0399ad05`: `CREATE INDEX clinica_receta_revisada_por_id_0399ad05 ON public.clinica_receta USING btree (revisada_por_id)`

## comercio_caja

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `apertura` | `timestamp with time zone` | No |
| `cierre` | `timestamp with time zone` | Sí |
| `fondo` | `numeric(14,0)` | No |
| `contado` | `numeric(14,0)` | Sí |
| `esperado_cierre` | `numeric(14,0)` | Sí |
| `motivo_diferencia` | `text` | No |
| `usuario_id` | `integer` | No |

- `caja_fondo_positivo`: `CHECK ((fondo >= (0)::numeric))`
- `comercio_caja_pkey`: `PRIMARY KEY (id)`
- `comercio_caja_usuario_id_d59d0b55_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `caja_abierta_por_usuario`: `CREATE UNIQUE INDEX caja_abierta_por_usuario ON public.comercio_caja USING btree (usuario_id) WHERE (cierre IS NULL)`
- Índice `comercio_caja_pkey`: `CREATE UNIQUE INDEX comercio_caja_pkey ON public.comercio_caja USING btree (id)`
- Índice `comercio_caja_usuario_id_d59d0b55`: `CREATE INDEX comercio_caja_usuario_id_d59d0b55 ON public.comercio_caja USING btree (usuario_id)`

## comercio_cobro

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `solicitud` | `jsonb` | No |
| `bruto` | `numeric(14,0)` | No |
| `descuento` | `numeric(14,0)` | No |
| `beneficio` | `numeric(14,0)` | No |
| `convenio_nombre` | `character varying(120)` | No |
| `medio` | `character varying(15)` | No |
| `caja_id` | `bigint` | No |
| `venta_id` | `bigint` | No |
| `convenio_id` | `bigint` | Sí |

- `comercio_cobro_caja_id_3c9b6602_fk_comercio_caja_id`: `FOREIGN KEY (caja_id) REFERENCES comercio_caja(id) DEFERRABLE INITIALLY DEFERRED`
- `comercio_cobro_convenio_id_0641fdad_fk_comercio_convenio_id`: `FOREIGN KEY (convenio_id) REFERENCES comercio_convenio(id) DEFERRABLE INITIALLY DEFERRED`
- `comercio_cobro_pkey`: `PRIMARY KEY (id)`
- `comercio_cobro_venta_id_c0f0cef3_fk_operaciones_venta_id`: `FOREIGN KEY (venta_id) REFERENCES operaciones_venta(id) DEFERRABLE INITIALLY DEFERRED`
- `comercio_cobro_venta_id_key`: `UNIQUE (venta_id)`
- Índice `comercio_cobro_caja_id_3c9b6602`: `CREATE INDEX comercio_cobro_caja_id_3c9b6602 ON public.comercio_cobro USING btree (caja_id)`
- Índice `comercio_cobro_convenio_id_0641fdad`: `CREATE INDEX comercio_cobro_convenio_id_0641fdad ON public.comercio_cobro USING btree (convenio_id)`
- Índice `comercio_cobro_pkey`: `CREATE UNIQUE INDEX comercio_cobro_pkey ON public.comercio_cobro USING btree (id)`
- Índice `comercio_cobro_venta_id_key`: `CREATE UNIQUE INDEX comercio_cobro_venta_id_key ON public.comercio_cobro USING btree (venta_id)`

## comercio_convenio

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `nombre` | `character varying(120)` | No |
| `inicio` | `date` | No |
| `fin` | `date` | No |
| `porcentaje` | `numeric(5,2)` | No |
| `tope` | `numeric(14,0)` | Sí |
| `activo` | `boolean` | No |

- `comercio_convenio_pkey`: `PRIMARY KEY (id)`
- `convenio_fechas_validas`: `CHECK ((fin >= inicio))`
- `convenio_porcentaje_valido`: `CHECK (((porcentaje >= (0)::numeric) AND (porcentaje <= (100)::numeric)))`
- Índice `comercio_convenio_pkey`: `CREATE UNIQUE INDEX comercio_convenio_pkey ON public.comercio_convenio USING btree (id)`

## comercio_documento

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `tipo` | `character varying(10)` | No |
| `receptor` | `character varying(160)` | No |
| `rut` | `character varying(20)` | No |
| `estado` | `character varying(10)` | No |
| `intentos` | `integer` | No |
| `emitido` | `timestamp with time zone` | Sí |
| `error` | `character varying(250)` | No |
| `venta_id` | `bigint` | No |

- `comercio_documento_intentos_check`: `CHECK ((intentos >= 0))`
- `comercio_documento_pkey`: `PRIMARY KEY (id)`
- `comercio_documento_venta_id_854c6647_fk_operaciones_venta_id`: `FOREIGN KEY (venta_id) REFERENCES operaciones_venta(id) DEFERRABLE INITIALLY DEFERRED`
- `comercio_documento_venta_id_key`: `UNIQUE (venta_id)`
- Índice `comercio_documento_pkey`: `CREATE UNIQUE INDEX comercio_documento_pkey ON public.comercio_documento USING btree (id)`
- Índice `comercio_documento_venta_id_key`: `CREATE UNIQUE INDEX comercio_documento_venta_id_key ON public.comercio_documento USING btree (venta_id)`

## comercio_eventocomercial

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `fecha` | `timestamp with time zone` | No |
| `accion` | `character varying(60)` | No |
| `referencia` | `character varying(120)` | No |
| `detalle` | `jsonb` | No |
| `usuario_id` | `integer` | No |

- `comercio_eventocomercial_pkey`: `PRIMARY KEY (id)`
- `comercio_eventocomercial_usuario_id_49bf9779_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `comercio_eventocomercial_pkey`: `CREATE UNIQUE INDEX comercio_eventocomercial_pkey ON public.comercio_eventocomercial USING btree (id)`
- Índice `comercio_eventocomercial_usuario_id_49bf9779`: `CREATE INDEX comercio_eventocomercial_usuario_id_49bf9779 ON public.comercio_eventocomercial USING btree (usuario_id)`

## comercio_movimientocaja

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `clave` | `uuid` | No |
| `tipo` | `character varying(10)` | No |
| `monto` | `numeric(14,0)` | No |
| `motivo` | `character varying(250)` | No |
| `fecha` | `timestamp with time zone` | No |
| `caja_id` | `bigint` | No |

- `comercio_movimientocaja_caja_id_c1dcfc40_fk_comercio_caja_id`: `FOREIGN KEY (caja_id) REFERENCES comercio_caja(id) DEFERRABLE INITIALLY DEFERRED`
- `comercio_movimientocaja_clave_key`: `UNIQUE (clave)`
- `comercio_movimientocaja_pkey`: `PRIMARY KEY (id)`
- `movimiento_caja_positivo`: `CHECK ((monto > (0)::numeric))`
- Índice `comercio_movimientocaja_caja_id_c1dcfc40`: `CREATE INDEX comercio_movimientocaja_caja_id_c1dcfc40 ON public.comercio_movimientocaja USING btree (caja_id)`
- Índice `comercio_movimientocaja_clave_key`: `CREATE UNIQUE INDEX comercio_movimientocaja_clave_key ON public.comercio_movimientocaja USING btree (clave)`
- Índice `comercio_movimientocaja_pkey`: `CREATE UNIQUE INDEX comercio_movimientocaja_pkey ON public.comercio_movimientocaja USING btree (id)`

## compras_detallerecepcion

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `movimiento_id` | `bigint` | No |
| `linea_id` | `bigint` | No |
| `recepcion_id` | `bigint` | No |

- `compras_detallerecep_linea_id_26a32816_fk_compras_l`: `FOREIGN KEY (linea_id) REFERENCES compras_lineaorden(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_detallerecep_movimiento_id_e1ce8d36_fk_operacion`: `FOREIGN KEY (movimiento_id) REFERENCES operaciones_movimiento(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_detallerecep_recepcion_id_6b3dafe4_fk_compras_r`: `FOREIGN KEY (recepcion_id) REFERENCES compras_recepcion(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_detallerecepcion_movimiento_id_key`: `UNIQUE (movimiento_id)`
- `compras_detallerecepcion_pkey`: `PRIMARY KEY (id)`
- Índice `compras_detallerecepcion_linea_id_26a32816`: `CREATE INDEX compras_detallerecepcion_linea_id_26a32816 ON public.compras_detallerecepcion USING btree (linea_id)`
- Índice `compras_detallerecepcion_movimiento_id_key`: `CREATE UNIQUE INDEX compras_detallerecepcion_movimiento_id_key ON public.compras_detallerecepcion USING btree (movimiento_id)`
- Índice `compras_detallerecepcion_pkey`: `CREATE UNIQUE INDEX compras_detallerecepcion_pkey ON public.compras_detallerecepcion USING btree (id)`
- Índice `compras_detallerecepcion_recepcion_id_6b3dafe4`: `CREATE INDEX compras_detallerecepcion_recepcion_id_6b3dafe4 ON public.compras_detallerecepcion USING btree (recepcion_id)`

## compras_eventocompra

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `fecha` | `timestamp with time zone` | No |
| `accion` | `character varying(12)` | No |
| `motivo` | `character varying(300)` | No |
| `usuario_id` | `integer` | No |
| `orden_id` | `bigint` | No |

- `compras_eventocompra_orden_id_8e80fb34_fk_compras_o`: `FOREIGN KEY (orden_id) REFERENCES compras_ordencompra(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_eventocompra_pkey`: `PRIMARY KEY (id)`
- `compras_eventocompra_usuario_id_62add403_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `compras_eventocompra_orden_id_8e80fb34`: `CREATE INDEX compras_eventocompra_orden_id_8e80fb34 ON public.compras_eventocompra USING btree (orden_id)`
- Índice `compras_eventocompra_pkey`: `CREATE UNIQUE INDEX compras_eventocompra_pkey ON public.compras_eventocompra USING btree (id)`
- Índice `compras_eventocompra_usuario_id_62add403`: `CREATE INDEX compras_eventocompra_usuario_id_62add403 ON public.compras_eventocompra USING btree (usuario_id)`

## compras_eventoproveedor

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `fecha` | `timestamp with time zone` | No |
| `anterior` | `jsonb` | No |
| `posterior` | `jsonb` | No |
| `usuario_id` | `integer` | No |
| `proveedor_id` | `bigint` | No |

- `compras_eventoprovee_proveedor_id_10ddfe82_fk_compras_p`: `FOREIGN KEY (proveedor_id) REFERENCES compras_proveedor(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_eventoproveedor_pkey`: `PRIMARY KEY (id)`
- `compras_eventoproveedor_usuario_id_8a806335_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `compras_eventoproveedor_pkey`: `CREATE UNIQUE INDEX compras_eventoproveedor_pkey ON public.compras_eventoproveedor USING btree (id)`
- Índice `compras_eventoproveedor_proveedor_id_10ddfe82`: `CREATE INDEX compras_eventoproveedor_proveedor_id_10ddfe82 ON public.compras_eventoproveedor USING btree (proveedor_id)`
- Índice `compras_eventoproveedor_usuario_id_8a806335`: `CREATE INDEX compras_eventoproveedor_usuario_id_8a806335 ON public.compras_eventoproveedor USING btree (usuario_id)`

## compras_lineaorden

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `codigo` | `character varying(30)` | No |
| `nombre` | `character varying(160)` | No |
| `presentacion` | `character varying(180)` | No |
| `solicitada` | `integer` | No |
| `recibida` | `integer` | No |
| `costo_unitario` | `numeric(12,0)` | No |
| `producto_id` | `bigint` | No |
| `orden_id` | `bigint` | No |

- `compras_lineaorden_orden_id_f3e44b46_fk_compras_ordencompra_id`: `FOREIGN KEY (orden_id) REFERENCES compras_ordencompra(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_lineaorden_pkey`: `PRIMARY KEY (id)`
- `compras_lineaorden_producto_id_e13b0080_fk_catalogo_producto_id`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_lineaorden_recibida_check`: `CHECK ((recibida >= 0))`
- `compras_lineaorden_solicitada_check`: `CHECK ((solicitada >= 0))`
- `orden_cantidad_positiva`: `CHECK ((solicitada > 0))`
- `orden_costo_no_negativo`: `CHECK ((costo_unitario >= (0)::numeric))`
- `orden_producto_unico`: `UNIQUE (orden_id, producto_id)`
- `orden_recibida_en_rango`: `CHECK (((recibida >= 0) AND (recibida <= solicitada)))`
- Índice `compras_lineaorden_orden_id_f3e44b46`: `CREATE INDEX compras_lineaorden_orden_id_f3e44b46 ON public.compras_lineaorden USING btree (orden_id)`
- Índice `compras_lineaorden_pkey`: `CREATE UNIQUE INDEX compras_lineaorden_pkey ON public.compras_lineaorden USING btree (id)`
- Índice `compras_lineaorden_producto_id_e13b0080`: `CREATE INDEX compras_lineaorden_producto_id_e13b0080 ON public.compras_lineaorden USING btree (producto_id)`
- Índice `orden_producto_unico`: `CREATE UNIQUE INDEX orden_producto_unico ON public.compras_lineaorden USING btree (orden_id, producto_id)`

## compras_ordencompra

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `clave` | `uuid` | No |
| `huella` | `character varying(64)` | No |
| `proveedor_nombre` | `character varying(160)` | No |
| `fecha` | `timestamp with time zone` | No |
| `estado` | `character varying(12)` | No |
| `observaciones` | `character varying(300)` | No |
| `total` | `numeric(24,0)` | No |
| `usuario_id` | `integer` | No |
| `proveedor_id` | `bigint` | No |

- `compras_ordencompra_clave_key`: `UNIQUE (clave)`
- `compras_ordencompra_pkey`: `PRIMARY KEY (id)`
- `compras_ordencompra_proveedor_id_c42e35e1_fk_compras_p`: `FOREIGN KEY (proveedor_id) REFERENCES compras_proveedor(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_ordencompra_usuario_id_a2084c63_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `orden_estado_valido`: `CHECK (((estado)::text = ANY ((ARRAY['pendiente'::character varying, 'parcial'::character varying, 'completa'::character varying, 'anulada'::character varying])::text[])))`
- `orden_total_no_negativo`: `CHECK ((total >= (0)::numeric))`
- Índice `compras_ordencompra_clave_key`: `CREATE UNIQUE INDEX compras_ordencompra_clave_key ON public.compras_ordencompra USING btree (clave)`
- Índice `compras_ordencompra_pkey`: `CREATE UNIQUE INDEX compras_ordencompra_pkey ON public.compras_ordencompra USING btree (id)`
- Índice `compras_ordencompra_proveedor_id_c42e35e1`: `CREATE INDEX compras_ordencompra_proveedor_id_c42e35e1 ON public.compras_ordencompra USING btree (proveedor_id)`
- Índice `compras_ordencompra_usuario_id_a2084c63`: `CREATE INDEX compras_ordencompra_usuario_id_a2084c63 ON public.compras_ordencompra USING btree (usuario_id)`

## compras_proveedor

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `codigo` | `character varying(30)` | No |
| `nombre` | `character varying(160)` | No |
| `email` | `character varying(254)` | No |
| `telefono` | `character varying(30)` | No |
| `activo` | `boolean` | No |

- `compras_proveedor_codigo_key`: `UNIQUE (codigo)`
- `compras_proveedor_pkey`: `PRIMARY KEY (id)`
- Índice `compras_proveedor_codigo_0a388f85_like`: `CREATE INDEX compras_proveedor_codigo_0a388f85_like ON public.compras_proveedor USING btree (codigo varchar_pattern_ops)`
- Índice `compras_proveedor_codigo_key`: `CREATE UNIQUE INDEX compras_proveedor_codigo_key ON public.compras_proveedor USING btree (codigo)`
- Índice `compras_proveedor_pkey`: `CREATE UNIQUE INDEX compras_proveedor_pkey ON public.compras_proveedor USING btree (id)`

## compras_recepcion

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `clave` | `uuid` | No |
| `huella` | `character varying(64)` | No |
| `referencia` | `character varying(60)` | No |
| `fecha` | `timestamp with time zone` | No |
| `orden_id` | `bigint` | No |
| `usuario_id` | `integer` | No |

- `compras_recepcion_clave_key`: `UNIQUE (clave)`
- `compras_recepcion_orden_id_a3eefc66_fk_compras_ordencompra_id`: `FOREIGN KEY (orden_id) REFERENCES compras_ordencompra(id) DEFERRABLE INITIALLY DEFERRED`
- `compras_recepcion_pkey`: `PRIMARY KEY (id)`
- `compras_recepcion_usuario_id_88afd7b1_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `orden_referencia_recepcion_unica`: `UNIQUE (orden_id, referencia)`
- Índice `compras_recepcion_clave_key`: `CREATE UNIQUE INDEX compras_recepcion_clave_key ON public.compras_recepcion USING btree (clave)`
- Índice `compras_recepcion_orden_id_a3eefc66`: `CREATE INDEX compras_recepcion_orden_id_a3eefc66 ON public.compras_recepcion USING btree (orden_id)`
- Índice `compras_recepcion_pkey`: `CREATE UNIQUE INDEX compras_recepcion_pkey ON public.compras_recepcion USING btree (id)`
- Índice `compras_recepcion_usuario_id_88afd7b1`: `CREATE INDEX compras_recepcion_usuario_id_88afd7b1 ON public.compras_recepcion USING btree (usuario_id)`
- Índice `orden_referencia_recepcion_unica`: `CREATE UNIQUE INDEX orden_referencia_recepcion_unica ON public.compras_recepcion USING btree (orden_id, referencia)`

## gestion_configuracionalerta

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `ubicacion` | `character varying(12)` | No |
| `stock_minimo` | `integer` | No |
| `dias_vencimiento` | `integer` | No |
| `producto_id` | `bigint` | No |

- `gestion_alerta_producto_ubicacion`: `UNIQUE (producto_id, ubicacion)`
- `gestion_configuracio_producto_id_1049a67a_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `gestion_configuracionalerta_dias_vencimiento_check`: `CHECK ((dias_vencimiento >= 0))`
- `gestion_configuracionalerta_pkey`: `PRIMARY KEY (id)`
- `gestion_configuracionalerta_stock_minimo_check`: `CHECK ((stock_minimo >= 0))`
- Índice `gestion_alerta_producto_ubicacion`: `CREATE UNIQUE INDEX gestion_alerta_producto_ubicacion ON public.gestion_configuracionalerta USING btree (producto_id, ubicacion)`
- Índice `gestion_configuracionalerta_pkey`: `CREATE UNIQUE INDEX gestion_configuracionalerta_pkey ON public.gestion_configuracionalerta USING btree (id)`
- Índice `gestion_configuracionalerta_producto_id_1049a67a`: `CREATE INDEX gestion_configuracionalerta_producto_id_1049a67a ON public.gestion_configuracionalerta USING btree (producto_id)`

## gestion_eventogestion

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `fecha` | `timestamp with time zone` | No |
| `accion` | `character varying(100)` | No |
| `referencia` | `character varying(120)` | No |
| `detalle` | `jsonb` | No |
| `usuario_id` | `integer` | No |

- `gestion_eventogestion_pkey`: `PRIMARY KEY (id)`
- `gestion_eventogestion_usuario_id_98392493_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `gestion_eventogestion_pkey`: `CREATE UNIQUE INDEX gestion_eventogestion_pkey ON public.gestion_eventogestion USING btree (id)`
- Índice `gestion_eventogestion_usuario_id_98392493`: `CREATE INDEX gestion_eventogestion_usuario_id_98392493 ON public.gestion_eventogestion USING btree (usuario_id)`

## gestion_politicaprecio

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `aplica_cenabast` | `boolean` | No |
| `precio_maximo` | `numeric(12,0)` | Sí |
| `descuento_maximo` | `numeric(5,2)` | No |
| `fuente` | `character varying(300)` | No |
| `producto_id` | `bigint` | No |

- `gestion_cap_no_negativo`: `CHECK (((precio_maximo IS NULL) OR (precio_maximo >= (0)::numeric)))`
- `gestion_cenabast_cap`: `CHECK (((NOT aplica_cenabast) OR (precio_maximo IS NOT NULL)))`
- `gestion_descuento_rango`: `CHECK (((descuento_maximo >= (0)::numeric) AND (descuento_maximo <= (100)::numeric)))`
- `gestion_politicaprec_producto_id_9ffc453d_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `gestion_politicaprecio_pkey`: `PRIMARY KEY (id)`
- `gestion_politicaprecio_producto_id_key`: `UNIQUE (producto_id)`
- Índice `gestion_politicaprecio_pkey`: `CREATE UNIQUE INDEX gestion_politicaprecio_pkey ON public.gestion_politicaprecio USING btree (id)`
- Índice `gestion_politicaprecio_producto_id_key`: `CREATE UNIQUE INDEX gestion_politicaprecio_producto_id_key ON public.gestion_politicaprecio USING btree (producto_id)`

## gestion_precioprogramado

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `precio` | `numeric(12,0)` | No |
| `desde` | `date` | No |
| `hasta` | `date` | Sí |
| `fuente` | `character varying(300)` | No |
| `creado` | `timestamp with time zone` | No |
| `producto_id` | `bigint` | No |
| `usuario_id` | `integer` | No |

- `gestion_precio_no_negativo`: `CHECK ((precio >= (0)::numeric))`
- `gestion_precioprogra_producto_id_bf4e1213_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `gestion_precioprogramado_pkey`: `PRIMARY KEY (id)`
- `gestion_precioprogramado_usuario_id_9656a3c8_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `gestion_vigencia_orden`: `CHECK (((hasta IS NULL) OR (hasta >= desde)))`
- Índice `gestion_precioprogramado_pkey`: `CREATE UNIQUE INDEX gestion_precioprogramado_pkey ON public.gestion_precioprogramado USING btree (id)`
- Índice `gestion_precioprogramado_producto_id_bf4e1213`: `CREATE INDEX gestion_precioprogramado_producto_id_bf4e1213 ON public.gestion_precioprogramado USING btree (producto_id)`
- Índice `gestion_precioprogramado_usuario_id_9656a3c8`: `CREATE INDEX gestion_precioprogramado_usuario_id_9656a3c8 ON public.gestion_precioprogramado USING btree (usuario_id)`

## gestion_trabajador

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `rut` | `character varying(12)` | No |
| `telefono` | `character varying(30)` | No |
| `usuario_id` | `integer` | No |

- `gestion_trabajador_pkey`: `PRIMARY KEY (id)`
- `gestion_trabajador_rut_key`: `UNIQUE (rut)`
- `gestion_trabajador_usuario_id_5b2bb12f_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `gestion_trabajador_usuario_id_key`: `UNIQUE (usuario_id)`
- Índice `gestion_trabajador_pkey`: `CREATE UNIQUE INDEX gestion_trabajador_pkey ON public.gestion_trabajador USING btree (id)`
- Índice `gestion_trabajador_rut_e9a6ff6e_like`: `CREATE INDEX gestion_trabajador_rut_e9a6ff6e_like ON public.gestion_trabajador USING btree (rut varchar_pattern_ops)`
- Índice `gestion_trabajador_rut_key`: `CREATE UNIQUE INDEX gestion_trabajador_rut_key ON public.gestion_trabajador USING btree (rut)`
- Índice `gestion_trabajador_usuario_id_key`: `CREATE UNIQUE INDEX gestion_trabajador_usuario_id_key ON public.gestion_trabajador USING btree (usuario_id)`

## operaciones_detalleventa

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `nombre` | `character varying(160)` | No |
| `codigo` | `character varying(30)` | No |
| `precio_unitario` | `numeric(12,0)` | No |
| `cantidad` | `integer` | No |
| `producto_id` | `bigint` | No |
| `venta_id` | `bigint` | No |

- `detalle_cantidad_positiva`: `CHECK ((cantidad > 0))`
- `detalle_precio_no_negativo`: `CHECK ((precio_unitario >= (0)::numeric))`
- `operaciones_detallev_producto_id_3391ad3b_fk_catalogo_`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- `operaciones_detallev_venta_id_caa4cd57_fk_operacion`: `FOREIGN KEY (venta_id) REFERENCES operaciones_venta(id) DEFERRABLE INITIALLY DEFERRED`
- `operaciones_detalleventa_cantidad_check`: `CHECK ((cantidad >= 0))`
- `operaciones_detalleventa_pkey`: `PRIMARY KEY (id)`
- Índice `operaciones_detalleventa_pkey`: `CREATE UNIQUE INDEX operaciones_detalleventa_pkey ON public.operaciones_detalleventa USING btree (id)`
- Índice `operaciones_detalleventa_producto_id_3391ad3b`: `CREATE INDEX operaciones_detalleventa_producto_id_3391ad3b ON public.operaciones_detalleventa USING btree (producto_id)`
- Índice `operaciones_detalleventa_venta_id_caa4cd57`: `CREATE INDEX operaciones_detalleventa_venta_id_caa4cd57 ON public.operaciones_detalleventa USING btree (venta_id)`

## operaciones_eventoreporte

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `fecha` | `timestamp with time zone` | No |
| `tipo` | `character varying(12)` | No |
| `formato` | `character varying(4)` | No |
| `filtros` | `jsonb` | No |
| `filas` | `integer` | No |
| `total` | `numeric(24,0)` | Sí |
| `usuario_id` | `integer` | No |

- `operaciones_eventoreporte_filas_check`: `CHECK ((filas >= 0))`
- `operaciones_eventoreporte_pkey`: `PRIMARY KEY (id)`
- `operaciones_eventoreporte_usuario_id_13e1ca98_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `operaciones_eventoreporte_pkey`: `CREATE UNIQUE INDEX operaciones_eventoreporte_pkey ON public.operaciones_eventoreporte USING btree (id)`
- Índice `operaciones_eventoreporte_usuario_id_13e1ca98`: `CREATE INDEX operaciones_eventoreporte_usuario_id_13e1ca98 ON public.operaciones_eventoreporte USING btree (usuario_id)`

## operaciones_existencia

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `ubicacion` | `character varying(10)` | No |
| `cantidad` | `integer` | No |
| `lote_id` | `bigint` | No |

- `existencia_lote_ubicacion_unica`: `UNIQUE (lote_id, ubicacion)`
- `existencia_no_negativa`: `CHECK ((cantidad >= 0))`
- `existencia_ubicacion_valida`: `CHECK (((ubicacion)::text = ANY ((ARRAY['bodega'::character varying, 'vitrina'::character varying])::text[])))`
- `operaciones_existencia_cantidad_check`: `CHECK ((cantidad >= 0))`
- `operaciones_existencia_lote_id_25d7a227_fk_operaciones_lote_id`: `FOREIGN KEY (lote_id) REFERENCES operaciones_lote(id) DEFERRABLE INITIALLY DEFERRED`
- `operaciones_existencia_pkey`: `PRIMARY KEY (id)`
- Índice `existencia_lote_ubicacion_unica`: `CREATE UNIQUE INDEX existencia_lote_ubicacion_unica ON public.operaciones_existencia USING btree (lote_id, ubicacion)`
- Índice `operaciones_existencia_lote_id_25d7a227`: `CREATE INDEX operaciones_existencia_lote_id_25d7a227 ON public.operaciones_existencia USING btree (lote_id)`
- Índice `operaciones_existencia_pkey`: `CREATE UNIQUE INDEX operaciones_existencia_pkey ON public.operaciones_existencia USING btree (id)`

## operaciones_lote

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `codigo` | `character varying(60)` | No |
| `vencimiento` | `date` | No |
| `bloqueado` | `boolean` | No |
| `producto_id` | `bigint` | No |

- `lote_producto_codigo_unico`: `UNIQUE (producto_id, codigo)`
- `operaciones_lote_pkey`: `PRIMARY KEY (id)`
- `operaciones_lote_producto_id_fa47296e_fk_catalogo_producto_id`: `FOREIGN KEY (producto_id) REFERENCES catalogo_producto(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `lote_producto_codigo_unico`: `CREATE UNIQUE INDEX lote_producto_codigo_unico ON public.operaciones_lote USING btree (producto_id, codigo)`
- Índice `operaciones_lote_pkey`: `CREATE UNIQUE INDEX operaciones_lote_pkey ON public.operaciones_lote USING btree (id)`
- Índice `operaciones_lote_producto_id_fa47296e`: `CREATE INDEX operaciones_lote_producto_id_fa47296e ON public.operaciones_lote USING btree (producto_id)`

## operaciones_movimiento

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `clave` | `uuid` | No |
| `tipo` | `character varying(10)` | No |
| `origen` | `character varying(10)` | No |
| `destino` | `character varying(10)` | No |
| `cantidad` | `integer` | No |
| `fecha` | `timestamp with time zone` | No |
| `detalle_venta_id` | `bigint` | Sí |
| `lote_id` | `bigint` | No |
| `usuario_id` | `integer` | No |

- `movimiento_cantidad_positiva`: `CHECK ((cantidad > 0))`
- `movimiento_tipo_coherente`: `CHECK (((((destino)::text = ANY ((ARRAY['bodega'::character varying, 'vitrina'::character varying])::text[])) AND (detalle_venta_id IS NULL) AND ((origen)::text = ''::text) AND ((tipo)::text = 'ingreso'::text)) OR (((destino)::text = ANY ((ARRAY['bodega'::character varying, 'vitrina'::character varying])::text[])) AND (detalle_venta_id IS NULL) AND ((origen)::text = ANY ((ARRAY['bodega'::character varying, 'vitrina'::character varying])::text[])) AND ((tipo)::text = 'traslado'::text) AND (NOT ((origen)::text = (destino)::text))) OR (((destino)::text = ''::text) AND (detalle_venta_id IS NOT NULL) AND ((origen)::text = 'vitrina'::text) AND ((tipo)::text = 'venta'::text))))`
- `operaciones_movimien_detalle_venta_id_28175abe_fk_operacion`: `FOREIGN KEY (detalle_venta_id) REFERENCES operaciones_detalleventa(id) DEFERRABLE INITIALLY DEFERRED`
- `operaciones_movimiento_cantidad_check`: `CHECK ((cantidad >= 0))`
- `operaciones_movimiento_clave_key`: `UNIQUE (clave)`
- `operaciones_movimiento_lote_id_0a4562ac_fk_operaciones_lote_id`: `FOREIGN KEY (lote_id) REFERENCES operaciones_lote(id) DEFERRABLE INITIALLY DEFERRED`
- `operaciones_movimiento_pkey`: `PRIMARY KEY (id)`
- `operaciones_movimiento_usuario_id_c8065588_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- Índice `operaciones_movimiento_clave_key`: `CREATE UNIQUE INDEX operaciones_movimiento_clave_key ON public.operaciones_movimiento USING btree (clave)`
- Índice `operaciones_movimiento_detalle_venta_id_28175abe`: `CREATE INDEX operaciones_movimiento_detalle_venta_id_28175abe ON public.operaciones_movimiento USING btree (detalle_venta_id)`
- Índice `operaciones_movimiento_lote_id_0a4562ac`: `CREATE INDEX operaciones_movimiento_lote_id_0a4562ac ON public.operaciones_movimiento USING btree (lote_id)`
- Índice `operaciones_movimiento_pkey`: `CREATE UNIQUE INDEX operaciones_movimiento_pkey ON public.operaciones_movimiento USING btree (id)`
- Índice `operaciones_movimiento_usuario_id_c8065588`: `CREATE INDEX operaciones_movimiento_usuario_id_c8065588 ON public.operaciones_movimiento USING btree (usuario_id)`

## operaciones_venta

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `clave` | `uuid` | No |
| `fecha` | `timestamp with time zone` | No |
| `total` | `numeric(14,0)` | No |
| `usuario_id` | `integer` | No |

- `operaciones_venta_clave_key`: `UNIQUE (clave)`
- `operaciones_venta_pkey`: `PRIMARY KEY (id)`
- `operaciones_venta_usuario_id_b1fa22b8_fk_auth_user_id`: `FOREIGN KEY (usuario_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED`
- `venta_total_no_negativo`: `CHECK ((total >= (0)::numeric))`
- Índice `operaciones_venta_clave_key`: `CREATE UNIQUE INDEX operaciones_venta_clave_key ON public.operaciones_venta USING btree (clave)`
- Índice `operaciones_venta_pkey`: `CREATE UNIQUE INDEX operaciones_venta_pkey ON public.operaciones_venta USING btree (id)`
- Índice `operaciones_venta_usuario_id_b1fa22b8`: `CREATE INDEX operaciones_venta_usuario_id_b1fa22b8 ON public.operaciones_venta USING btree (usuario_id)`

## seguridad_eventoacceso

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `id` | `bigint` | No |
| `cuenta` | `character varying(64)` | No |
| `origen` | `character varying(64)` | No |
| `fecha` | `timestamp with time zone` | No |
| `resultado` | `character varying(12)` | No |

- `seguridad_eventoacceso_pkey`: `PRIMARY KEY (id)`
- Índice `seguridad_eventoacceso_pkey`: `CREATE UNIQUE INDEX seguridad_eventoacceso_pkey ON public.seguridad_eventoacceso USING btree (id)`

## seguridad_limiteacceso

| Columna | Tipo PostgreSQL | Admite nulo |
|---|---|---|
| `clave` | `character varying(64)` | No |
| `inicio` | `timestamp with time zone` | No |
| `intentos` | `integer` | No |
| `bloqueado_hasta` | `timestamp with time zone` | Sí |

- `seguridad_limiteacceso_intentos_check`: `CHECK ((intentos >= 0))`
- `seguridad_limiteacceso_pkey`: `PRIMARY KEY (clave)`
- Índice `seguridad_limiteacceso_clave_8001eb4f_like`: `CREATE INDEX seguridad_limiteacceso_clave_8001eb4f_like ON public.seguridad_limiteacceso USING btree (clave varchar_pattern_ops)`
- Índice `seguridad_limiteacceso_pkey`: `CREATE UNIQUE INDEX seguridad_limiteacceso_pkey ON public.seguridad_limiteacceso USING btree (clave)`
