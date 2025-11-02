from django import forms
from taller.models import Taller

class IngresoForm(forms.Form):
    patente = forms.CharField(
        max_length=12,
        label="Patente",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "AB12-34"
        })
    )
    taller = forms.ModelChoiceField(
        queryset=Taller.objects.all(),
        label="Taller",
        widget=forms.Select(attrs={"class": "form-select"})
    )
    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3
        })
    )

    def clean_patente(self):
        return self.cleaned_data["patente"].strip().upper()

# ot/forms.py
from django import forms
from .models import EstadoOT

class CambioEstadoForm(forms.Form):
    nuevo_estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=EstadoOT.choices,
        widget=forms.Select(attrs={"class": "form-select"})
    )

class PausaIniciarForm(forms.Form):
    motivo = forms.CharField(
        max_length=100,
        label="Motivo de pausa",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Motivo"})
    )

class PausaFinalizarForm(forms.Form):
    confirmar = forms.BooleanField(
        required=True,
        initial=True,
        label="Confirmar término de pausa"
    )
