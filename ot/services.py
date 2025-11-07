# ot/services.py
from django.db import transaction
from django.utils import timezone
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT, PausaOT
from core.services import notificar   # ← este import es clave

# Matriz de transiciones válidas (puedes ajustar según tu SRS)
ALLOWED_TRANSITIONS = {
    EstadoOT.INGRESADO:   {EstadoOT.DIAGNOSTICO},
    EstadoOT.DIAGNOSTICO: {EstadoOT.REPARACION, EstadoOT.LISTO},
    EstadoOT.REPARACION:  {EstadoOT.LISTO, EstadoOT.DIAGNOSTICO},  # ejemplo: volver a Diagnóstico
    EstadoOT.LISTO:       {EstadoOT.ENTREGADO, EstadoOT.REPARACION},
    EstadoOT.ENTREGADO:   {EstadoOT.CERRADO},
    EstadoOT.CERRADO:     set(),  # no hay salidas desde CERRADO
}

def validar_transicion(estado_actual, nuevo_estado):
    return nuevo_estado in ALLOWED_TRANSITIONS.get(estado_actual, set())

@transaction.atomic
def cambiar_estado(ot: OrdenTrabajo, nuevo_estado: str, usuario=None):
    """
    Cambia el estado de la OT de forma atómica:
    - valida transición
    - cierra tramo anterior en historial
    - actualiza estado_actual
    - crea notificación
    """
    
    from core.services import notificar

    # 👉 Guardamos el estado antes de cambiarlo
    estado_anterior = ot.estado_actual

    if not validar_transicion(estado_anterior, nuevo_estado):
        raise ValueError(f"Transición inválida: {estado_anterior} → {nuevo_estado}")

    # Cerrar pausa abierta (si existe)
    pausa_abierta = PausaOT.objects.filter(ot=ot, fin__isnull=True).first()
    if pausa_abierta:
        pausa_abierta.fin = timezone.now()
        pausa_abierta.save()

    # Cerrar tramo de historial abierto
    tramo_abierto = HistorialEstadoOT.objects.filter(ot=ot, fin__isnull=True).first()
    if tramo_abierto:
        tramo_abierto.fin = timezone.now()
        tramo_abierto.save()

    # Cambiar estado
    ot.estado_actual = nuevo_estado
    if nuevo_estado == EstadoOT.CERRADO:
        ot.activa = False
        ot.fecha_cierre = timezone.now()
    ot.save()

    from core.models import EventoAgenda
    from datetime import timedelta

    if nuevo_estado in [EstadoOT.LISTO, EstadoOT.ENTREGADO, EstadoOT.CERRADO]:
        EventoAgenda.objects.create(
            titulo=f"Entrega OT {ot.folio}",
            inicio=timezone.now() + timedelta(hours=1),
            ot=ot,
            asignado_a=usuario
        )


    # Registrar nuevo tramo
    HistorialEstadoOT.objects.create(ot=ot, estado=nuevo_estado)

    # 🔔 Crear notificación
    try:
        nombre_estado_anterior = ot.get_estado_actual_display() if estado_anterior == nuevo_estado else dict(EstadoOT.choices).get(estado_anterior, estado_anterior)
        nombre_estado_nuevo = ot.get_estado_actual_display()
        notificar(
            destinatario=usuario,
            titulo=f"OT {ot.folio}: {nombre_estado_nuevo}",
            mensaje=f"Cambio de estado: {nombre_estado_anterior} → {nombre_estado_nuevo}.",
            url=f"/ot/{ot.id}/"
        )
    except Exception:
        # Silenciar cualquier error de notificación (no debe romper flujo)
        pass

    return ot

@transaction.atomic
def iniciar_pausa(ot: OrdenTrabajo, motivo: str):
    """
    Inicia una pausa si no existe una pausa abierta.
    """
    if PausaOT.objects.filter(ot=ot, fin__isnull=True).exists():
        raise ValueError("Ya existe una pausa abierta en esta OT.")

    PausaOT.objects.create(ot=ot, motivo=motivo)
    return True

@transaction.atomic
def finalizar_pausa(ot: OrdenTrabajo):
    """
    Finaliza la pausa abierta (si existe).
    """
    pausa_abierta = PausaOT.objects.filter(ot=ot, fin__isnull=True).first()
    if not pausa_abierta:
        raise ValueError("No hay una pausa abierta para esta OT.")
    pausa_abierta.fin = timezone.now()
    pausa_abierta.save()
    return True
