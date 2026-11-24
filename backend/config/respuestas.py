"""Permite a vistas compartidas entregar datos a la interfaz independiente."""
from django.http import Http404
from django.shortcuts import render as render_html


def id_numerico(valor, error=Http404):
    """Convierte un identificador recibido por URL o formulario; uno inválido equivale a «no existe»."""
    texto = str(valor or '').strip()
    if not (texto.isascii() and texto.isdigit() and len(texto) <= 18):
        raise error('Identificador inválido.')
    return int(texto)


def render(request, plantilla, contexto=None, *, status=None):
    respuesta_api = getattr(request, 'respuesta_api', None)
    if respuesta_api is not None:
        return respuesta_api(contexto or {}, status or 200)
    return render_html(request, plantilla, contexto, status=status)
