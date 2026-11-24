from uuid import uuid4

from django.core.exceptions import ValidationError
from django.utils import timezone

from compras.forms import AnularForm
from compras.models import OrdenCompra
from compras.services import anular_orden
from operaciones.models import Venta
from .respuestas import render
from .ui_datos import campo, campos_form, enlace, fijo, formulario, formulario_django, listado, seleccionar, tabla


def proveedores(request, c):
    p = c['pagina']
    editar = request.user.has_perm('compras.change_proveedor')
    return listado(['Código', 'Nombre', 'Correo', 'Teléfono', 'Estado', ''],
                   ([o.codigo, o.nombre, o.email, o.telefono, 'Activo' if o.activo else 'Inactivo',
                     enlace('Editar', f'proveedor-editar/{o.pk}') if editar else ''] for o in p), p,
                   enlaces=[enlace('Nuevo proveedor', 'proveedor-nuevo')]
                   if request.user.has_perm('compras.add_proveedor') else [])


def anular(request, pk):
    orden = OrdenCompra.objects.get(pk=pk)
    form = AnularForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        anular_orden(usuario=request.user, orden_id=pk, motivo=form.cleaned_data['motivo'])
        return render(request, '', {'guardado': True})
    return render(request, '', {'orden': orden, 'form': form})


def formulario_anular(request, c):
    return dict(formulario_django(c, 'Confirmar anulación'),
                resumen=[['Orden', f"OC-{c['orden'].pk}"], ['Estado', c['orden'].get_estado_display()]])


def alertas_stock(request, c):
    p = c['pagina']
    return listado(['Código', 'Producto', 'Disponible', 'Stock mínimo', 'Motivo'],
                   ([o.codigo, o.nombre, o.disponible, o.stock_minimo, o.motivo] for o in p), p)


def movimientos(request, c):
    p = c['pagina']
    return listado(['Fecha', 'Producto', 'Lote', 'Tipo', 'Origen', 'Destino', 'Envases'],
                   ([o.fecha, o.lote.producto.nombre, o.lote.codigo, o.get_tipo_display(),
                     o.get_origen_display(), o.get_destino_display(), o.cantidad] for o in p), p)


def caja(request, c):
    activa = c['caja']
    datos = {}
    if activa:
        clave = fijo('clave', c['clave'])
        ref = fijo('caja_id', activa.pk)
        datos['resumen'] = [['Caja abierta', activa.pk], ['Fondo inicial CLP', activa.fondo],
                            ['Efectivo esperado CLP', c['resumen']['esperado']]] + [
            [etiqueta, c['resumen'][key]] for key, etiqueta in (
                ('efectivo', 'Ventas en efectivo'), ('tarjeta', 'Ventas con tarjeta'),
                ('transferencia', 'Transferencias'), ('ingresos', 'Ingresos'), ('retiros', 'Retiros'))]
        datos['formularios'] = [
            formulario('Registrar movimiento', [fijo('accion', 'mover'), ref, clave,
                seleccionar('tipo', 'Tipo', [('ingreso', 'Ingreso'), ('retiro', 'Retiro')]),
                campo('monto', 'Monto CLP', 'number', min=1, requerido=True),
                campo('motivo', 'Motivo', maxLength=250, requerido=True)]),
            formulario('Cerrar caja', [fijo('accion', 'cerrar'), ref,
                campo('contado', 'Efectivo contado CLP', 'number', min=0, requerido=True),
                campo('motivo', 'Motivo si hay diferencia', maxLength=250)]),
        ]
        datos['enlaces'] = [enlace('Ir al punto de venta', 'pos')] if request.user.has_perm('operaciones.add_venta') else []
    else:
        datos['formularios'] = [formulario('Abrir caja', [fijo('accion', 'abrir'),
            campo('fondo', 'Fondo inicial CLP', 'number', min=0, requerido=True)])]
    datos['tablas'] = [tabla(['Caja', 'Cierre', 'Esperado CLP', 'Contado CLP', 'Motivo'],
                             ([o.pk, o.cierre, o.esperado_cierre, o.contado, o.motivo_diferencia] for o in c['historial']),
                             'Cierres anteriores')]
    return datos


