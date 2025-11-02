from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    return render(request, "home.html")

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
