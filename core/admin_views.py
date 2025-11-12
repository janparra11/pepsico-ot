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

from django.http import JsonResponse, Http404
from django.utils.html import escape
import json

from datetime import datetime, time as dtime
from django.contrib.auth import get_user_model

@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def config_view(request):
    cfg = Config.get_solo()
    if request.method == "POST":
        cfg.nombre_taller = request.POST.get("nombre_taller", cfg.nombre_taller)
        cfg.horario = request.POST.get("horario", cfg.horario)
        cfg.contacto = request.POST.get("contacto", cfg.contacto)
        # NEW: SLA
        try:
            cfg.sla_horas = int(request.POST.get("sla_horas") or cfg.sla_horas)
        except (TypeError, ValueError):
            pass
        cfg.save()
        AuditLog.objects.create(app="CONFIG", action="UPDATE", user=request.user,
                                object_repr="Config", extra=f"sla_horas={cfg.sla_horas}")
        messages.success(request, "Configuración actualizada")
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
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def logs_detail(request, pk: int):
    try:
        l = AuditLog.objects.select_related("user").get(pk=pk)
    except AuditLog.DoesNotExist:
        raise Http404("Log no encontrado")

    # intenta parsear extra como JSON; si no, devuélvelo como texto
    extra_raw = l.extra or ""
    extra_json = None
    if extra_raw:
        try:
            extra_json = json.loads(extra_raw)
        except Exception:
            extra_json = None

    data = {
        "id": l.id,
        "ts": l.ts.strftime("%Y-%m-%d %H:%M:%S"),
        "app": l.app,
        "action": l.action,
        "user": getattr(l.user, "username", None),
        "object_repr": l.object_repr,
        "extra_is_json": extra_json is not None,
        "extra_json": extra_json,           # el front lo mostrará pretty
        "extra_text": extra_raw if extra_json is None else None,
    }
    return JsonResponse(data)

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

def _parse_date_aware(s, end=False):
    """Convierte 'YYYY-MM-DD' en datetime TZ-aware (inicio o fin del día)."""
    if not s:
        return None
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None
    dt = datetime.combine(d, dtime.max if end else dtime.min)
    return timezone.make_aware(dt)

def _logs_queryset_from_request(request):
    """Replica exactamente los filtros de la vista de bitácora."""
    qs = AuditLog.objects.select_related("user").all().order_by("-ts")

    fini = (request.GET.get("fini") or "").strip()
    ffin = (request.GET.get("ffin") or "").strip()
    app  = (request.GET.get("app")  or "").strip()
    act  = (request.GET.get("action") or "").strip()
    uid  = (request.GET.get("user") or "").strip()
    obj  = (request.GET.get("obj") or "").strip()
    ext  = (request.GET.get("extra") or "").strip()
    q    = (request.GET.get("q") or "").strip()

    dt_ini = _parse_date_aware(fini, end=False)
    dt_fin = _parse_date_aware(ffin, end=True)
    if dt_ini:
        qs = qs.filter(ts__gte=dt_ini)
    if dt_fin:
        qs = qs.filter(ts__lte=dt_fin)
    if app:
        qs = qs.filter(app__iexact=app)
    if act:
        qs = qs.filter(action__iexact=act)
    if uid:
        qs = qs.filter(user_id=uid)
    if obj:
        qs = qs.filter(object_repr__icontains=obj)
    if ext:
        qs = qs.filter(extra__icontains=ext)
    if q:
        qs = qs.filter(Q(object_repr__icontains=q) | Q(extra__icontains=q))

    return qs

@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def export_logs_csv(request):
    """Descarga CSV con los registros filtrados de la bitácora."""
    qs = _logs_queryset_from_request(request)

    # Nombre de archivo con fecha
    hoy = timezone.localdate().strftime("%Y%m%d")
    fname = f"logs_{hoy}.csv"

    # Respuesta CSV (BOM para Excel en Windows)
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    resp.write("\ufeff")  # BOM UTF-8

    writer = csv.writer(resp)
    writer.writerow(["Fecha", "App", "Acción", "Usuario", "Objeto", "Extra"])

    # Si quieres, limita un máximo (por ejemplo 50k filas):
    for log in qs.iterator(chunk_size=2000):
        ts_local = timezone.localtime(log.ts).strftime("%Y-%m-%d %H:%M")
        writer.writerow([
            ts_local,
            log.app or "",
            log.action or "",
            getattr(log.user, "username", "") or "",
            log.object_repr or "",
            (log.extra or "").replace("\n", " ").strip(),
        ])

    return resp