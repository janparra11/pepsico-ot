from django.db import models
from django.contrib.auth.models import User
from .roles import Rol

from django.utils import timezone
from ot.models import OrdenTrabajo

from django.db.models.signals import post_save
from django.dispatch import receiver

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=32, choices=Rol.choices, default=Rol.RECEPCIONISTA)

    def __str__(self):
        return f"{self.user.username} · {self.get_rol_display()}"

    @receiver(post_save, sender=User)
    def ensure_perfil(sender, instance, created, **kwargs):
        # Asegura que todo usuario tenga Perfil (evita 403 “fantasmas”)
        if not hasattr(instance, "perfil"):
            Perfil.objects.get_or_create(user=instance)

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

class EventoAgenda(models.Model):
    titulo = models.CharField(max_length=140)
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)
    todo_el_dia = models.BooleanField(default=False)
    asignado_a = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos")
    ot = models.ForeignKey(OrdenTrabajo, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventos")
    descripcion = models.TextField(blank=True)  # ← NUEVO
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["inicio"]), models.Index(fields=["asignado_a", "inicio"])]
        ordering = ["-inicio"]

    def __str__(self):
        return self.titulo

class Config(models.Model):
    nombre_taller = models.CharField(max_length=120, default="Taller")
    horario = models.CharField(max_length=120, blank=True, default="")
    contacto = models.CharField(max_length=120, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    sla_horas = models.PositiveIntegerField(default=72, help_text="Horas de SLA para cierre de OT")

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"

    def __str__(self):
        return f"Config · {self.nombre_taller}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class AuditLog(models.Model):
    app = models.CharField(max_length=40)          # <-- max_length correcto
    action = models.CharField(max_length=40)       # CREATE/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    object_repr = models.CharField(max_length=140, blank=True, default="")
    extra = models.TextField(blank=True, default="")
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]
        indexes = [models.Index(fields=["app", "action", "ts"])]

    def __str__(self):
        return f"[{self.ts:%Y-%m-%d %H:%M}] {self.app}:{self.action} · {self.object_repr or '-'}"

class SessionLog(models.Model):
    LOGIN = "LOGIN"; LOGOUT = "LOGOUT"
    ACTIONS = [(LOGIN, "Login"), (LOGOUT, "Logout")]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTIONS)
    ua = models.CharField(max_length=200, blank=True, default="")
    ip = models.CharField(max_length=64, blank=True, default="")
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]

    def __str__(self):
        return f"{self.user} {self.action} @ {self.ts:%Y-%m-%d %H:%M}"
