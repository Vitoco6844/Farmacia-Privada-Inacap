import logging
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import redirect
from config.respuestas import render
from django.utils import timezone
from .exportaciones import generar_excel, generar_pdf, visible
from .models import EventoReporte
from .reportes import MAX_EXPORT_ROWS, InventarioFiltro, VentasFiltro, columnas, consulta, descripcion_filtros, filas, resumen

logger = logging.getLogger(__name__)


@login_required
def inicio(request):
    if request.user.has_perm('operaciones.exportar_ventas'):
        return redirect('operaciones:reporte_ventas')
    if request.user.has_perm('operaciones.exportar_inventario'):
        return redirect('operaciones:reporte_inventario')
    raise PermissionDenied


def _reporte(request, tipo):
    if not request.user.has_perm(f'operaciones.exportar_{tipo}'):
        raise PermissionDenied
    clase = VentasFiltro if tipo == 'ventas' else InventarioFiltro
    parametros = request.GET.copy()
    if not parametros and tipo == 'ventas':
        parametros.update({'desde': (timezone.localdate() - timedelta(days=29)).isoformat(), 'hasta': timezone.localdate().isoformat()})
    form = clase(parametros)
    formato = request.GET.get('formato', '')
    valido = form.is_valid()
    if formato not in ('', 'pdf', 'xlsx'):
        form.add_error(None, 'El formato solicitado no está disponible.')
        valido = False
    contexto = {'form': form, 'tipo': tipo, 'titulo': 'Reporte de ventas' if tipo == 'ventas' else 'Reporte de inventario',
        'cabeceras': columnas(tipo), 'max_export': MAX_EXPORT_ROWS}
    status = 200
    if valido:
        try:
            qs = consulta(tipo, form.cleaned_data)
            if formato:
                registros = list(qs[:MAX_EXPORT_ROWS + 1])
                if len(registros) > MAX_EXPORT_ROWS:
                    form.add_error(None, f'El reporte supera {MAX_EXPORT_ROWS} filas. Acota los filtros antes de exportar.')
                    status = 400
                else:
                    datos = filas(tipo, registros)
                    totales = {'filas': len(registros), 'envases': sum(r.cantidad for r in registros),
                        'total': sum((r.importe for r in registros), Decimal('0')) if tipo == 'ventas' else None}
                    ahora = timezone.localtime()
                    opciones = dict(titulo=contexto['titulo'], cabeceras=columnas(tipo), datos=datos,
                        filtros=descripcion_filtros(form.cleaned_data), generado=ahora.strftime('%d/%m/%Y %H:%M:%S'),
                        usuario=request.user.get_username(), totales=totales, tipo=tipo)
                    archivo = generar_pdf(**opciones) if formato == 'pdf' else generar_excel(**opciones)
                    EventoReporte.objects.create(usuario=request.user, tipo=tipo, formato=formato,
                        filtros={k: v.isoformat() if hasattr(v, 'isoformat') else v for k, v in form.cleaned_data.items()},
                        filas=totales['filas'], total=totales['total'])
                    mime = 'application/pdf' if formato == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    respuesta = HttpResponse(archivo, content_type=mime)
                    respuesta['Content-Disposition'] = f'attachment; filename="{tipo}-{ahora:%Y%m%d-%H%M%S}.{formato}"'
                    respuesta['Cache-Control'] = 'private, no-store'
                    respuesta['X-Content-Type-Options'] = 'nosniff'
                    return respuesta
            if not form.errors:
                totales = resumen(tipo, qs)
                pagina = Paginator(qs, 20).get_page(request.GET.get('pagina'))
                contexto.update(totales=totales, pagina=pagina,
                    filas_pantalla=[[visible(v) for v in fila] for fila in filas(tipo, pagina.object_list)],
                    filtro_texto=descripcion_filtros(form.cleaned_data))
        except (DatabaseError, ImportError):
            logger.error('No se pudo consultar o generar el reporte solicitado.')
            form.add_error(None, 'No pudimos generar el reporte. Inténtalo nuevamente cuando el servicio esté disponible.')
            status = 503
    else:
        status = 400
    params = parametros.copy()
    params.pop('pagina', None)
    params.pop('formato', None)
    contexto['params'] = params.urlencode()
    respuesta = render(request, 'operaciones/reportes.html', contexto, status=status)
    respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


@login_required
def ventas(request):
    return _reporte(request, 'ventas')


@login_required
def inventario(request):
    return _reporte(request, 'inventario')