def pos(request, c):
    activa = c['caja']
    if not activa:
        return {'resumen': [['Caja', 'Abre tu caja para vender.']], 'enlaces': [enlace('Ir a caja', 'caja')]}
    convenios = list(c['convenios'])
    campos = [
        fijo('caja_id', activa.pk), fijo('clave', c['clave']),
        seleccionar('medio', 'Medio de pago', [('efectivo', 'Efectivo'), ('tarjeta', 'Tarjeta'),
                                               ('transferencia', 'Transferencia')]),
        seleccionar('convenio', 'Convenio', [('', 'Sin convenio'), *[(o.pk, o.nombre) for o in convenios]], False),
        campo('descuento', 'Descuento manual (%)', 'number', valor=0, min=0, max=100, step='0.01'),
        seleccionar('tipo_documento', 'Documento académico', [('boleta', 'Boleta'), ('factura', 'Factura')]),
        campo('receptor', 'Razón social para factura', maxLength=160),
        campo('rut', 'RUT para factura', maxLength=20),
        campo('receta', 'Número interno de receta', 'number', min=1),
        campo('retirante', 'Número interno de quien retira', 'number', min=1),
        campo('autorizacion', 'Relación y referencia de autorización del tercero', maxLength=300),
    ]
    return {'pos': {'caja': activa.pk}, 'formularios': [formulario('Confirmar venta', campos, carrito=True)]}


def convenios(request, c):
    usuario = request.user
    edicion = c['editando']
    permisos = usuario.has_perm('comercio.change_convenio' if edicion else 'comercio.add_convenio')
    return listado(['Nombre', 'Inicio', 'Fin', 'Porcentaje', 'Tope CLP', 'Activo', ''],
                   ([o.nombre, o.inicio, o.fin, o.porcentaje, o.tope, o.activo,
                     enlace('Editar', f'convenios?editar={o.pk}') if usuario.has_perm('comercio.change_convenio') else '']
                    for o in c['convenios']),
                   formularios=[formulario('Guardar convenio', campos_form(c['form']))] if permisos else [])


def documento(request, c):
    d = c['doc']
    v = d.venta
    cobro = getattr(v, 'cobro', None)
    resumen = [['Número', d.pk], ['Venta', v.pk], ['Tipo', d.get_tipo_display()],
               ['Estado', d.get_estado_display()], ['Total CLP', v.total], ['Intentos', d.intentos]]
    if cobro:
        resumen.extend([['Medio de pago', cobro.medio], ['Bruto CLP', cobro.bruto],
                        ['Descuento CLP', cobro.descuento], ['Aporte convenio CLP', cobro.beneficio]])
    if d.error:
        resumen.append(['Resultado de emisión', d.error])
    return {'nota': 'Documento académico sin validez tributaria.', 'resumen': resumen,
            'formularios': [formulario('Emitir o reintentar', [fijo('accion', 'emitir')]),
                            formulario('Simular fallo', [fijo('accion', 'simular_error')])]
            if d.estado != 'emitido' and request.user.has_perm('comercio.emitir_documento') else [],
            'enlaces': [enlace('Ver venta', f'venta/{v.pk}')]}


def ventas(request, c):
    p = c['pagina']
    return listado(['Fecha', 'Venta', 'Total CLP'],
                   ([o.fecha, enlace(f'Venta {o.pk}', f'venta/{o.pk}'), o.total] for o in p), p)


def venta(request, c):
    v = c['venta']
    doc = getattr(v, 'documento', None)
    entrega = getattr(v, 'entrega_clinica', None)
    enlaces = [enlace('Documento académico', f'documento/{doc.pk}')] if doc else []
    if entrega and request.user.has_perm('clinica.view_entrega'):
        enlaces.append(enlace('Orden de entrega', f'entrega/{entrega.pk}'))
    return listado(['Producto', 'Código', 'Envases', 'Precio unitario CLP', 'Lotes'],
                   ([o.nombre, o.codigo, o.cantidad, o.precio_unitario,
                     ', '.join(f'{a.lote.codigo} ({a.cantidad})' for a in o.asignaciones.all())] for o in v.detalles.all()),
                   resumen=[['Venta', v.pk], ['Fecha', v.fecha], ['Total CLP', v.total]], enlaces=enlaces)


