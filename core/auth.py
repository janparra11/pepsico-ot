from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .roles import Rol

def require_roles(*roles):
    def decorator(viewfunc):
        @wraps(viewfunc)
        @login_required
        def _wrapped(request, *args, **kwargs):
            perfil = getattr(request.user, "perfil", None)
            rol = getattr(perfil, "rol", None)
            if rol in roles or rol == Rol.ADMIN:
                return viewfunc(request, *args, **kwargs)
            raise PermissionDenied  # 403
        return _wrapped
    return decorator

# Atajos
require_guardia = require_roles(Rol.GUARDIA)
require_supervisor = require_roles(Rol.SUPERVISOR)
require_jefe_taller = require_roles(Rol.JEFE_TALLER)
require_mecanico = require_roles(Rol.MECANICO)
require_asistente = require_roles(Rol.ASISTENTE_REPUESTO)
require_recepcionista = require_roles(Rol.RECEPCIONISTA)
