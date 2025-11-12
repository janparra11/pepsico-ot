# ot/signals.py
import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import AnonymousUser

from .models import OrdenTrabajo
try:
    # si existe DocumentoOT en tu app ot.models, se loguea; si no, no falla
    from .models import DocumentoOT
    HAS_DOC_OT = True
except Exception:
    HAS_DOC_OT = False

from core.models import AuditLog

from core.middleware import get_current_user

# -------- helpers --------
def _get_user_from_instance(instance):
    # prioridad 1: usuario en el thread local (request.actual)
    u = get_current_user()
    if u and not isinstance(u, AnonymousUser):
        return u
    # fallback: campos del modelo si existen
    u = getattr(instance, "actualizado_por", None) or getattr(instance, "creado_por", None)
    return u if u and not isinstance(u, AnonymousUser) else None

def _ot_repr(ot: OrdenTrabajo):
    folio = getattr(ot, "folio", "") or ""
    pat = getattr(getattr(ot, "vehiculo", None), "patente", "") or ""
    if folio or pat:
        return f"OT {folio} · {pat}".strip(" ·")
    return f"OT #{getattr(ot, 'pk', '')}"

# -------- OrdenTrabajo --------
@receiver(post_save, sender=OrdenTrabajo, dispatch_uid="ot_orden_post_save", weak=False)
def ot_saved(sender, instance: OrdenTrabajo, created, **kwargs):
    user = _get_user_from_instance(instance)
    extra = {
        "estado": getattr(instance, "estado_actual", ""),
        "estado_label": getattr(instance, "get_estado_actual_display", lambda: "")(),
        "activa": bool(getattr(instance, "activa", False)),
        "taller": getattr(getattr(instance, "taller", None), "nombre", ""),
        "vehiculo": getattr(getattr(instance, "vehiculo", None), "patente", ""),
        "fecha_ingreso": getattr(instance, "fecha_ingreso", None).isoformat() if getattr(instance, "fecha_ingreso", None) else None,
        "fecha_cierre": getattr(instance, "fecha_cierre", None).isoformat() if getattr(instance, "fecha_cierre", None) else None,
    }
    AuditLog.objects.create(
        app="OT",
        action=("CREATE" if created else "UPDATE"),
        user=user,
        object_repr=_ot_repr(instance),
        extra=json.dumps(extra, ensure_ascii=False),
    )

@receiver(post_delete, sender=OrdenTrabajo, dispatch_uid="ot_orden_post_delete", weak=False)
def ot_deleted(sender, instance: OrdenTrabajo, **kwargs):
    user = _get_user_from_instance(instance)
    AuditLog.objects.create(
        app="OT",
        action="DELETE",
        user=user,
        object_repr=_ot_repr(instance),
        extra=json.dumps({"detail": "OT eliminada"}, ensure_ascii=False),
    )

# -------- DocumentoOT (opcional) --------
if HAS_DOC_OT:
    def _doc_repr(doc: "DocumentoOT"):
        folio = getattr(getattr(doc, "ot", None), "folio", "")
        tipo = getattr(doc, "tipo", "") or ""
        return f"Doc {tipo} · OT {folio}".strip(" ·")

    @receiver(post_save, sender=DocumentoOT, dispatch_uid="ot_documento_post_save", weak=False)
    def doc_saved(sender, instance: "DocumentoOT", created, **kwargs):
        user = _get_user_from_instance(instance)
        extra = {
            "tipo": getattr(instance, "tipo", "") or "",
            "archivo": getattr(getattr(instance, "archivo", None), "name", ""),
            "ot": getattr(getattr(instance, "ot", None), "folio", ""),
        }
        AuditLog.objects.create(
            app="OT_DOC",
            action=("CREATE" if created else "UPDATE"),
            user=user,
            object_repr=_doc_repr(instance),
            extra=json.dumps(extra, ensure_ascii=False),
        )

    @receiver(post_delete, sender=DocumentoOT, dispatch_uid="ot_documento_post_delete", weak=False)
    def doc_deleted(sender, instance: "DocumentoOT", **kwargs):
        user = _get_user_from_instance(instance)
        extra = {
            "tipo": getattr(instance, "tipo", "") or "",
            "archivo": getattr(getattr(instance, "archivo", None), "name", ""),
            "ot": getattr(getattr(instance, "ot", None), "folio", ""),
            "detail": "Documento eliminado",
        }
        AuditLog.objects.create(
            app="OT_DOC",
            action="DELETE",
            user=user,
            object_repr=_doc_repr(instance),
            extra=json.dumps(extra, ensure_ascii=False),
        )
