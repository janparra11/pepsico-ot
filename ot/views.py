from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from django.views.decorators.http import require_POST
from .services import cambiar_estado, iniciar_pausa, finalizar_pausa

from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden

from core.services import notificar
from datetime import timedelta

from .forms import IngresoForm, CambioEstadoForm, PausaIniciarForm, PausaFinalizarForm, DocumentoForm, PrioridadForm, EstadoVehiculoForm
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT, PausaOT, DocumentoOT, PrioridadOT
from taller.models import Vehiculo, EstadoVehiculo

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q, F
import json

from taller.models import Taller
from .forms import EventoOTForm

from .forms import AsignarMecanicoForm

from core.auth import require_roles
from core.roles import Rol


def generar_folio():
    # folio corto legible; si prefieres secuencial, lo podemos cambiar luego
    from uuid import uuid4
    return uuid4().hex[:8].upper()

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import IngresoForm
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT
from taller.models import Vehiculo
from core.models import EventoAgenda
# Si tienes el helper notificar, importa así. Si no existe, puedes omitir el try/except más abajo.
# from core.services import notificar

@require_roles(Rol.RECEPCIONISTA, Rol.GUARDIA, Rol.JEFE_TALLER)
@login_required
def ingreso_nuevo(request):
    if request.method == "POST":
        form = IngresoForm(request.POST, request.FILES)
        if form.is_valid():
            patente = form.cleaned_data["patente"].strip().upper()
            chofer = (form.cleaned_data.get("chofer") or "").strip()
            tipo   = form.cleaned_data.get("tipo")
            taller = form.cleaned_data["taller"]
            obs    = (form.cleaned_data.get("observaciones") or "").strip()

            with transaction.atomic():
                # Aseguramos creación/actualización del vehículo
                veh, _ = Vehiculo.objects.select_for_update().get_or_create(
                    patente=patente,
                    defaults={"tipo": tipo}
                )
                if tipo and veh.tipo_id != tipo.id:
                    veh.tipo = tipo
                    veh.save(update_fields=["tipo"])

                # Regla: solo una OT ACTIVA por vehículo
                ot_activa = OrdenTrabajo.objects.filter(vehiculo=veh, activa=True).first()
                if ot_activa:
                    messages.warning(
                        request,
                        f"Ya existe una OT activa para {veh.patente} (OT {ot_activa.folio})."
                    )
                    return redirect("ot_detalle", ot_id=ot_activa.id)

                # Crear OT
                ot = OrdenTrabajo.objects.create(
                    folio=generar_folio(),
                    vehiculo=veh,
                    taller=taller,
                    estado_actual=EstadoOT.INGRESADO,
                    activa=True,
                    chofer=chofer,
                )

                # Primer registro de historial (usa obs del ingreso si corresponde)
                HistorialEstadoOT.objects.create(
                    ot=ot,
                    estado=EstadoOT.INGRESADO,
                    observaciones=obs
                )

                # Evento en Agenda (ingreso)
                EventoAgenda.objects.create(
                    titulo=f"Ingreso OT {ot.folio}",
                    inicio=ot.fecha_ingreso,
                    ot=ot,
                    asignado_a=request.user if request.user.is_authenticated else None
                )

                # Notificación opcional al usuario actual
                try:
                    from core.services import notificar
                    if request.user.is_authenticated:
                        notificar(
                            destinatario=request.user,
                            titulo=f"OT creada: {ot.folio}",
                            mensaje=f"Se creó la OT {ot.folio} para {veh.patente} en {taller.nombre}.",
                            url=f"/ot/{ot.id}/"
                        )
                except Exception:
                    # Si no tienes `notificar`, o falla, seguimos sin romper el flujo
                    pass

            messages.success(request, f"OT {ot.folio} creada correctamente.")
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
    evento_form = EventoOTForm()
    eventos_ot = ot.eventos.order_by("-inicio")[:10] 
    asignar_mec_form = AsignarMecanicoForm(initial={"mecanico": ot.mecanico_asignado})

    return render(
        request, "ot/ot_detalle.html",
        {
            "ot": ot, "historial": historial, "pausas": pausas,
            "estado_choices": estado_choices, "pausa_abierta": pausa_abierta,
            "doc_form": doc_form, "prioridad_form": prioridad_form, "estado_veh_form": estado_veh_form,
            "evento_form": evento_form,
            "eventos_ot": eventos_ot,
            "asignar_mec_form": asignar_mec_form,
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
@require_roles(Rol.MECANICO, Rol.JEFE_TALLER)
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
@require_roles(Rol.MECANICO)
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

@require_roles(Rol.MECANICO)
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

@require_roles(Rol.RECEPCIONISTA, Rol.MECANICO, Rol.JEFE_TALLER)
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

@require_roles(Rol.JEFE_TALLER)
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

@require_roles(Rol.JEFE_TALLER, Rol.SUPERVISOR)
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

@require_roles(Rol.JEFE_TALLER)
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

@require_roles(Rol.RECEPCIONISTA, Rol.GUARDIA, Rol.JEFE_TALLER, Rol.MECANICO, Rol.ASISTENTE_REPUESTO, Rol.SUPERVISOR)
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

@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER)
@login_required
def dashboard(request):
    now = timezone.now()
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)


    # 1) Conteos por estado (solo activas)
    por_estado = (
        OrdenTrabajo.objects
        .filter(activa=True)
        .values("estado_actual")
        .annotate(total=Count("id"))
    )
    estados_labels = [dict(EstadoOT.choices).get(row["estado_actual"], row["estado_actual"]) for row in por_estado]
    estados_data = [row["total"] for row in por_estado]

    # 2) Conteos por prioridad (solo activas)
    por_prioridad = (
        OrdenTrabajo.objects
        .filter(activa=True)
        .values("prioridad")
        .annotate(total=Count("id"))
    )
    prioridades_labels = [dict(PrioridadOT.choices).get(row["prioridad"], row["prioridad"]) for row in por_prioridad]
    prioridades_data = [row["total"] for row in por_prioridad]

    # 3) OTs por taller (activas)
    por_taller = (
        OrdenTrabajo.objects
        .filter(activa=True)
        .values("taller__nombre")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    talleres_labels = [row["taller__nombre"] for row in por_taller]
    talleres_data = [row["total"] for row in por_taller]

    # 4) Tiempo de ciclo promedio (OTs cerradas últimos 90 días)
    hace_90 = now - timedelta(days=90)
    cerradas = OrdenTrabajo.objects.filter(activa=False, fecha_cierre__gte=hace_90, fecha_cierre__isnull=False)
    # calculamos en Python para compatibilidad total
    duraciones_horas = []
    for ot in cerradas.only("fecha_ingreso", "fecha_cierre"):
        diff = (ot.fecha_cierre - ot.fecha_ingreso).total_seconds() / 3600.0
        if diff >= 0:
            duraciones_horas.append(diff)
    ciclo_promedio_horas = round(sum(duraciones_horas) / len(duraciones_horas), 2) if duraciones_horas else 0.0

    # 5) % OTs en pausa (activas con una pausa abierta)
    ots_con_pausa = (
        OrdenTrabajo.objects
        .filter(activa=True, pausas__fin__isnull=True)
        .distinct()
        .count()
    )
    activas_total = OrdenTrabajo.objects.filter(activa=True).count() or 1
    porcentaje_pausa = round(100.0 * ots_con_pausa / activas_total, 1)

    # 6) Motivos de pausa top 5 (últimos 30 días)
    hace_30 = now - timedelta(days=30)
    motivos = (
        PausaOT.objects
        .filter(inicio__gte=hace_30)
        .values("motivo")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    motivos_labels = [row["motivo"] or "(sin motivo)" for row in motivos]
    motivos_data = [row["total"] for row in motivos]

    finalizados_hoy = OrdenTrabajo.objects.filter(
        activa=False,
        fecha_cierre__gte=hoy_inicio
    ).count()

    ctx = {
        # KPIs
        "kpi_activas": activas_total if activas_total != 1 else OrdenTrabajo.objects.filter(activa=True).count(),
        "kpi_en_pausa": ots_con_pausa,
        "kpi_pct_pausa": porcentaje_pausa,
        "kpi_ciclo_promedio": ciclo_promedio_horas,
        "kpi_finalizados_hoy": finalizados_hoy,

        # Charts
        "chart_estados_labels": json.dumps(estados_labels),
        "chart_estados_data": json.dumps(estados_data),
        "chart_prioridades_labels": json.dumps(prioridades_labels),
        "chart_prioridades_data": json.dumps(prioridades_data),
        "chart_talleres_labels": json.dumps(talleres_labels),
        "chart_talleres_data": json.dumps(talleres_data),
        "chart_motivos_labels": json.dumps(motivos_labels),
        "chart_motivos_data": json.dumps(motivos_data),
    }
    return render(request, "ot/dashboard.html", ctx)

from core.models import EventoAgenda
from .forms import EventoOTForm

@require_POST
def ot_agendar_evento(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    form = EventoOTForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Formulario de evento inválido.")
        return redirect("ot_detalle", ot_id=ot.id)

    titulo = form.cleaned_data["titulo"]
    fecha = form.cleaned_data["fecha"]

    EventoAgenda.objects.create(
        titulo=f"{titulo} (OT {ot.folio})",
        inicio=fecha,
        ot=ot,
        asignado_a=request.user if request.user.is_authenticated else None
    )
    messages.success(request, "Evento agendado correctamente.")
    return redirect("ot_detalle", ot_id=ot.id)

@require_roles(Rol.JEFE_TALLER, Rol.SUPERVISOR)
@require_POST
def ot_asignar_mecanico(request, ot_id):
    ot = get_object_or_404(OrdenTrabajo, id=ot_id)
    if not ot.activa:
        messages.error(request, "La OT está cerrada. No puedes asignar mecánico.")
        return redirect("ot_detalle", ot_id=ot.id)

    form = AsignarMecanicoForm(request.POST)
    if form.is_valid():
        ot.mecanico_asignado = form.cleaned_data["mecanico"]
        ot.save()
        messages.success(request, "Mecánico asignado correctamente.")
    else:
        messages.error(request, "Formulario inválido al asignar mecánico.")
    return redirect("ot_detalle", ot_id=ot.id)


