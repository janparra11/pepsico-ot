# inventario/signals.py
import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import AnonymousUser

from .models import MovimientoStock
try:
    from .models import Repuesto
    HAS_REP = True
except Exception:
    HAS_REP = False

from core.models import AuditLog

# -------- helpers --------
def _get_user_from_instance(instance):
    """
    Usa creado_por o actualizado_por si existen; ajusta si tu modelo difiere.
    """
    u = getattr(instance, "actualizado_por", None) or getattr(instance, "creado_por", None)
    return (u if u and not isinstance(u, AnonymousUser) else None)

def _mov_repr(m: MovimientoStock):
    cod = getattr(getattr(m, "repuesto", None), "codigo", "") or ""
    tipo = getattr(m, "get_tipo_display", lambda: "")()
    if cod or tipo:
        return f"MOV #{getattr(m, 'pk', '')} · {cod} · {tipo}".strip(" ·")
    return f"Movimiento #{getattr(m, 'pk', '')}"

# -------- MovimientoStock --------
@receiver(post_save, sender=MovimientoStock, dispatch_uid="inv_mov_post_save", weak=False)
def mov_saved(sender, instance: MovimientoStock, created, **kwargs):
    user = _get_user_from_instance(instance)
    extra = {
        "repuesto": getattr(getattr(instance, "repuesto", None), "codigo", ""),
        "descripcion": getattr(getattr(instance, "repuesto", None), "descripcion", ""),
        "tipo": getattr(instance, "get_tipo_display", lambda: "")(),
        "cantidad": float(getattr(instance, "cantidad", 0)) if getattr(instance, "cantidad", None) is not None else None,
        "motivo": getattr(instance, "motivo", "") or "",
        "ot": getattr(getattr(instance, "ot", None), "folio", ""),
    }
    AuditLog.objects.create(
        app="INV",
        action=("CREATE" if created else "UPDATE"),
        user=user,
        object_repr=_mov_repr(instance),
        extra=json.dumps(extra, ensure_ascii=False),
    )

@receiver(post_delete, sender=MovimientoStock, dispatch_uid="inv_mov_post_delete", weak=False)
def mov_deleted(sender, instance: MovimientoStock, **kwargs):
    user = _get_user_from_instance(instance)
    extra = {
        "repuesto": getattr(getattr(instance, "repuesto", None), "codigo", ""),
        "ot": getattr(getattr(instance, "ot", None), "folio", ""),
        "detail": "Movimiento eliminado",
    }
    AuditLog.objects.create(
        app="INV",
        action="DELETE",
        user=user,
        object_repr=_mov_repr(instance),
        extra=json.dumps(extra, ensure_ascii=False),
    )

# -------- Repuesto (opcional) --------
if HAS_REP:
    def _rep_repr(r: "Repuesto"):
        return f"Repuesto {getattr(r, 'codigo', '')}"

    @receiver(post_save, sender=Repuesto, dispatch_uid="inv_rep_post_save", weak=False)
    def rep_saved(sender, instance: "Repuesto", created, **kwargs):
        user = _get_user_from_instance(instance)
        extra = {
            "codigo": getattr(instance, "codigo", ""),
            "descripcion": getattr(instance, "descripcion", ""),
            "stock_minimo": float(getattr(instance, "stock_minimo", 0)) if getattr(instance, "stock_minimo", None) is not None else None,
            "activo": bool(getattr(instance, "activo", True)),
        }
        AuditLog.objects.create(
            app="INV_REP",
            action=("CREATE" if created else "UPDATE"),
            user=user,
            object_repr=_rep_repr(instance),
            extra=json.dumps(extra, ensure_ascii=False),
        )

    @receiver(post_delete, sender=Repuesto, dispatch_uid="inv_rep_post_delete", weak=False)
    def rep_deleted(sender, instance: "Repuesto", **kwargs):
        user = _get_user_from_instance(instance)
        AuditLog.objects.create(
            app="INV_REP",
            action="DELETE",
            user=user,
            object_repr=_rep_repr(instance),
            extra=json.dumps({"detail": "Repuesto eliminado"}, ensure_ascii=False),
        )
