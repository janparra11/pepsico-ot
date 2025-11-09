from django import forms
from django.contrib.auth.models import User
from .roles import Rol

class UserCreateForm(forms.ModelForm):
    # password simple para crear; luego el usuario puede cambiarla
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña (temporal)")
    rol = forms.ChoiceField(choices=Rol.choices, label="Rol")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "rol"]

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("Ya existe un usuario con ese username.")
        return u

    def clean_email(self):
        e = (self.cleaned_data.get("email") or "").strip()
        if e and User.objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("Ya existe un usuario con ese email.")
        return e

class UserRoleForm(forms.Form):
    rol = forms.ChoiceField(choices=Rol.choices, label="Rol")

class UserStatusForm(forms.Form):
    activo = forms.BooleanField(required=False, initial=True, label="Activo")
