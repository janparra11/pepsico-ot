from django.http import HttpResponse
from django.shortcuts import render
from core.roles import Rol
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from core.models import Perfil
from django.http import HttpResponse

def healthcheck(request):
    return HttpResponse("OK", content_type="text/plain")

from ot.models import OrdenTrabajo, PausaOT, EstadoOT
from core.models import Notificacion
from django.db.models import Q, Count, F
from core.filters import filter_ots_for_user

from django.db import models
from inventario.models import Repuesto

@login_required
def home(request):
    user = request.user
    now = timezone.now()
    hoy_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 🔹 Rol del usuario (puede ser None si no tiene perfil)
    rol = getattr(getattr(user, "perfil", None), "rol", None)

    # ========= OTs filtradas por rol =========
    # Usamos el mismo filtro que en otros lados para que el mecánico
    # solo vea sus OTs, el guardia las activas, etc.
    qs_base = filter_ots_for_user(OrdenTrabajo.objects.all(), user)

    # 🔹 KPI: Vehículos ingresados hoy (sobre el queryset filtrado)
    kpi_vehiculos_hoy = qs_base.filter(
        fecha_ingreso__gte=hoy_inicio
    ).count()

    # 🔹 KPI: OTs activas
    kpi_activas = qs_base.filter(activa=True).count()

    # 🔹 KPI: OTs en pausa (al menos una pausa abierta)
    kpi_en_pausa = (
        qs_base.filter(activa=True, pausas__fin__isnull=True)
        .distinct()
        .count()
    )

    # 🔹 KPI: Vehículos finalizados (CERRADO, ajusta si tu estado final es otro)
    kpi_vehiculos_finalizados = qs_base.filter(
        activa=False,
        estado_actual=EstadoOT.CERRADO
    ).count()

    # Notificaciones
    notif_unread = Notificacion.objects.filter(
        destinatario=user, leida=False
    ).count()

    # Últimas OTs ya filtradas por rol
    ultimas_ots = qs_base.order_by("-fecha_ingreso")[:5]

    ultimas_notifs = (
        Notificacion.objects
        .filter(destinatario=user)
        .order_by("-creada_en")[:5]
    )

    # ========= PERMISOS POR ROL (para mostrar/ocultar tarjetas) =========
    can_registrar_ingreso = rol in (
        Rol.RECEPCIONISTA,
        Rol.GUARDIA,
        Rol.JEFE_TALLER,
        Rol.ADMIN,
    )

    can_ver_dashboard = rol in (
        Rol.SUPERVISOR,
        Rol.JEFE_TALLER,
        Rol.ADMIN,
    )

    # Ver listado de OTs (mecánico, recepcionista, guardia, jefe, asistente, supervisor, admin)
    can_ver_ots = rol in (
        Rol.RECEPCIONISTA,
        Rol.GUARDIA,
        Rol.JEFE_TALLER,
        Rol.MECANICO,
        Rol.ASISTENTE_REPUESTO,
        Rol.SUPERVISOR,
        Rol.ADMIN,
    )

    # Notificaciones: todos los roles logueados
    can_ver_notifs = True

    ctx = {
        "username": user.get_username(),
        "now": now,

        # KPIs
        "kpi_vehiculos_hoy": kpi_vehiculos_hoy,
        "kpi_activas": kpi_activas,
        "kpi_en_pausa": kpi_en_pausa,
        "kpi_vehiculos_finalizados": kpi_vehiculos_finalizados,
        "notif_unread": notif_unread,

        # Listas
        "ultimas_ots": ultimas_ots,
        "ultimas_notifs": ultimas_notifs,

        # Flags para accesos
        "can_registrar_ingreso": can_registrar_ingreso,
        "can_ver_ots": can_ver_ots,
        "can_ver_dashboard": can_ver_dashboard,
        "can_ver_notifs": can_ver_notifs,

        # Por si lo usas en otros templates
        "estado_choices_dict": dict(EstadoOT.choices),
    }

    return render(request, "core/home.html", ctx)

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

from django.shortcuts import redirect
from .roles import Rol

@login_required
def redir_por_rol(request):
    rol = getattr(getattr(request.user, "perfil", None), "rol", None)
    if rol in (Rol.ADMIN, Rol.SUPERVISOR, Rol.JEFE_TALLER):
        return redirect("ot_dashboard")
    if rol == Rol.GUARDIA:
        return redirect("ingreso_nuevo")
    if rol == Rol.MECANICO:
        return redirect("ot_lista")
    if rol == Rol.ASISTENTE_REPUESTO:
        return redirect("ot_lista")  # luego: módulo inventario
    # default recepcionista
    return redirect("home")


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.crypto import get_random_string

from core.auth import require_roles
from core.roles import Rol
from .forms import UserCreateForm, UserRoleForm, UserStatusForm

@require_roles(Rol.ADMIN)
@login_required
def users_admin_list(request):
    qs = User.objects.select_related("perfil").order_by("username")
    return render(request, "core/users_admin_list.html", {"users": qs})

from core.models import Perfil  # asegúrate de tener este import arriba

@require_roles(Rol.ADMIN)
@login_required
def users_admin_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            u = User(
                username=form.cleaned_data["username"].strip(),
                first_name=form.cleaned_data["first_name"].strip(),
                last_name=form.cleaned_data["last_name"].strip(),
                email=form.cleaned_data["email"].strip(),
                is_active=True,
                password=make_password(form.cleaned_data["password"]),
            )
            u.save()

            # 🔹 Crear Perfil asociado (sin signals)
            Perfil.objects.get_or_create(
                user=u,
                defaults={"rol": form.cleaned_data["rol"]},
            )

            messages.success(request, f"Usuario {u.username} creado correctamente.")
            return redirect("users_admin_list")
    else:
        form = UserCreateForm()

    return render(request, "core/users_admin_create.html", {"form": form})

@require_roles(Rol.ADMIN)
@login_required
def users_admin_set_role(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserRoleForm(request.POST)
        if form.is_valid():
            rol = form.cleaned_data["rol"]
            u.perfil.rol = rol
            u.perfil.save()
            messages.success(request, f"Rol de {u.username} actualizado a {u.perfil.get_rol_display()}.")
            return redirect("users_admin_list")
    else:
        form = UserRoleForm(initial={"rol": getattr(u.perfil, "rol", Rol.RECEPCIONISTA)})
    return render(request, "core/users_admin_set_role.html", {"u": u, "form": form})

@require_roles(Rol.ADMIN)
@login_required
def users_admin_toggle_active(request, user_id):
    u = get_object_or_404(User, id=user_id)
    if request.method == "POST":
        form = UserStatusForm(request.POST)
        if form.is_valid():
            u.is_active = form.cleaned_data["activo"]
            u.save()
            messages.success(request, f"Usuario {u.username} ahora está {'activo' if u.is_active else 'inactivo'}.")
            return redirect("users_admin_list")
    else:
        form = UserStatusForm(initial={"activo": u.is_active})
    return render(request, "core/users_admin_toggle_active.html", {"u": u, "form": form})

@require_roles(Rol.ADMIN)
@login_required
def users_admin_reset_password(request, user_id):
    u = get_object_or_404(User, id=user_id)
    # genera una contraseña temporal segura (12 chars)
    temp_password = get_random_string(12)
    u.password = make_password(temp_password)
    u.save()
    messages.success(request, f"Contraseña temporal de {u.username}: {temp_password}")
    # En producción: enviar por correo, no mostrar en pantalla.
    return redirect("users_admin_list")

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_with_message(request):
    logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")
