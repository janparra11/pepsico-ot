# ot/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import OrdenTrabajo, DocumentoOT
from core.models import AuditLog

def _safe_user(request):
    try:
        return getattr(request, "user", None)
    except Exception:
        return None

def _ot_repr(ot: OrdenTrabajo):
    return f"OT {ot.folio} · {getattr(ot.vehiculo,'patente','')}"

@receiver(post_save, sender=OrdenTrabajo, dispatch_uid="ot_orden_post_save", weak=False)
def log_ot_save(sender, instance: OrdenTrabajo, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    extra = {
        "estado": instance.get_estado_actual_display(),
        "activa": instance.activa,
        "taller": getattr(instance.taller, "nombre", ""),
        "vehiculo": getattr(instance.vehiculo, "patente", ""),
        "fecha_ingreso": instance.fecha_ingreso.isoformat() if instance.fecha_ingreso else None,
        "fecha_cierre": instance.fecha_cierre.isoformat() if instance.fecha_cierre else None,
    }
    AuditLog.objects.create(
        app="OT",
        action=action,
        user=None,  # si quieres capturar usuario, puedes inyectarlo en la request con middleware
        object_repr=_ot_repr(instance),
        extra=str(extra),
    )

@receiver(post_delete, sender=OrdenTrabajo, dispatch_uid="ot_orden_post_delete", weak=False)
def log_ot_delete(sender, instance: OrdenTrabajo, **kwargs):
    AuditLog.objects.create(
        app="OT",
        action="DELETE",
        user=None,
        object_repr=_ot_repr(instance),
        extra="",
    )

@receiver(post_save, sender=DocumentoOT, dispatch_uid="ot_documento_post_save", weak=False)
def log_doc_save(sender, instance: DocumentoOT, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    extra = {
        "tipo": instance.tipo or "",
        "archivo": getattr(instance.archivo, "name", ""),
        "ot": getattr(instance.ot, "folio", ""),
    }
    AuditLog.objects.create(
        app="OT_DOC",
        action=action,
        user=None,
        object_repr=f"Doc OT {getattr(instance.ot,'folio','')}",
        extra=str(extra),
    )

@receiver(post_delete, sender=DocumentoOT, dispatch_uid="ot_documento_post_delete", weak=False)
def log_doc_delete(sender, instance: DocumentoOT, **kwargs):
    AuditLog.objects.create(
        app="OT_DOC",
        action="DELETE",
        user=None,
        object_repr=f"Doc OT {getattr(instance.ot,'folio','')}",
        extra=getattr(instance.archivo, "name", ""),
    )
