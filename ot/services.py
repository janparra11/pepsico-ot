# ot/services.py
from django.db import transaction
from django.utils import timezone
from .models import OrdenTrabajo, HistorialEstadoOT, EstadoOT, PausaOT

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
    - cierra tramo abierto en historial anterior (fin = now)
    - cierra pausa abierta (si la hubiera)
    - actualiza estado_actual y abre nuevo tramo de historial
    - si CERRADO: inactiva la OT y pone fecha_cierre
    """
    if not validar_transicion(ot.estado_actual, nuevo_estado):
        raise ValueError(f"Transición inválida: {ot.estado_actual} → {nuevo_estado}")

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

    # Cambiar estado y abrir nuevo tramo
    ot.estado_actual = nuevo_estado
    if nuevo_estado == EstadoOT.CERRADO:
        ot.activa = False
        ot.fecha_cierre = timezone.now()
    ot.save()

    HistorialEstadoOT.objects.create(
        ot=ot,
        estado=nuevo_estado,
    )
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
