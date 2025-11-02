from django.db import models
from django.conf import settings
from django.utils import timezone
from taller.models import Vehiculo, Taller

class EstadoOT(models.TextChoices):
    INGRESADO   = "ING", "Ingresado"
    DIAGNOSTICO = "DIA", "Diagnóstico"
    REPARACION  = "REP", "Reparación"
    LISTO       = "LIS", "Listo"
    ENTREGADO   = "ENT", "Entregado"
    CERRADO     = "CER", "Cerrado"

class OrdenTrabajo(models.Model):
    folio = models.CharField(max_length=20, unique=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT)
    taller = models.ForeignKey(Taller, on_delete=models.PROTECT)
    responsable = models.CharField(max_length=120, blank=True)
    estado_actual = models.CharField(max_length=3, choices=EstadoOT.choices, default=EstadoOT.INGRESADO)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)  # bloquear duplicidad activa por patente

    class Meta:
        constraints = [
            # No más de una OT activa por vehículo
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(activa=True),
                name="uq_ot_activa_por_vehiculo"
            )
        ]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["estado_actual"]),
        ]

    def __str__(self):
        return f"OT {self.folio} · {self.vehiculo}"

class HistorialEstadoOT(models.Model):
    ot = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="historial")
    estado = models.CharField(max_length=3, choices=EstadoOT.choices)
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["ot", "estado", "inicio"])]
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"

class PausaOT(models.Model):
    ot = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="pausas")
    motivo = models.CharField(max_length=100)
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["ot", "inicio"])]
        constraints = [
            models.UniqueConstraint(
                fields=["ot"],
                condition=models.Q(fin__isnull=True),
                name="uq_pausa_abierta_por_ot"
            )
        ]
        verbose_name = "Pausa"
        verbose_name_plural = "Pausas"

class DocumentoOT(models.Model):
    ot = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="documentos")
    archivo = models.FileField(upload_to="docs/")  # valida mime/tamaño en vistas/forms
    tipo = models.CharField(max_length=30, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["ot", "ts"])]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
