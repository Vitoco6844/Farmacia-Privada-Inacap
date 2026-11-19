"""Contratos de pantalla para el frontend. Solo incluye campos presentables."""
from datetime import date

from django import forms


def campo(nombre, etiqueta, tipo='text', **opciones):
    return dict(nombre=nombre, etiqueta=etiqueta, tipo=tipo, **opciones)


def fijo(nombre, valor):
    return campo(nombre, '', 'hidden', valor=str(valor))


def seleccionar(nombre, etiqueta, opciones, requerido=True):
    return campo(nombre, etiqueta, 'select', opciones=list(opciones), requerido=requerido)


def formulario(titulo, campos, ruta=None, metodo='POST', **extras):
    return dict(titulo=titulo, campos=campos, ruta=ruta, metodo=metodo, **extras)


def campos_form(form):
    resultado = []
    for bound in form:
        f, widget = bound.field, bound.field.widget
        valor = bound.value()
        if isinstance(widget, (forms.PasswordInput, forms.FileInput)):
            valor = None
        if isinstance(valor, date):
            valor = valor.isoformat()[:10]
        datos = {'valor': valor, 'requerido': f.required, 'ayuda': str(f.help_text or ''),
                 'deshabilitado': f.disabled}
        if isinstance(f, forms.ChoiceField):
            tipo = 'multiple' if isinstance(f, (forms.MultipleChoiceField, forms.ModelMultipleChoiceField)) else 'select'
            datos['opciones'] = [(str(k), str(v)) for k, v in f.choices]
        elif isinstance(f, forms.BooleanField):
            tipo = 'checkbox'
        elif isinstance(f, forms.DateField):
            tipo = 'date'
        elif isinstance(widget, forms.Textarea):
            tipo = 'textarea'
        else:
            tipo = getattr(widget, 'input_type', 'text')
        for nombre, valor in (('min', getattr(f, 'min_value', None)), ('max', getattr(f, 'max_value', None)),
                              ('maxLength', getattr(f, 'max_length', None)),
                              ('step', widget.attrs.get('step', 'any' if isinstance(f, forms.DecimalField) else None))):
            if valor is not None:
                datos[nombre] = valor
        resultado.append(campo(bound.html_name, str(bound.label or bound.name), tipo, **datos))
    return resultado


def formulario_django(contexto, titulo='Guardar', **extras):
    return {'formularios': [formulario(titulo, campos_form(contexto['form']), **extras)]}


def errores_form(contexto):
    errores = [str(mensaje) for grupo in contexto['form'].errors.values() for mensaje in grupo] if 'form' in contexto else []
    if 'lineas' in contexto:
        lineas = contexto['lineas']
        errores.extend(str(mensaje) for mensaje in lineas.non_form_errors())
        errores.extend(str(mensaje) for fila in lineas.errors for grupo in fila.values() for mensaje in grupo)
    return errores


def enlace(titulo, ruta):
    return dict(titulo=titulo, ruta=ruta)


def tabla(columnas, filas, nombre=None):
    return dict(columnas=columnas, filas=list(filas), nombre=nombre)


def listado(columnas, filas, pagina=None, **extras):
    datos = dict(tablas=[tabla(columnas, filas)], **extras)
    if pagina is not None:
        datos.update(pagina=pagina.number, paginas=pagina.paginator.num_pages)
    return datos
