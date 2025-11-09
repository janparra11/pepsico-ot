from django import forms
from django.contrib.auth.models import User
from .roles import Rol


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña (temporal)")
    rol = forms.ChoiceField(choices=Rol.choices, label="Rol")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "rol"]
        widgets = {
            "username": forms.TextInput(),
            "first_name": forms.TextInput(),
            "last_name": forms.TextInput(),
            "email": forms.EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            field.widget.attrs.setdefault("class", css)
            field.widget.attrs.setdefault("autocomplete", "off")

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
