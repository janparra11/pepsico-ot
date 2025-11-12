# core/admin_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.conf import settings

from .models import Config, AuditLog, SessionLog
from core.auth import require_roles
from core.roles import Rol

import os, io, zipfile

@login_required
@require_roles(Rol.ADMIN, Rol.JEFE_TALLER, Rol.SUPERVISOR)
def config_view(request):
    cfg = Config.get_solo()
    if request.method == "POST":
        cfg.nombre_taller = request.POST.get("nombre_taller", cfg.nombre_taller).strip()
        cfg.horario = request.POST.get("horario", cfg.horario).strip()
        cfg.contacto = request.POST.get("contacto", cfg.contacto).strip()
        cfg.save()
        messages.success(request, "Configuración actualizada.")
        AuditLog.objects.create(
            app="CORE", action="UPDATE_CONFIG", user=request.user, object_repr=cfg.nombre_taller
        )
        return redirect("core_config")
    return render(request, "core/config.html", {"cfg": cfg})


@login_required
@require_roles(Rol.ADMIN, Rol.JEFE_TALLER, Rol.SUPERVISOR)
def logs_view(request):
    logs = AuditLog.objects.select_related("user")[:200]
    sessions = SessionLog.objects.select_related("user")[:200]
    return render(request, "core/logs.html", {"logs": logs, "sessions": sessions})


@login_required
@require_roles(Rol.ADMIN)
def backup_media_zip(request):
    """
    Comprime la carpeta MEDIA_ROOT y la entrega como descarga.
    Si no hay MEDIA_ROOT o está vacía, devuelve un ZIP con README.
    """
    mem = io.BytesIO()
    base = getattr(settings, "MEDIA_ROOT", None)

    if not base or not os.path.isdir(base):
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", "No hay MEDIA_ROOT configurado o no existen archivos de media.")
        mem.seek(0)
        AuditLog.objects.create(app="CORE", action="EXPORT_MEDIA", user=request.user, extra="empty media")
        return FileResponse(mem, as_attachment=True, filename="media_backup.zip")

    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(base):
            for f in files:
                path = os.path.join(root, f)
                arcname = os.path.relpath(path, base)
                zf.write(path, arcname)

    mem.seek(0)
    AuditLog.objects.create(app="CORE", action="EXPORT_MEDIA", user=request.user)
    return FileResponse(mem, as_attachment=True, filename="media_backup.zip")

# core/admin_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User

from .models import Config, AuditLog, SessionLog
from core.auth import require_roles
from core.roles import Rol
import os, io, zipfile


def _parse_log_filters(request):
    fini = (request.GET.get("fini") or "").strip()   # yyyy-mm-dd
    ffin = (request.GET.get("ffin") or "").strip()   # yyyy-mm-dd
    app  = (request.GET.get("app") or "").strip()
    act  = (request.GET.get("action") or "").strip()
    uid  = (request.GET.get("user") or "").strip()
    qtxt = (request.GET.get("q") or "").strip()

    qs = AuditLog.objects.select_related("user").all()

    if fini:
        qs = qs.filter(ts__date__gte=fini)
    if ffin:
        qs = qs.filter(ts__date__lte=ffin)
    if app:
        qs = qs.filter(app=app)
    if act:
        qs = qs.filter(action=act)
    if uid:
        qs = qs.filter(user_id=uid)
    if qtxt:
        qs = qs.filter(Q(object_repr__icontains=qtxt) | Q(extra__icontains=qtxt))

    return qs, {"fini": fini, "ffin": ffin, "app": app, "action": act, "user": uid, "q": qtxt}


@login_required
@require_roles(Rol.ADMIN, Rol.JEFE_TALLER, Rol.SUPERVISOR)
def logs_view(request):
    # filtros para AuditLog
    qs, filtros = _parse_log_filters(request)

    # opciones para selects (apps y actions más recientes)
    apps = list(AuditLog.objects.order_by().values_list("app", flat=True).distinct())
    actions = list(AuditLog.objects.order_by().values_list("action", flat=True).distinct())
    users = User.objects.filter(is_active=True).order_by("username").only("id", "username")

    # paginar audit log
    page = int(request.GET.get("page", 1) or 1)
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(page)

    # sesiones (simple: últimas 200, se podrían paginar aparte si quieres)
    sessions = SessionLog.objects.select_related("user")[:200]

    ctx = {
        "logs_page": page_obj,   # página de AuditLog
        "sessions": sessions,    # últimas sesiones
        "apps": apps,
        "actions": actions,
        "users": users,
        "filtros": filtros,
    }
    return render(request, "core/logs.html", ctx)
