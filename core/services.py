from django.contrib.auth.models import User
from .models import Notificacion

def notificar(destinatario: User | None, titulo: str, mensaje: str = "", url: str = ""):
    return Notificacion.objects.create(
        destinatario=destinatario,
        titulo=titulo,
        mensaje=mensaje,
        url=url
    )
