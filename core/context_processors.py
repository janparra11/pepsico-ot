def notif_count(request):
    if request.user.is_authenticated:
        try:
            return {
                "notif_unread": request.user.notificaciones.filter(leida=False).count()
            }
        except Exception:
            return {"notif_unread": 0}
    return {"notif_unread": 0}
