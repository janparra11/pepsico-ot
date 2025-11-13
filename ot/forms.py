from django import forms
from taller.models import Taller, TipoVehiculo

# --- Input para múltiples archivos (evita el ValueError de ClearableFileInput) ---
from django import forms
from taller.models import Taller, TipoVehiculo

ALLOWED_EXTS = {"jpg","jpeg","png","pdf"}

class IngresoForm(forms.Form):
    patente = forms.CharField(max_length=12, widget=forms.TextInput(attrs={"class":"form-control", "placeholder":"ABCJ11"}))
    taller = forms.ModelChoiceField(queryset=Taller.objects.all(), widget=forms.Select(attrs={"class":"form-select"}))
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"class":"form-control", "rows":3}))
    chofer = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control"}))
    # si tienes catálogo:
    tipo = forms.ModelChoiceField(
        queryset=TipoVehiculo.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class":"form-select"})
    )
    # si no tienes catálogo o quieres permitir texto:
    tipo_texto = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control", "placeholder":"Camión 3/4"}))

    # **un solo archivo**
    evidencia = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={"class":"form-control"}))

    def clean_evidencia(self):
        f = self.cleaned_data.get("evidencia")
        if not f:
            return f
        name = f.name.lower()
        ok = any(name.endswith("." + ext) for ext in ALLOWED_EXTS)
        if not ok:
            raise forms.ValidationError("Solo se permiten JPG, JPEG, PNG o PDF.")
        return f


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
        from django.conf import settings
        f = self.cleaned_data["archivo"]
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        if f.size > max_bytes:
            raise forms.ValidationError(f"El archivo excede {settings.MAX_UPLOAD_MB} MB.")
        nombre = f.name.lower()
        _, ext = os.path.splitext(nombre)
        ext = ext.replace(".", "")
        if ext not in getattr(settings, "ALLOWED_EXTENSIONS", {"jpg","jpeg","png","pdf"}):
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
