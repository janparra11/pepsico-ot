def notif_count(request):
    if request.user.is_authenticated:
        try:
            return {
                "notif_unread": request.user.notificaciones.filter(leida=False).count()
            }
        except Exception:
            return {"notif_unread": 0}
    return {"notif_unread": 0}

# core/context_processors.py
def unread_notifications(request):
    try:
        from core.models import Notificacion
    except Exception:
        return {}

    if request.user.is_authenticated:
        qs = Notificacion.objects.filter(destinatario=request.user).order_by("-creada_en")
        return {
            "notif_unread": qs.filter(leida=False).count(),
            "notif_latest": qs[:5],  # queryset, se puede iterar en el template
        }
    return {"notif_unread": 0, "notif_latest": []}
