from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .forms import IngresoForm
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT
from taller.models import Vehiculo

def generar_folio():
    # folio corto legible; si prefieres secuencial, lo podemos cambiar luego
    from uuid import uuid4
    return uuid4().hex[:8].upper()

def ingreso_nuevo(request):
    if request.method == "POST":
        form = IngresoForm(request.POST)
        if form.is_valid():
            patente = form.cleaned_data["patente"]
            taller = form.cleaned_data["taller"]
            with transaction.atomic():
                veh, _ = Vehiculo.objects.get_or_create(
                    patente=patente,
                    defaults={"marca": "", "modelo": ""}
                )
                # Bloquear duplicidad de OT activa
                if OrdenTrabajo.objects.filter(vehiculo=veh, activa=True).exists():
                    messages.error(request, "Ya existe una OT activa para esta patente.")
                    return redirect("ingreso_nuevo")

                ot = OrdenTrabajo.objects.create(
                    folio=generar_folio(),
                    vehiculo=veh,
                    taller=taller,
                    estado_actual=EstadoOT.INGRESADO,
                    activa=True
                )
                # abrir tramo de historial
                HistorialEstadoOT.objects.create(ot=ot, estado=EstadoOT.INGRESADO)

                messages.success(request, f"Ingreso registrado. OT {ot.folio} creada.")
                return redirect("ot_detalle", ot_id=ot.id)
    else:
        form = IngresoForm()

    return render(request, "ot/ingreso_nuevo.html", {"form": form})

def ot_detalle(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    historial = ot.historial.order_by("-inicio")
    pausas = ot.pausas.order_by("-inicio")
    estado_choices = ot._meta.get_field("estado_actual").choices

    # Pausa abierta si existe una con fin null
    pausa_abierta = ot.pausas.filter(fin__isnull=True).order_by("-inicio").first()

    return render(
        request,
        "ot/ot_detalle.html",
        {
            "ot": ot,
            "historial": historial,
            "pausas": pausas,
            "estado_choices": estado_choices,
            "pausa_abierta": pausa_abierta,  # <- importante
        },
    )


# ot/views.py (agrega imports)
from django.views.decorators.http import require_POST
from .forms import IngresoForm, CambioEstadoForm, PausaIniciarForm, PausaFinalizarForm
from .services import cambiar_estado, iniciar_pausa, finalizar_pausa
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT, PausaOT

# Vista para cambiar estado
@require_POST
def ot_cambiar_estado(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)  # sin activa=True
    if not ot.activa:
        messages.error(request, "La OT está cerrada y no admite más cambios de estado.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = CambioEstadoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario inválido.")
        return redirect("ot_detalle", ot_id=ot.id)

    nuevo_estado = form.cleaned_data["nuevo_estado"]
    try:
        cambiar_estado(ot, nuevo_estado, usuario=request.user if request.user.is_authenticated else None)
        messages.success(request, f"Estado cambiado a {ot.get_estado_actual_display()}.")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Ocurrió un error inesperado al cambiar el estado.")
    return redirect("ot_detalle", ot_id=ot.id)

# Vistas para iniciar/terminar pausa
def pausa_iniciar(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No se pueden iniciar pausas.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = PausaIniciarForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario inválido.")
        return redirect("ot_detalle", ot_id=ot.id)
    motivo = form.cleaned_data["motivo"]
    try:
        iniciar_pausa(ot, motivo)
        messages.success(request, "Pausa iniciada.")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Ocurrió un error al iniciar la pausa.")
    return redirect("ot_detalle", ot_id=ot.id)


@require_POST
def pausa_finalizar(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No se pueden finalizar pausas.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = PausaFinalizarForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario inválido.")
        return redirect("ot_detalle", ot_id=ot.id)
    try:
        finalizar_pausa(ot)
        messages.success(request, "Pausa finalizada.")
    except ValueError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Ocurrió un error al finalizar la pausa.")
    return redirect("ot_detalle", ot_id=ot.id)