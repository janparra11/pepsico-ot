from django.db import models

class Taller(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    direccion = models.CharField(max_length=200, blank=True)
    capacidad = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Taller"
        verbose_name_plural = "Talleres"

    def __str__(self):
        return self.nombre

class Vehiculo(models.Model):
    patente = models.CharField(max_length=12, unique=True)
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)

    class Meta:
        indexes = [models.Index(fields=["patente"])]
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return self.patente.upper()

from django.db import models

class EstadoVehiculo(models.TextChoices):
    TALLER = "TALLER", "En taller"
    FUERA_SERVICIO = "FUERA", "Fuera de servicio"
    OPERATIVO = "OPER", "Operativo"

class Vehiculo(models.Model):
    patente = models.CharField(max_length=12, unique=True)
    marca = models.CharField(max_length=80, blank=True)
    modelo = models.CharField(max_length=80, blank=True)
    estado = models.CharField(
        max_length=10,
        choices=EstadoVehiculo.choices,
        default=EstadoVehiculo.OPERATIVO
    )
    class Meta:
        indexes = [models.Index(fields=["patente"])]
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"

    def __str__(self):
        return self.patente.upper()
