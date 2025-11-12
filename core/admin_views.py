# core/admin_views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.conf import settings

from .models import Config, AuditLog, SessionLog
from core.auth import require_roles
from core.roles import Rol

from datetime import timedelta
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User

import os, io, zipfile

from django.http import HttpResponse
import csv

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
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def logs_view(request):
    fini = (request.GET.get("fini") or "").strip()
    ffin = (request.GET.get("ffin") or "").strip()
    app  = (request.GET.get("app")  or "").strip()
    act  = (request.GET.get("action") or "").strip()
    usr  = (request.GET.get("user") or "").strip()
    objq = (request.GET.get("objq") or "").strip()   # NUEVO: objeto contiene
    exq  = (request.GET.get("exq")  or "").strip()   # NUEVO: extra contiene

    qs = AuditLog.objects.all().select_related("user").order_by("-ts")

    if fini: qs = qs.filter(ts__date__gte=fini)
    if ffin: qs = qs.filter(ts__date__lte=ffin)
    if app:  qs = qs.filter(app=app)
    if act:  qs = qs.filter(action=act)
    if usr:  qs = qs.filter(user_id=usr)
    if objq: qs = qs.filter(object_repr__icontains=objq)
    if exq:  qs = qs.filter(extra__icontains=exq)  # útil aunque sea JSON texto

    # Export CSV rápido
    if request.GET.get("export") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        resp["Content-Disposition"] = "attachment; filename=logs.csv"
        w = csv.writer(resp)
        w.writerow(["ts","app","action","user","object","extra"])
        for l in qs[:50000]:
            w.writerow([l.ts, l.app, l.action, getattr(l.user, "username", ""), l.object_repr, l.extra])
        return resp

    # paginar
    from django.core.paginator import Paginator
    page = request.GET.get("page") or 1
    logs_page = Paginator(qs, 50).get_page(page)

    # combos
    users = User.objects.filter(is_active=True).order_by("username")
    apps = AuditLog.objects.values_list("app", flat=True).distinct().order_by("app")
    actions = AuditLog.objects.values_list("action", flat=True).distinct().order_by("action")

    ctx = {
        "logs_page": logs_page,
        "users": users, "apps": apps, "actions": actions,
        "filtros": {"fini":fini, "ffin":ffin, "app":app, "action":act, "user":usr, "objq":objq, "exq":exq},
    }
    return render(request, "core/logs.html", ctx)


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
