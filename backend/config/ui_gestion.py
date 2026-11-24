from .ui_datos import campo, campos_form, enlace, fijo, formulario, listado, seleccionar, tabla


def filtro_texto(c, etiqueta, nombre='q'):
    return formulario('Buscar', [campo(nombre, etiqueta, valor=c.get(nombre, ''), maxLength=100)], metodo='GET')


def usuarios(request, c):
    p = c['pagina']
    return listado(['Usuario', 'Nombre', 'Roles', 'Activo', ''],
                   ([o.username, o.get_full_name(), ', '.join(g.name for g in o.groups.all()), o.is_active,
                     enlace('Editar', f'usuario-editar/{o.pk}')] for o in p), p,
                   formularios=[filtro_texto(c, 'Usuario, nombre o RUT')],
                   enlaces=[enlace('Nuevo trabajador', 'usuario-nuevo')])


def categorias(request, c):
    editar = request.user.has_perm('catalogo.change_categoria')
    return listado(['Categoría', ''],
                   ([nombre, enlace('Editar', f'categoria-editar/{url.rstrip("/").split("/")[-1]}') if editar else '']
                    for nombre, url in c['filas']),
                   enlaces=[enlace('Nueva categoría', 'categoria-nueva')]
                   if request.user.has_perm('catalogo.add_categoria') else [])


def precios(request, c):
    return {
        'enlaces': [enlace('Programar precio', 'precio-nuevo')],
        'tablas': [
            tabla(['Producto', 'Vigente CLP', 'Máximo CLP', 'Descuento máximo (%)', ''],
                  ([str(f['producto']), f['vigente'],
                    f['politica'].precio_maximo if f['politica'] else None,
                    f['politica'].descuento_maximo if f['politica'] else 0,
                    enlace('Configurar límites', f"precio-limites/{f['producto'].pk}")] for f in c['productos'])),
            tabla(['Producto', 'Precio CLP', 'Desde', 'Hasta', 'Fuente'],
                  ([str(o.producto), o.precio, o.desde, o.hasta, o.fuente] for o in c['historial']), 'Historial reciente'),
        ],
    }


def alertas(request, c):
    return listado(['Producto', 'Ubicación', 'Disponible', 'Umbral', 'Stock bajo', 'Lotes en alerta', ''],
                   ([str(s['config'].producto), s['config'].get_ubicacion_display(), s['disponible'],
                     s['config'].stock_minimo, s['bajo'],
                     ', '.join(f'{l.lote.codigo} ({l.lote.vencimiento})' for l in s['vencimientos']),
                     enlace('Editar', f"alerta-editar/{s['config'].pk}")] for s in c['estados']),
                   enlaces=[enlace('Configurar alerta', 'alerta-nueva')])


def indicadores(request, c):
    total = c.get('totales', {})
    return listado(['Código', 'Producto', 'Categoría', 'Envases', 'Importe bruto CLP'],
                   ([o['codigo'], o['nombre'], o['producto__categoria__nombre'], o['envases'], o['total']]
                    for o in c.get('filas', [])),
                   formularios=[formulario('Aplicar filtros', campos_form(c['form']), metodo='GET')],
                   resumen=[['Ventas', c.get('ventas')], ['Envases', total.get('envases')],
                            ['Importe bruto CLP', total.get('total')], ['Recetas', c.get('recetas')],
                            ['Recetas pendientes', c.get('pendientes')], ['Entregas', c.get('entregas')]])


def reportes(request, c):
    formato = [seleccionar('formato', 'Salida', [('', 'Consultar'), ('pdf', 'PDF'), ('xlsx', 'Excel')], False)]
    return listado(c['cabeceras'], c.get('filas_pantalla', []), c.get('pagina'),
                   formularios=[formulario('Generar reporte', campos_form(c['form']) + formato, metodo='GET')],
                   resumen=[[k.capitalize(), v] for k, v in c.get('totales', {}).items() if v is not None])


def auditoria(request, c):
    p = c['pagina']
    filtros = [seleccionar('modulo', 'Módulo', [('', 'Todos'), *[(m, m) for m in c['modulos']]], False),
               campo('actor', 'Responsable', valor=c['actor'], maxLength=100),
               campo('desde', 'Desde', 'date', valor=c['desde']),
               campo('hasta', 'Hasta', 'date', valor=c['hasta'])]
    filtros[0]['valor'] = c['modulo']
    return listado(['Fecha', 'Módulo', 'Responsable', 'Acción', 'Referencia'],
                   ([o['fecha'], o['modulo'], o['actor'], o['accion'], o['referencia']] for o in p), p,
                   formularios=[formulario('Aplicar filtros', filtros, metodo='GET')])


def recetas(request, c):
    return listado(['Receta', 'Paciente', 'Vence', 'Estado'],
                   ([enlace(f'Receta {o.pk}', f'receta/{o.pk}'), str(o.paciente), o.vence, o.get_estado_display()]
                    for o in c['recetas']),
                   formularios=[filtro_texto(c, 'Nombre o identificador del paciente')],
                   enlaces=[enlace('Registrar receta', 'receta-nueva')]
                   if request.user.has_perm('clinica.gestionar_clinica') else [])


