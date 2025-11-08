from django.http import HttpResponse
from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from ot.models import OrdenTrabajo, PausaOT, EstadoOT
from core.models import Notificacion

@login_required
def home(request):
    user = request.user
    now = timezone.now()
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hace_7 = now - timedelta(days=7)

    # KPIs livianos (rápidos)
    kpi_activas = OrdenTrabajo.objects.filter(activa=True).count()
    kpi_en_pausa = (
        OrdenTrabajo.objects.filter(activa=True, pausas__fin__isnull=True)
        .distinct().count()
    )
    kpi_creadas_hoy = OrdenTrabajo.objects.filter(fecha_ingreso__gte=hoy_inicio).count()

    # Listados cortos (últimas 5)
    ultimas_ots = (
        OrdenTrabajo.objects
        .order_by("-fecha_ingreso")
        .only("id", "folio", "estado_actual", "fecha_ingreso")
    )[:5]

    ultimas_notifs = (
        Notificacion.objects
        .filter(destinatario=user)
        .order_by("-creada_en")
    )[:5]

    notif_unread = Notificacion.objects.filter(destinatario=user, leida=False).count()

    ctx = {
        "username": user.get_username(),

        # KPIs
        "kpi_activas": kpi_activas,
        "kpi_en_pausa": kpi_en_pausa,
        "kpi_creadas_hoy": kpi_creadas_hoy,
        "notif_unread": notif_unread,

        # Listas
        "ultimas_ots": ultimas_ots,
        "ultimas_notifs": ultimas_notifs,
        "now": timezone.now(),

        # Flags para accesos (luego se conectan a roles)
        "can_registrar_ingreso": True,
        "can_ver_ots": True,
        "can_ver_dashboard": True,
        "can_ver_notifs": True,

        # Choices para render amigable
        "estado_choices_dict": dict(EstadoOT.choices),
    }
    return render(request, "core/home.html", ctx)

def healthcheck(request):
    return HttpResponse("OK", content_type="text/plain")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Notificacion

@login_required
def notificaciones_lista(request):
    qs = Notificacion.objects.filter(destinatario=request.user).order_by("-creada_en")
    return render(request, "core/notificaciones.html", {"items": qs})

@login_required
def notificacion_marcar_leida(request, notif_id):
    n = get_object_or_404(Notificacion, id=notif_id, destinatario=request.user)
    n.leida = True
    n.save()
    # Si tiene URL asociada, redirige allá, si no, vuelve a la lista
    return redirect(n.url or "core_notificaciones")

@login_required
def notificaciones_marcar_todas_leidas(request):
    Notificacion.objects.filter(destinatario=request.user, leida=False).update(leida=True)
    return redirect("core_notificaciones")

@login_required
def notificacion_detalle(request, notif_id):
    n = get_object_or_404(Notificacion, id=notif_id, destinatario=request.user)
    if not n.leida:
        n.leida = True
        n.save()
    return render(request, "core/notificacion_detalle.html", {"n": n})

# core/views.py
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.db import models
from .models import EventoAgenda

@login_required
def agenda_view(request):
    return render(request, "core/agenda.html")

@login_required
def agenda_events_api(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    qs = EventoAgenda.objects.all()
    if start and end:
        qs = qs.filter(inicio__lte=end).filter(models.Q(fin__gte=start) | models.Q(fin__isnull=True))

    items = []
    for e in qs.select_related("ot", "asignado_a"):
        ev = {
            "id": e.id,
            "title": e.titulo,                       # título limpio
            "start": e.inicio.isoformat(),
            "end": e.fin.isoformat() if e.fin else None,
            "allDay": e.todo_el_dia,
            # Datos extra para el modal (no rompen el calendario)
            "extendedProps": {
                "descripcion": e.descripcion or "",
                "ot_id": e.ot_id,
                "ot_folio": (e.ot.folio if e.ot_id else ""),
                "asignado": (e.asignado_a.get_username() if e.asignado_a_id else ""),
            }
        }
        # Sólo agrega url si hay OT
        if e.ot_id:
            ev["url"] = f"/ot/{e.ot_id}/"
        items.append(ev)

    return JsonResponse(items, safe=False)

from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.dateparse import parse_datetime

@login_required
@csrf_exempt
def agenda_crear_api(request):
    if request.method != "POST":
        return JsonResponse({"error":"Método no permitido"}, status=405)

    data = json.loads(request.body.decode("utf-8"))
    titulo = data.get("titulo") or ""
    inicio = parse_datetime(data.get("inicio") or "")
    fin = parse_datetime(data.get("fin") or "")
    todo = bool(data.get("todo_el_dia", False))
    descripcion = data.get("descripcion") or ""
    ot_id = data.get("ot_id")

    if not titulo or not inicio:
        return JsonResponse({"error":"Faltan título o inicio"}, status=400)

    e = EventoAgenda.objects.create(
        titulo=titulo,
        inicio=inicio,
        fin=fin if not todo else None,
        todo_el_dia=todo,
        descripcion=descripcion,
        ot_id=ot_id if ot_id else None,
        asignado_a=request.user
    )
    return JsonResponse({"ok": True, "id": e.id})

@login_required
@csrf_exempt
def agenda_detalle_api(request, ev_id):
    try:
        e = EventoAgenda.objects.get(id=ev_id)
    except EventoAgenda.DoesNotExist:
        return JsonResponse({"error":"No existe"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "id": e.id,
            "titulo": e.titulo,
            "inicio": e.inicio.isoformat(),
            "fin": e.fin.isoformat() if e.fin else "",
            "todo_el_dia": e.todo_el_dia,
            "descripcion": e.descripcion or "",
            "ot_id": e.ot_id,
            "ot_folio": (e.ot.folio if e.ot_id else "")
        })

    if request.method == "PUT":
        data = json.loads(request.body.decode("utf-8"))
        e.titulo = data.get("titulo") or e.titulo
        e.inicio = parse_datetime(data.get("inicio") or e.inicio.isoformat())
        fin = data.get("fin")
        e.fin = parse_datetime(fin) if fin else None
        e.todo_el_dia = bool(data.get("todo_el_dia", e.todo_el_dia))
        e.descripcion = data.get("descripcion") or ""
        e.ot_id = data.get("ot_id") or None
        e.asignado_a = request.user
        e.save()
        return JsonResponse({"ok": True})

    if request.method == "DELETE":
        e.delete()
        return JsonResponse({"ok": True})

    return JsonResponse({"error":"Método no permitido"}, status=405)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def notif_unread_count(request):
    from core.models import Notificacion
    count = Notificacion.objects.filter(destinatario=request.user, leida=False).count()
    return JsonResponse({"count": count})
