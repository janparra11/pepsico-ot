from django.db import models
from django.conf import settings
from django.utils import timezone
from taller.models import Vehiculo, Taller
import os
from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ValidationError


class EstadoOT(models.TextChoices):
    INGRESADO   = "ING", "Ingresado"
    DIAGNOSTICO = "DIA", "Diagnóstico"
    REPARACION  = "REP", "Reparación"
    LISTO       = "LIS", "Listo"
    ENTREGADO   = "ENT", "Entregado"
    CERRADO     = "CER", "Cerrado"

class PrioridadOT(models.IntegerChoices):
    BAJA = 1, "Baja"
    MEDIA = 2, "Media"
    ALTA = 3, "Alta"
    CRITICA = 4, "Crítica"

class OrdenTrabajo(models.Model):
    folio = models.CharField(max_length=20, unique=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT)
    taller = models.ForeignKey(Taller, on_delete=models.PROTECT)
    responsable = models.CharField(max_length=120, blank=True)
    estado_actual = models.CharField(max_length=3, choices=EstadoOT.choices, default=EstadoOT.INGRESADO)
    # NUEVO:
    prioridad = models.IntegerField(choices=PrioridadOT.choices, default=PrioridadOT.MEDIA)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(activa=True),
                name="uq_ot_activa_por_vehiculo"
            )
        ]
        indexes = [
            models.Index(fields=["folio"]),
            models.Index(fields=["estado_actual"]),
            models.Index(fields=["prioridad"]),  # ← para ordenar/buscar por prioridad
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

def documento_upload_path(instance, filename):
    # carpeta por OT, nombre aleatorio
    ext = os.path.splitext(filename)[1].lower()  # conserva extensión
    return f"docs/ot_{instance.ot_id}/{uuid4().hex}{ext}"

def validar_archivo(archivo):
    """Valida tamaño y extensión de forma tolerante (sin depender de MIME)."""
    import os
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if archivo.size > max_bytes:
        raise ValidationError(f"El archivo excede el límite de {settings.MAX_UPLOAD_MB} MB.")

    nombre = archivo.name.lower()
    _, ext = os.path.splitext(nombre)
    ext = ext.replace(".", "")
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValidationError("Solo se permiten archivos JPG, JPEG, PNG o PDF.")

class DocumentoOT(models.Model):
    ot = models.ForeignKey(OrdenTrabajo, on_delete=models.CASCADE, related_name="documentos")
    archivo = models.FileField(upload_to=documento_upload_path)  # ← NUEVO upload_to
    tipo = models.CharField(max_length=30, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["ot", "ts"])]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def clean(self):
        # Llama al validador
        if self.archivo:
            validar_archivo(self.archivo)
