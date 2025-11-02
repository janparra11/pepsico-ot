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
