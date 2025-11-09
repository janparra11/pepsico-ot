# core/templatetags/roles.py
from django import template

register = template.Library()

def _get_user_role(user):
    try:
        return user.perfil.rol or ""
    except Exception:
        return ""

def _is_admin(user):
    return _get_user_role(user) == "ADMIN"

@register.filter(name="has_role")
def has_role(user, role_code):
    """
    Uso: {% if request.user|has_role:"JEFE_TALLER" %}...{% endif %}
    ADMIN siempre pasa.
    """
    if _is_admin(user):
        return True
    return _get_user_role(user) == role_code

@register.simple_tag(takes_context=True)
def is_role(context, *roles):
    """
    Uso:
      {% is_role 'RECEPCIONISTA' 'GUARDIA' as puede %}
      {% if puede %}...{% endif %}
    ADMIN siempre pasa.
    """
    user = context.get("request").user
    if _is_admin(user):
        return True
    return _get_user_role(user) in roles
