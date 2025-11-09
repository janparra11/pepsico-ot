from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.roles import Rol
from core.auth import require_roles

from .models import Repuesto, MovimientoStock
from .forms import (
    RepuestoForm, MovimientoEntradaForm, MovimientoSalidaForm, MovimientoAjusteForm
)

# ---------- Repuestos ----------
@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN, Rol.SUPERVISOR)
def repuesto_list(request):
    q = request.GET.get("q", "").strip()
    qs = Repuesto.objects.all()
    if q:
        qs = qs.filter(descripcion__icontains=q) | qs.filter(codigo__icontains=q)
    return render(request, "inventario/repuesto_list.html", {"items": qs})

@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN)
def repuesto_create(request):
    if request.method == "POST":
        form = RepuestoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Repuesto creado.")
            return redirect("inv_repuesto_list")
    else:
        form = RepuestoForm()
    return render(request, "inventario/repuesto_form.html", {"form": form, "title": "Nuevo repuesto"})

@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN)
def repuesto_edit(request, pk):
    rep = get_object_or_404(Repuesto, pk=pk)
    if request.method == "POST":
        form = RepuestoForm(request.POST, instance=rep)
        if form.is_valid():
            form.save()
            messages.success(request, "Repuesto actualizado.")
            return redirect("inv_repuesto_list")
    else:
        form = RepuestoForm(instance=rep)
    return render(request, "inventario/repuesto_form.html", {"form": form, "title": f"Editar {rep.codigo}"})


# ---------- Movimientos ----------
@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN, Rol.SUPERVISOR)
def mov_list(request):
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    qs = MovimientoStock.objects.select_related("repuesto","ot","creado_por").all()
    if q:
        qs = qs.filter(repuesto__codigo__icontains=q) | qs.filter(repuesto__descripcion__icontains=q) | qs.filter(motivo__icontains=q)
    if tipo in [t for t,_ in MovimientoStock.TIPO_CHOICES]:
        qs = qs.filter(tipo=tipo)
    return render(request, "inventario/mov_list.html", {"items": qs, "tipo": tipo, "TIPOS": MovimientoStock.TIPO_CHOICES})

@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN)
def mov_entrada(request):
    if request.method == "POST":
        form = MovimientoEntradaForm(request.POST)
        if form.is_valid():
            try:
                form.save(user=request.user)
                messages.success(request, "Entrada registrada.")
                return redirect("inv_mov_list")
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = MovimientoEntradaForm()
    return render(request, "inventario/mov_form.html", {"form": form, "title": "Entrada de stock"})

@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN)
def mov_salida(request):
    if request.method == "POST":
        form = MovimientoSalidaForm(request.POST)
        if form.is_valid():
            try:
                form.save(user=request.user)
                messages.success(request, "Salida registrada.")
                return redirect("inv_mov_list")
            except Exception as e:
                messages.error(request, str(e))
    else:
        initial = {}
        ot_id = request.GET.get("ot")
        if ot_id:
            try:
                initial["ot"] = int(ot_id)
            except:
                pass
        form = MovimientoSalidaForm(initial=initial)

    return render(request, "inventario/mov_form.html", {"form": form, "title": "Salida (consumo en OT)"})

@login_required
@require_roles(Rol.ASISTENTE_REPUESTO, Rol.JEFE_TALLER, Rol.ADMIN)
def mov_ajuste(request):
    if request.method == "POST":
        form = MovimientoAjusteForm(request.POST)
        if form.is_valid():
            try:
                form.save(user=request.user)
                messages.success(request, "Ajuste registrado.")
                return redirect("inv_mov_list")
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = MovimientoAjusteForm()
    return render(request, "inventario/mov_form.html", {"form": form, "title": "Ajuste de stock"})