def receta_nueva(request, c):
    lineas = c['lineas']
    principal = campos_form(c['form']) + campos_form(lineas.management_form)
    grupos = [campos_form(f) for f in lineas.forms]
    return {'formularios': [formulario('Registrar receta', principal, grupos=grupos, prefijo=lineas.prefix)]}


def personas(request, c):
    ruta = 'pacientes' if request.respuesta_api_ruta == 'pacientes' else 'prescriptores'
    return listado(['Número', 'Identificador', 'Nombre', 'Activo', ''],
                   ([o.pk, o.identificador, o.nombre, o.activo,
                     enlace('Editar', f'{ruta}?editar={o.pk}')] for o in c['registros'][:200]),
                   formularios=[formulario('Guardar registro', campos_form(c['form']))])


def receta(request, c):
    r = c['receta']
    usuario = request.user
    es_qf = c['es_qf']
    lineas = list(r.lineas.select_related('producto'))
    formularios = []
    if es_qf and usuario.has_perm('clinica.revisar_receta') and r.estado != 'rechazada':
        decisiones = [('aprobar', 'Aprobar'), ('rechazar', 'Rechazar')] if r.estado == 'pendiente' else [('rechazar', 'Revocar aprobación')]
        formularios.append(formulario('Registrar revisión' if r.estado == 'pendiente' else 'Revocar aprobación', [fijo('accion', 'revisar'),
            seleccionar('decision', 'Decisión profesional', decisiones),
            campo('nota', 'Observación (obligatoria para revocar)', 'textarea', maxLength=500)]))
    controlados = [(o.pk, str(o.producto)) for o in lineas if o.producto.condicion == 'Receta retenida']
    if r.estado == 'aprobada' and controlados and es_qf and usuario.has_perm('clinica.autorizar_controlado'):
        formularios.append(formulario('Autorizar controlado', [fijo('accion', 'autorizar'),
            seleccionar('linea', 'Producto', controlados), campo('cantidad', 'Envases', 'number', min=1, requerido=True)]))
    if usuario.has_perm('clinica.gestionar_clinica'):
        formularios.append(formulario('Adjuntar respaldo', [fijo('accion', 'adjunto'), *campos_form(c['form'])]))
    adjuntos = list(r.adjuntos.all())
    if adjuntos and es_qf and usuario.has_perm('clinica.revisar_receta'):
        formularios.append(formulario('Registrar revisión de adjunto', [fijo('accion', 'revisar_adjunto'),
            seleccionar('adjunto', 'Archivo', [(a.pk, a.nombre) for a in adjuntos]),
            seleccionar('decision', 'Decisión', [('aprobar', 'Marcar revisado'), ('rechazar', 'Rechazar')])]))
    enlaces = [enlace(f'Orden de entrega {e.folio}', f'entrega/{e.pk}') for e in r.entregas.all()] if usuario.has_perm('clinica.view_entrega') else []
    puede_descargar = es_qf and usuario.has_perm('clinica.descargar_adjunto')
    return {'resumen': [['Receta', r.pk], ['Paciente', str(r.paciente)], ['Prescriptor', str(r.prescriptor)],
                        ['Estado', r.get_estado_display()], ['Vence', r.vence]], 'formularios': formularios,
            'enlaces': enlaces,
            'tablas': [tabla(['Producto', 'Prescrito', 'Entregado', 'Saldo'],
                             ([str(l.producto), l.cantidad, l.entregada, l.saldo if l.saldo is not None else 'Sin saldo definido']
                              for l in lineas)),
                       tabla(['Archivo', 'Estado', ''],
                             ([a.nombre, a.get_estado_display(),
                               enlace('Descargar', f'adjunto/{a.pk}') if puede_descargar and a.estado != 'rechazado' else '']
                              for a in adjuntos), 'Adjuntos')]}


def controlados(request, c):
    asientos = list(c['asientos'])
    formularios = []
    if request.user.groups.filter(name='Químico Farmacéutico').exists() and request.user.has_perm('clinica.autorizar_controlado'):
        opciones = [(o.pk, f'#{o.pk} · {o.producto}') for o in asientos if o.compensa_id is None and o.cantidad > 0]
        if opciones:
            formularios.append(formulario('Registrar compensación', [seleccionar('asiento', 'Asiento original', opciones),
                campo('motivo', 'Motivo', 'textarea', requerido=True)]))
    return listado(['Asiento', 'Fecha', 'Producto', 'Cantidad', 'Responsable', 'Compensa', 'Motivo'],
                   ([o.pk, o.fecha, str(o.producto), o.cantidad, o.profesional.username, o.compensa_id, o.motivo]
                    for o in asientos), formularios=formularios)


def entrega(request, c):
    e = c['entrega']
    i = e.instantanea
    return listado(['Código', 'Producto', 'Cantidad'],
                   ([o.get('codigo'), o.get('nombre'), o.get('cantidad')] for o in i.get('productos', [])),
                   resumen=[['Folio', e.folio], ['Venta', e.venta_id], ['Receta', e.receta_id],
                            ['Paciente', i.get('paciente')], ['Retira', i.get('retirante')], ['Fecha', e.fecha],
                            ['Autorización de retiro', e.autorizacion_retiro]],
                   imprimir=True)
