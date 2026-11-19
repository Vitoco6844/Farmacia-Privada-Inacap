"""Permite a vistas compartidas entregar datos a la interfaz independiente."""
from django.shortcuts import render as render_html


def render(request, plantilla, contexto=None, *, status=None):
    respuesta_api = getattr(request, 'respuesta_api', None)
    if respuesta_api is not None:
        return respuesta_api(contexto or {}, status or 200)
    return render_html(request, plantilla, contexto, status=status)
