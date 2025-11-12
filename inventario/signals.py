# inventario/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import MovimientoStock, Repuesto
from core.models import AuditLog

def _mov_repr(m: MovimientoStock):
    cod = getattr(m.repuesto, "codigo", "")
    return f"MOV {m.id} · {cod} · {m.get_tipo_display()}"

@receiver(post_save, sender=MovimientoStock, dispatch_uid="inv_mov_post_save", weak=False)
def log_mov_save(sender, instance: MovimientoStock, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    extra = {
        "repuesto": getattr(instance.repuesto, "codigo", ""),
        "descripcion": getattr(instance.repuesto, "descripcion", ""),
        "tipo": instance.get_tipo_display(),
        "cantidad": float(instance.cantidad) if instance.cantidad is not None else None,
        "motivo": instance.motivo or "",
        "ot": getattr(getattr(instance, "ot", None), "folio", ""),
    }
    AuditLog.objects.create(
        app="INV",
        action=action,
        user=None,
        object_repr=_mov_repr(instance),
        extra=str(extra),
    )

@receiver(post_delete, sender=MovimientoStock, dispatch_uid="inv_mov_post_delete", weak=False)
def log_mov_delete(sender, instance: MovimientoStock, **kwargs):
    AuditLog.objects.create(
        app="INV",
        action="DELETE",
        user=None,
        object_repr=_mov_repr(instance),
        extra="",
    )

@receiver(post_save, sender=Repuesto, dispatch_uid="inv_rep_post_save", weak=False)
def log_rep_save(sender, instance: Repuesto, created, **kwargs):
    action = "CREATE" if created else "UPDATE"
    extra = {
        "codigo": instance.codigo,
        "descripcion": instance.descripcion,
        "stock_minimo": float(instance.stock_minimo) if instance.stock_minimo is not None else None,
        "activo": instance.activo,
    }
    AuditLog.objects.create(
        app="INV_REP",
        action=action,
        user=None,
        object_repr=f"Repuesto {instance.codigo}",
        extra=str(extra),
    )

@receiver(post_delete, sender=Repuesto, dispatch_uid="inv_rep_post_delete", weak=False)
def log_rep_delete(sender, instance: Repuesto, **kwargs):
    AuditLog.objects.create(
        app="INV_REP",
        action="DELETE",
        user=None,
        object_repr=f"Repuesto {instance.codigo}",
        extra="",
    )
