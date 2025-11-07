from django.http import HttpResponse
from django.shortcuts import render

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def home(request):
    user = request.user
    # Flags simples hoy; mañana se conectan a roles/permisos
    ctx = {
        "username": user.get_username(),
        "can_registrar_ingreso": True,   # luego: user.perfil.rol in ["GUARDIA","SUP","JEFE"]
        "can_ver_ots": True,             # luego: cualquier rol autenticado
        "can_ver_dashboard": True,       # luego: user.perfil.rol in ["SUP","JEFE"]
        "can_ver_notifs": True,          # luego: cualquier rol autenticado
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
