from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from django.http import FileResponse,Http404
from django.shortcuts import redirect,get_object_or_404
from config.respuestas import render
from django.views.decorators.http import require_POST
from .models import *
from .forms import *
from .services import *
from config.respuestas import id_numerico

@login_required
@permission_required('clinica.view_receta',raise_exception=True)
def recetas(request):
    qs=Receta.objects.select_related('paciente','prescriptor')
    q=request.GET.get('q','').strip()
    if q: qs=qs.filter(models.Q(paciente__nombre__icontains=q)|models.Q(paciente__identificador__icontains=q))
    return render(request,'clinica/recetas.html',{'recetas':qs[:200],'q':q})

@login_required
@permission_required('clinica.gestionar_clinica',raise_exception=True)
def receta_crear(request):
    form=RecetaForm(request.POST or None); lineas=LineasFormSet(request.POST or None)
    if request.method=='POST' and form.is_valid() and lineas.is_valid():
        with transaction.atomic():
            receta=form.save(); lineas.instance=receta; lineas.save()
            EventoClinico.objects.create(receta=receta,usuario=request.user,accion='creacion')
        messages.success(request,'Receta registrada, pendiente de revisión QF.')
        return redirect('clinica:receta_detalle',pk=receta.pk)
    return render(request,'clinica/form.html',{'form':form,'lineas':lineas,'titulo':'Registrar receta'})

@login_required
@permission_required('clinica.view_receta',raise_exception=True)
def receta_detalle(request,pk):
    receta=get_object_or_404(Receta,pk=pk)
    form=AdjuntoForm()
    if request.method=='POST':
        accion=request.POST.get('accion')
        try:
            if accion=='revisar': revisar_receta(usuario=request.user,receta=receta,aprobar=request.POST.get('decision')=='aprobar',nota=request.POST.get('nota',''))
            elif accion=='autorizar':
                producto=get_object_or_404(LineaReceta,receta=receta,pk=request.POST.get('linea')).producto
                try: cantidad=int(request.POST.get('cantidad',''))
                except ValueError: raise ValidationError('Indica una cantidad entera.')
                autorizar_controlado(usuario=request.user,receta=receta,producto=producto,cantidad=cantidad)
            elif accion=='adjunto':
                form=AdjuntoForm(request.POST,request.FILES)
                if not form.is_valid(): raise ValidationError('Selecciona un archivo válido.')
                subir_adjunto(usuario=request.user,receta=receta,archivo=form.cleaned_data['archivo'])
            elif accion=='revisar_adjunto':
                exigir_qf(request.user,'revisar_receta')
                adjunto=get_object_or_404(AdjuntoReceta,pk=request.POST.get('adjunto'),receta=receta)
                adjunto.estado='revisado' if request.POST.get('decision')=='aprobar' else 'rechazado'
                adjunto.revisado_por=request.user; adjunto.save(update_fields=['estado','revisado_por'])
                EventoClinico.objects.create(receta=receta,usuario=request.user,accion='revision_adjunto',detalle={'adjunto':adjunto.pk,'estado':adjunto.estado})
            else: raise ValidationError('Acción desconocida.')
            messages.success(request,'Acción registrada.')
            return redirect('clinica:receta_detalle',pk=pk)
        except ValidationError as exc: messages.error(request,' '.join(exc.messages))
    return render(request,'clinica/detalle.html',{'receta':receta,'form':form,'es_qf':request.user.groups.filter(name='Químico Farmacéutico').exists()})

@login_required
@permission_required('clinica.gestionar_clinica',raise_exception=True)
def personas(request,tipo='paciente'):
    clase,formulario=(Paciente,PacienteForm) if tipo=='paciente' else (Prescriptor,PrescriptorForm)
    objeto=get_object_or_404(clase,pk=id_numerico(request.GET['editar'])) if request.GET.get('editar') else None
    form=formulario(request.POST or None,instance=objeto)
    if request.method=='POST' and form.is_valid():
        form.save(); messages.success(request,'Registro guardado.'); return redirect(request.path)
    return render(request,'clinica/personas.html',{'form':form,'registros':clase.objects.order_by('nombre'),'titulo':'Pacientes y retirantes' if tipo=='paciente' else 'Prescriptores'})

@login_required
@permission_required('clinica.descargar_adjunto',raise_exception=True)
def descargar(request,pk):
    adjunto=get_object_or_404(AdjuntoReceta,pk=pk)
    if adjunto.estado=='rechazado': raise Http404('Documento rechazado.')
    response=FileResponse(adjunto.archivo.open('rb'),as_attachment=True,filename=adjunto.nombre,content_type='application/octet-stream')
    response['Cache-Control']='private, no-store'; response['X-Content-Type-Options']='nosniff'
    EventoClinico.objects.create(receta=adjunto.receta,usuario=request.user,accion='descarga_adjunto',detalle={'adjunto':adjunto.pk})
    return response

@login_required
@permission_required('clinica.view_entrega',raise_exception=True)
def imprimir(request,pk):
    return render(request,'clinica/imprimir.html',{'entrega':get_object_or_404(Entrega,pk=pk)})

@login_required
@permission_required('clinica.view_asientocontrolado',raise_exception=True)
def controlados(request):
    if request.method=='POST':
        try: compensar_asiento(usuario=request.user,asiento_id=id_numerico(request.POST.get('asiento'),AsientoControlado.DoesNotExist),motivo=request.POST.get('motivo',''))
        except (ValidationError,AsientoControlado.DoesNotExist) as exc: messages.error(request,' '.join(exc.messages) if isinstance(exc,ValidationError) else 'Asiento inexistente.')
        else: messages.success(request,'Compensación registrada. El original permanece; esta corrección no revierte la entrega ni el stock.')
        return redirect('clinica:controlados')
    return render(request,'clinica/controlados.html',{'asientos':AsientoControlado.objects.select_related('producto','profesional','entrega')[:300]})
