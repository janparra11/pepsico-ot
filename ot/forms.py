from django import forms
from taller.models import Taller
import os

from taller.models import TipoVehiculo

class IngresoForm(forms.Form):
    patente = forms.CharField(max_length=12, widget=forms.TextInput(attrs={"class":"form-control"}))
    chofer = forms.CharField(max_length=120, required=False, widget=forms.TextInput(attrs={"class":"form-control"}))
    tipo = forms.ModelChoiceField(
        queryset=TipoVehiculo.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class":"form-select"})
    )
    taller = forms.ModelChoiceField(
        queryset=Taller.objects.all(),
        widget=forms.Select(attrs={"class":"form-select"})
    )
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"class":"form-control", "rows":3}))

    def clean_patente(self):
        return self.cleaned_data["patente"].strip().upper()

#class IngresoForm(forms.Form):
#    patente = forms.CharField(
#        max_length=12,
#        label="Patente",
#        widget=forms.TextInput(attrs={
#            "class": "form-control",
#            "placeholder": "AB12-34"
#        })
#    )
#    taller = forms.ModelChoiceField(
#        queryset=Taller.objects.all(),
#        label="Taller",
#        widget=forms.Select(attrs={"class": "form-select"})
#    )
#    observaciones = forms.CharField(
#        required=False,
#        label="Observaciones",
#        widget=forms.Textarea(attrs={
#            "class": "form-control",
#            "rows": 3
#        })
#    )
#
#    def clean_patente(self):
#        return self.cleaned_data["patente"].strip().upper()

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

from django.conf import settings

class DocumentoForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo (JPG/PNG/PDF)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )
    tipo = forms.CharField(
        required=False,
        max_length=30,
        label="Tipo (opcional)",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "ej. Informe, Siniestro, Antes/Después"})
    )

def clean_archivo(self):
    import os
    f = self.cleaned_data["archivo"]
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if f.size > max_bytes:
        raise forms.ValidationError(f"El archivo excede {settings.MAX_UPLOAD_MB} MB.")

    nombre = f.name.lower()
    _, ext = os.path.splitext(nombre)
    ext = ext.replace(".", "")
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise forms.ValidationError("Solo se permiten archivos JPG, JPEG, PNG o PDF.")
    return f

from django import forms
from .models import PrioridadOT
from taller.models import EstadoVehiculo

class PrioridadForm(forms.Form):
    prioridad = forms.ChoiceField(
        choices=PrioridadOT.choices,
        label="Prioridad",
        widget=forms.Select(attrs={"class": "form-select"})
    )

class EstadoVehiculoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=EstadoVehiculo.choices,
        label="Estado del vehículo",
        widget=forms.Select(attrs={"class": "form-select"})
    )

from django import forms

class EventoOTForm(forms.Form):
    titulo = forms.CharField(max_length=140, widget=forms.TextInput(attrs={"class":"form-control"}))
    fecha = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type":"datetime-local", "class":"form-control"}))

from django import forms
from django.contrib.auth.models import User  # si usas el User por defecto

class AsignarMecanicoForm(forms.Form):
    mecanico = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("username"),
        required=False,
        label="Mecánico",
        widget=forms.Select(attrs={"class": "form-select"})
    )
