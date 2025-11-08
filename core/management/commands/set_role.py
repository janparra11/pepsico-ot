from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from core.roles import Rol

class Command(BaseCommand):
    help = "Asigna un rol a un usuario. Ej: python manage.py set_role admin JEFE_TALLER"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("rol", choices=[c[0] for c in Rol.choices])

    def handle(self, *args, **opts):
        try:
            u = User.objects.get(username=opts["username"])
        except User.DoesNotExist:
            raise CommandError("Usuario no existe")
        if not hasattr(u, "perfil"):
            # en caso de usuarios viejos sin perfil
            from core.models import Perfil
            Perfil.objects.create(user=u, rol=opts["rol"])
        else:
            u.perfil.rol = opts["rol"]
            u.perfil.save()
        self.stdout.write(self.style.SUCCESS(f"Rol {opts['rol']} asignado a {u.username}"))
