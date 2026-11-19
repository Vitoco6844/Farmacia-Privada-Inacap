from datetime import timedelta
from decimal import Decimal
from django import forms
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.http import HttpResponse
from config.respuestas import render
from django.utils import timezone
from catalogo.models import Producto, Categoria
from compras.models import LineaOrden, Proveedor
from .models import DetalleVenta, EventoReporte
from .exportaciones import generar_pdf, generar_excel, visible


class Periodo(forms.Form):
    desde = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    producto = forms.ModelChoiceField(Producto.objects.all(), required=False)
    categoria = forms.ModelChoiceField(Categoria.objects.all(), required=False)

    def clean(self):
        datos = super().clean()
        if datos.get('desde') and datos.get('hasta') and datos['desde'] > datos['hasta']:
            raise forms.ValidationError('La fecha inicial debe ser anterior a la final.')
        return datos


class CompraFiltro(Periodo):
    proveedor = forms.ModelChoiceField(Proveedor.objects.all(), required=False)


def parametros(request):
    datos = request.GET.copy()
    datos.setdefault('desde', (timezone.localdate() - timedelta(days=29)).isoformat())
    datos.setdefault('hasta', timezone.localdate().isoformat())
    return datos


@permission_required('compras.exportar_compras', raise_exception=True)
def compras(request):
    form = CompraFiltro(parametros(request))
    formato = request.GET.get('formato', '')
    contexto = {'form': form, 'titulo': 'Reporte de compras', 'tipo': 'compras', 'max_export': 5000,
                'cabeceras': ['Orden', 'Fecha', 'Proveedor', 'Producto', 'Pedidos', 'Recibidos', 'Total CLP']}
    valido = form.is_valid()
    if formato not in ('', 'pdf', 'xlsx'):
        form.add_error(None, 'Formato desconocido.')
        valido = False
    if valido:
        d = form.cleaned_data
        qs = LineaOrden.objects.select_related('orden', 'producto').filter(orden__fecha__date__gte=d['desde'], orden__fecha__date__lte=d['hasta']).order_by('-orden__fecha', 'pk')
        if d['producto']: qs = qs.filter(producto=d['producto'])
        if d['categoria']: qs = qs.filter(producto__categoria=d['categoria'])
        if d['proveedor']: qs = qs.filter(orden__proveedor=d['proveedor'])
        totales = {'filas': qs.count(), 'envases': qs.aggregate(n=Sum('solicitada'))['n'] or 0}
        filtro = ' · '.join(f'{k}: {v}' for k, v in d.items() if v)
        def filas(registros):
            return [[f'OC-{x.orden_id} ({x.orden.get_estado_display()})', timezone.localtime(x.orden.fecha).replace(tzinfo=None), x.orden.proveedor_nombre, x.nombre, x.solicitada, x.recibida, x.subtotal] for x in registros]
        if formato and totales['filas'] > 5000:
            form.add_error(None, 'Acota los filtros a un máximo de 5000 filas.')
        elif formato:
            datos = filas(qs)
            opciones = dict(titulo=contexto['titulo'], cabeceras=contexto['cabeceras'], datos=datos, filtros=filtro,
                           generado=timezone.localtime().strftime('%d/%m/%Y %H:%M'), usuario=request.user.username, totales=totales, tipo='compras')
            archivo = generar_pdf(**opciones) if formato == 'pdf' else generar_excel(**opciones)
            EventoReporte.objects.create(usuario=request.user, tipo='compras', formato=formato, filtros={k:str(v) for k,v in d.items() if v}, filas=totales['filas'])
            response = HttpResponse(archivo, content_type='application/pdf' if formato == 'pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="compras.{formato}"'
            return response
        else:
            pagina = Paginator(qs, 20).get_page(request.GET.get('pagina'))
            contexto.update(totales=totales, pagina=pagina, filas_pantalla=[[visible(v) for v in fila] for fila in filas(pagina.object_list)], filtro_texto=filtro)
    params = parametros(request)
    params.pop('pagina', None)
    params.pop('formato', None)
    contexto['params'] = params.urlencode()
    return render(request, 'operaciones/reportes.html', contexto, status=400 if form.errors else 200)


@permission_required('operaciones.exportar_ventas', raise_exception=True)
def analisis(request):
    form = Periodo(parametros(request))
    contexto = {'form': form}
    if form.is_valid():
        d = form.cleaned_data
        qs = DetalleVenta.objects.filter(venta__fecha__date__gte=d['desde'], venta__fecha__date__lte=d['hasta'])
        if d['producto']: qs = qs.filter(producto=d['producto'])
        if d['categoria']: qs = qs.filter(producto__categoria=d['categoria'])
        importe = ExpressionWrapper(F('precio_unitario') * F('cantidad'), output_field=DecimalField(max_digits=24, decimal_places=0))
        contexto['filas'] = qs.values('codigo', 'nombre', 'producto__categoria__nombre').annotate(envases=Sum('cantidad'), total=Sum(importe)).order_by('-total')[:100]
        contexto['totales'] = qs.aggregate(envases=Sum('cantidad'), total=Sum(importe))
        contexto['ventas'] = qs.values('venta_id').distinct().count()
        from clinica.models import Receta, Entrega
        recetas = Receta.objects.filter(creada__date__gte=d['desde'], creada__date__lte=d['hasta'])
        entregas = Entrega.objects.filter(fecha__date__gte=d['desde'], fecha__date__lte=d['hasta'])
        if d['producto']:
            recetas = recetas.filter(lineas__producto=d['producto'])
            entregas = entregas.filter(lineas__linea_receta__producto=d['producto'])
        if d['categoria']:
            recetas = recetas.filter(lineas__producto__categoria=d['categoria'])
            entregas = entregas.filter(lineas__linea_receta__producto__categoria=d['categoria'])
        contexto.update(recetas=recetas.distinct().count(), pendientes=recetas.filter(estado='pendiente').distinct().count(), entregas=entregas.distinct().count())
    return render(request, 'operaciones/analisis.html', contexto, status=400 if form.errors else 200)