def _clp(valor):
    return '$ ' + f'{int(valor or 0):,}'.replace(',', '.')


def panel(request, c):
    """Turno de hoy para el frontend: mismos indicadores y gráficos que el Inicio de Django."""
    resumen = []
    graficos = []
    if c.get('ver_comercial'):
        resumen += [['Ventas de hoy', c['ventas_hoy']], ['Importe vendido hoy', _clp(c['importe_hoy'])]]
        horas = c['horas']
        graficos.append(dict(
            tipo='columnas', titulo='Ventas por hora',
            nota=f"Hoy · la hora más fuerte fue {c['pico']['rango']}" if c['pico'] else 'Hoy',
            vacio='Todavía no hay ventas hoy. Cuando se confirme la primera aparecerá aquí, hora por hora.',
            items=[dict(etiqueta=h['etiqueta'], alto=h['alto'], destacado=False,
                        tip=f"{h['rango']} · {_clp(h['total'])} · {h['cantidad']} ventas") for h in horas],
            tabla=tabla(['Hora', 'Ventas', 'Monto'], ([h['rango'], h['cantidad'], _clp(h['total'])] for h in horas))))
        dias = c['dias']
        graficos.append(dict(
            tipo='columnas', titulo='Última semana', nota='Hoy destacado; los demás días en tono suave', semana=True,
            items=[dict(etiqueta=d['etiqueta'], alto=d['alto'], destacado=d['es_hoy'], valor=_clp(d['total']) if d['es_hoy'] else '',
                        tip=f"{d['etiqueta']} {d['dia']:%d/%m} · {_clp(d['total'])} · {d['cantidad']} ventas") for d in dias],
            tabla=tabla(['Día', 'Ventas', 'Monto'], ([f"{d['etiqueta']} {d['dia']:%d/%m}", d['cantidad'], _clp(d['total'])] for d in dias))))
    resumen += [['Productos bajo mínimo', c['bajos_total']], ['Lotes próximos a vencer', c['proximos_total']],
                ['Lotes no utilizables por fecha', c['vencidos_total']]]
    graficos.append(dict(tipo='segmentos', titulo='Estado de la vitrina', nota='Productos activos según su stock vigente en vitrina',
                         items=[dict(clave=s['clave'], nombre=s['nombre'], cantidad=s['cantidad'], detalle=s['detalle'])
                                for s in c['vitrina']]))
    if c.get('ver_comercial'):
        graficos.append(dict(tipo='barras', titulo='Cómo pagaron hoy', nota='El efectivo es lo que debe cuadrar en caja',
                             vacio='Sin pagos registrados hoy. Abre tu caja y confirma una venta para ver aquí cómo pagan los clientes.'
                             if not c['importe_hoy'] else '',
                             items=[dict(nombre=p['nombre'], ancho=p['ancho'], valor=_clp(p['total']), porcentaje=p['porcentaje'])
                                    for p in c['pagos']]))
    tablas = [tabla(['Producto', 'Disponible', 'Mínimo', 'Motivo'], ([p.nombre, p.disponible, p.stock_minimo, p.motivo] for p in c['bajos']),
                    'Reposición prioritaria'),
              tabla(['Producto / lote', 'Vence', 'Envases'],
                    ([f'{l.producto.nombre} · {l.codigo}', l.vencimiento.strftime('%d/%m/%Y'), l.envases] for l in c['proximos']),
                    'Vencimientos próximos')]
    return dict(resumen=resumen, graficos=graficos, tablas=tablas,
                nota=f"Actualizado a las {timezone.localtime(c['actualizado']):%H:%M} · hora de Santiago.")
