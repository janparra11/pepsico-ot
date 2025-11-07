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
