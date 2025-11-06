from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from django.views.decorators.http import require_POST
from .services import cambiar_estado, iniciar_pausa, finalizar_pausa

from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden

from core.services import notificar
from django.utils import timezone
from datetime import timedelta

from .forms import IngresoForm, CambioEstadoForm, PausaIniciarForm, PausaFinalizarForm, DocumentoForm, PrioridadForm, EstadoVehiculoForm
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT, PausaOT, DocumentoOT, PrioridadOT
from taller.models import Vehiculo, EstadoVehiculo


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

                # Notificar al usuario actual (si está logueado)
                if request.user.is_authenticated:
                    notificar(
                        destinatario=request.user,
                        titulo=f"OT creada: {ot.folio}",
                        mensaje=f"Se creó la OT {ot.folio} para el vehículo {ot.vehiculo.patente} en {ot.taller.nombre}.",
                        url=f"/ot/{ot.id}/"
                    )

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
    pausa_abierta = ot.pausas.filter(fin__isnull=True).order_by("-inicio").first()

    doc_form = DocumentoForm()
    prioridad_form = PrioridadForm(initial={"prioridad": ot.prioridad})
    estado_veh_form = EstadoVehiculoForm(initial={"estado": ot.vehiculo.estado})

    return render(
        request, "ot/ot_detalle.html",
        {
            "ot": ot, "historial": historial, "pausas": pausas,
            "estado_choices": estado_choices, "pausa_abierta": pausa_abierta,
            "doc_form": doc_form, "prioridad_form": prioridad_form, "estado_veh_form": estado_veh_form
        }
    )

    # alarma simple v1: si hay pausa abierta > 30 min, crear notificación (una por visita)
    if pausa_abierta:
        limite = timezone.now() - timedelta(minutes=30)  # ajusta a gusto
        if pausa_abierta.inicio < limite and request.user.is_authenticated:
            # Puedes mejorar: guardar un flag para no duplicar. Para v1, basta.
            notificar(
                destinatario=request.user,
                titulo=f"Alerta: Pausa prolongada en OT {ot.folio}",
                mensaje=f"La pausa iniciada a las {pausa_abierta.inicio} superó los 30 minutos.",
                url=f"/ot/{ot.id}/"
            )

    doc_form = DocumentoForm()

    return render(
        request,
        "ot/ot_detalle.html",
        {
            "ot": ot,
            "historial": historial,
            "pausas": pausas,
            "estado_choices": estado_choices,
            "pausa_abierta": pausa_abierta,
            "doc_form": doc_form,  # ← nuevo
        },
    )

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
        if request.user.is_authenticated:
            notificar(
                destinatario=request.user,
                titulo=f"Pausa iniciada en OT {ot.folio}",
                mensaje=f"Motivo: {motivo}",
                url=f"/ot/{ot.id}/"
            )
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
        if request.user.is_authenticated:
            notificar(
                destinatario=request.user,
                titulo=f"Pausa finalizada en OT {ot.folio}",
                mensaje=f"Se cerró la pausa abierta.",
                url=f"/ot/{ot.id}/"
            )
    except ValueError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Ocurrió un error al finalizar la pausa.")
    return redirect("ot_detalle", ot_id=ot.id)

@require_POST
def ot_subir_documento(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No puedes adjuntar documentos.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = DocumentoForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "; ".join([str(e) for e in form.errors.get("__all__", [])]))
        for campo, errs in form.errors.items():
            if campo != "__all__":
                messages.error(request, f"{campo}: {', '.join(errs)}")
        return redirect("ot_detalle", ot_id=ot.id)

    try:
        doc = DocumentoOT(
            ot=ot,
            archivo=form.cleaned_data["archivo"],
            tipo=form.cleaned_data.get("tipo", "") or "",
            creado_por=request.user if request.user.is_authenticated else None
        )
        # Ejecuta clean() del modelo (valida tamaño/MIME/ext)
        doc.full_clean()
        doc.save()
        messages.success(request, "Documento subido correctamente.")
        if request.user.is_authenticated:
            notificar(
                destinatario=request.user,
                titulo=f"Documento agregado en OT {ot.folio}",
                mensaje=f"Tipo: {doc.tipo or '(sin tipo)'} · Archivo: {doc.archivo.name}",
                url=f"/ot/{ot.id}/"
            )
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    except Exception:
        messages.error(request, "Ocurrió un error al subir el documento.")
    return redirect("ot_detalle", ot_id=ot.id)


