from django.db import models

class Rol(models.TextChoices):
    ADMIN = "ADMIN", "Administrador"
    GUARDIA = "GUARDIA", "Guardia de Acceso"
    SUPERVISOR = "SUPERVISOR", "Supervisor de Flota"
    JEFE_TALLER = "JEFE_TALLER", "Jefe del Taller"
    MECANICO = "MECANICO", "Mecánico"
    ASISTENTE_REPUESTO = "ASISTENTE_REPUESTO", "Asistente de Repuesto"
    RECEPCIONISTA = "RECEPCIONISTA", "Recepcionista de Vehículo"
    # Coordinador de zona: no lo implementamos aún
