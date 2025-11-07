from django.db import models
from django.contrib.auth.models import User

class Rol(models.TextChoices):
    GUARDA = "GUARDA", "Guardia"
    RECEP = "RECEP", "Recepcionista"
    MECANICO = "MEC", "Mecánico"
    JEFE = "JEFE", "Jefe de Taller"
    SUPERV = "SUP", "Supervisor"

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=10, choices=Rol.choices)

    def __str__(self):
        return f"{self.user.username} · {self.rol}"

from django.db import models
from django.contrib.auth.models import User

class Notificacion(models.Model):
    titulo = models.CharField(max_length=140)
    mensaje = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)  # ruta interna para “ir a…”
    destinatario = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="notificaciones")
    # Si quisieras “broadcast” (para todos), deja destinatario=None y filtra por rol en una futura versión
    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada_en"]
        indexes = [models.Index(fields=["leida", "creada_en"])]

    def __str__(self):
        return f"{self.titulo} · {'leída' if self.leida else 'no leída'}"

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from ot.models import OrdenTrabajo

class EventoAgenda(models.Model):
    titulo = models.CharField(max_length=140)
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)
    todo_el_dia = models.BooleanField(default=False)
    asignado_a = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos")
    ot = models.ForeignKey(OrdenTrabajo, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["inicio"]), models.Index(fields=["asignado_a", "inicio"])]
        ordering = ["-inicio"]

    def __str__(self):
        return self.titulo
