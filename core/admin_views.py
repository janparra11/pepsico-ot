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