@require_POST
def ot_eliminar_documento(request, ot_id, doc_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    doc = get_object_or_404(DocumentoOT, id=doc_id, ot=ot)

    # (Simple) Autorización: sólo si la OT está activa. Puedes endurecer por rol/propiedad.
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No puedes eliminar documentos.")
        return redirect("ot_detalle", ot_id=ot.id)

    try:
        # Borra el archivo del storage y el registro
        doc.archivo.delete(save=False)
        doc.delete()
        messages.success(request, "Documento eliminado.")
        if request.user.is_authenticated:
            notificar(
                destinatario=request.user,
                titulo=f"Documento eliminado en OT {ot.folio}",
                mensaje=f"Tipo: {doc.tipo or '(sin tipo)'} · Archivo: {doc.archivo.name}",
                url=f"/ot/{ot.id}/"
            )
    except Exception:
        messages.error(request, "No se pudo eliminar el documento.")
    return redirect("ot_detalle", ot_id=ot.id)

@require_POST
def ot_cambiar_prioridad(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No puedes cambiar la prioridad.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = PrioridadForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario de prioridad inválido.")
        return redirect("ot_detalle", ot_id=ot.id)

    nueva = int(form.cleaned_data["prioridad"])
    if nueva not in [p.value for p in PrioridadOT]:
        messages.error(request, "Prioridad no válida.")
        return redirect("ot_detalle", ot_id=ot.id)

    ot.prioridad = nueva
    ot.save()
    messages.success(request, f"Prioridad actualizada a {ot.get_prioridad_display()}.")
    # notificación opcional
    if request.user.is_authenticated:
        from core.services import notificar
        notificar(
            destinatario=request.user,
            titulo=f"OT {ot.folio}: Prioridad {ot.get_prioridad_display()}",
            mensaje=f"Se actualizó la prioridad a {ot.get_prioridad_display()}.",
            url=f"/ot/{ot.id}/"
        )
    return redirect("ot_detalle", ot_id=ot.id)


@require_POST
def vehiculo_cambiar_estado(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    form = EstadoVehiculoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario de estado de vehículo inválido.")
        return redirect("ot_detalle", ot_id=ot.id)

    nuevo = form.cleaned_data["estado"]
    if nuevo not in [e.value for e in EstadoVehiculo]:
        messages.error(request, "Estado de vehículo no válido.")
        return redirect("ot_detalle", ot_id=ot.id)

    ot.vehiculo.estado = nuevo
    ot.vehiculo.save()
    messages.success(request, f"Estado del vehículo: {ot.vehiculo.get_estado_display()}.")
    # notificación opcional
    if request.user.is_authenticated:
        from core.services import notificar
        notificar(
            destinatario=request.user,
            titulo=f"Vehículo {ot.vehiculo.patente}: {ot.vehiculo.get_estado_display()}",
            mensaje=f"Estado de vehículo actualizado a {ot.vehiculo.get_estado_display()}.",
            url=f"/ot/{ot.id}/"
        )
    return redirect("ot_detalle", ot_id=ot.id)

from django.core.paginator import Paginator
from django.db.models import Q
from .models import OrdenTrabajo, EstadoOT, PrioridadOT

def ot_lista(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    activa = request.GET.get("activa", "1")  # 1=solo activas por defecto

    qs = OrdenTrabajo.objects.all()

    if activa == "1":
        qs = qs.filter(activa=True)

    if estado:
        qs = qs.filter(estado_actual=estado)

    if q:
        qs = qs.filter(Q(folio__icontains=q) | Q(vehiculo__patente__icontains=q))

    # 🔽 AQUÍ aplicas el orden por prioridad
    qs = qs.order_by("-prioridad", "fecha_ingreso")

    paginator = Paginator(qs, 10)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    return render(request, "ot/ot_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "estado": estado,
        "activa": activa,
        "estado_choices": EstadoOT.choices,
        "prioridad_choices": PrioridadOT.choices,
    })
