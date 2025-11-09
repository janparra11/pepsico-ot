# core/filters.py
from typing import Any
from django.contrib.auth.models import User

def filter_ots_for_user(qs, user: User):
    """
    Devuelve el queryset de OrdenTrabajo ya filtrado según el rol del usuario.
    """
    if not getattr(user, "is_authenticated", False):
        return qs.none()

    from core.roles import Rol
    from ot.models import OrdenTrabajo

    rol = getattr(getattr(user, "perfil", None), "rol", None)

    if rol == Rol.MECANICO:
        return qs.filter(mecanico_asignado=user)

    elif rol == Rol.GUARDIA:
        return qs.filter(activa=True)

    elif rol == Rol.RECEPCIONISTA:
        if hasattr(OrdenTrabajo, "creado_por"):
            return qs.filter(creado_por=user)
        return qs

    # ADMIN, SUPERVISOR, JEFE_TALLER → ven todo
    return qs
