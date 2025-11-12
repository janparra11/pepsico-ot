from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Perfil

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import SessionLog, AuditLog

@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    SessionLog.objects.create(
        user=user,
        action=SessionLog.LOGIN,
        ua=(request.META.get("HTTP_USER_AGENT", "") or "")[:200],
        ip=request.META.get("REMOTE_ADDR", "") or "",
    )
    AuditLog.objects.create(app="AUTH", action="LOGIN", user=user, object_repr=user.username)

@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user and getattr(user, "is_authenticated", False):
        SessionLog.objects.create(
            user=user,
            action=SessionLog.LOGOUT,
            ua=(request.META.get("HTTP_USER_AGENT", "") or "")[:200],
            ip=request.META.get("REMOTE_ADDR", "") or "",
        )
        AuditLog.objects.create(app="AUTH", action="LOGOUT", user=user, object_repr=user.username)
