import json, uuid
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from config.respuestas import id_numerico, render
from django.http import JsonResponse
from django.utils import timezone
from catalogo.models import Producto
from .models import Caja, Convenio, Documento
from .services import abrir_caja, mover_caja, cerrar_caja, resumen_caja, confirmar_venta, emitir_documento, guardar_convenio

class ConvenioForm(forms.ModelForm):
    class Meta:
        model=Convenio
        fields=['nombre','inicio','fin','porcentaje','tope','activo']
        widgets={'inicio':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'),'fin':forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d')}
    def clean(self):
        datos=super().clean()
        if datos.get('inicio') and datos.get('fin') and datos['fin']<datos['inicio']:
            self.add_error('fin','La fecha de término no puede ser anterior a la de inicio.')
        return datos

@permission_required('operaciones.add_venta',raise_exception=True)
def buscar(request):
    from gestion.services import precio_vigente
    q=request.GET.get('q','').strip()
    productos=Producto.objects.filter(activo=True).filter(Q(nombre__icontains=q)|Q(codigo__icontains=q)|Q(barras=q))[:20] if q else []
    return JsonResponse({'productos':[dict(id=p.pk,nombre=p.nombre,codigo=p.codigo,barras=p.barras,precio=str(precio_vigente(p)),condicion=p.condicion) for p in productos]})

@permission_required('operaciones.add_venta',raise_exception=True)
def pos(request):
    data=request.POST if request.method=='POST' else {}
    if request.method=='POST':
        try:
            venta=confirmar_venta(usuario=request.user,items=json.loads(data.get('items','[]')),clave=uuid.UUID(data.get('clave','')),caja_id=int(data.get('caja_id','0')),medio=data.get('medio'),convenio_id=int(data['convenio']) if data.get('convenio') else None,descuento=data.get('descuento','0'),receta_id=int(data['receta']) if data.get('receta') else None,retirante_id=int(data['retirante']) if data.get('retirante') else None,autorizacion_retiro=data.get('autorizacion',''),tipo_documento=data.get('tipo_documento','boleta'),receptor=data.get('receptor',''),rut=data.get('rut',''))
            messages.success(request,'Venta confirmada. El documento se emite por separado.')
            return redirect('comercio:documento',pk=venta.documento.pk)
        except (ValidationError,ValueError,TypeError,ObjectDoesNotExist) as exc: messages.error(request,'; '.join(exc.messages) if isinstance(exc,ValidationError) else 'Revisa los datos de la venta y las referencias seleccionadas.')
    return render(request,'comercio/pos.html',{'caja':Caja.objects.filter(usuario=request.user,cierre__isnull=True).first(),'convenios':Convenio.objects.filter(activo=True,inicio__lte=timezone.localdate(),fin__gte=timezone.localdate()),'clave':data.get('clave') or uuid.uuid4(),'datos':data,'items_iniciales':data.get('items','[]')})

@permission_required('comercio.operar_caja',raise_exception=True)
def caja(request):
    if request.method=='POST':
        try:
            accion=request.POST.get('accion')
            if accion=='abrir': abrir_caja(usuario=request.user,fondo=request.POST.get('fondo'))
            elif accion=='mover': mover_caja(usuario=request.user,caja_id=int(request.POST['caja_id']),tipo=request.POST.get('tipo'),monto=request.POST.get('monto'),motivo=request.POST.get('motivo',''),clave=uuid.UUID(request.POST['clave']))
            elif accion=='cerrar': cerrar_caja(usuario=request.user,caja_id=int(request.POST['caja_id']),contado=request.POST.get('contado'),motivo=request.POST.get('motivo',''))
            else: raise ValidationError('Operación inválida.')
            messages.success(request,'Operación de caja registrada.')
            return redirect('comercio:caja')
        except (ValidationError,ValueError,KeyError,ObjectDoesNotExist) as exc: messages.error(request,'; '.join(exc.messages) if isinstance(exc,ValidationError) else 'Datos de caja inválidos.')
    actual=Caja.objects.filter(usuario=request.user,cierre__isnull=True).first()
    return render(request,'comercio/caja.html',{'caja':actual,'resumen':resumen_caja(actual) if actual else None,'historial':Caja.objects.filter(usuario=request.user,cierre__isnull=False).order_by('-pk')[:20],'clave':uuid.uuid4()})

@permission_required('comercio.view_convenio',raise_exception=True)
def convenios(request):
    seleccionado=get_object_or_404(Convenio,pk=id_numerico(request.GET['editar'])) if request.GET.get('editar') else None
    form=ConvenioForm(request.POST or None,instance=seleccionado)
    if request.method=='POST':
        from django.core.exceptions import PermissionDenied
        if not request.user.has_perm('comercio.change_convenio' if seleccionado else 'comercio.add_convenio'): raise PermissionDenied
        if form.is_valid():
            guardar_convenio(usuario=request.user,datos=form.cleaned_data,convenio_id=seleccionado.pk if seleccionado else None)
            messages.success(request,'Convenio guardado.'); return redirect('comercio:convenios')
    return render(request,'comercio/convenios.html',{'form':form,'convenios':Convenio.objects.order_by('nombre'),'editando':seleccionado})

@permission_required('operaciones.view_venta',raise_exception=True)
def documento(request,pk):
    doc=get_object_or_404(Documento.objects.select_related('venta__cobro'),pk=pk)
    if request.method=='POST':
        emitir_documento(usuario=request.user,documento_id=pk,simular_error=request.POST.get('accion')=='simular_error')
        return redirect('comercio:documento',pk=pk)
    return render(request,'comercio/documento.html',{'doc':doc})
