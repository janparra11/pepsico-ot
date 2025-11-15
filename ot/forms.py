from django import forms
from taller.models import Taller, TipoVehiculo

from .models import EstadoOT
from django.conf import settings
from django.contrib.auth.models import User
from .models import PrioridadOT
from taller.models import EstadoVehiculo
from core.roles import Rol
from django.contrib.auth.models import User

ALLOWED_EXTS = {"jpg","jpeg","png","pdf"}

class IngresoForm(forms.Form):
    patente = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "ABCJ11"})
    )

    # ⚠ AHORA: taller NO es obligatorio aquí (lo validamos a mano)
    taller = forms.ModelChoiceField(
        queryset=Taller.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    # NUEVO: para "Otro taller..."
    taller_otro = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej. Taller Maipú 2"})
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3})
    )

    chofer = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    # catálogo de tipos
    tipo = forms.ModelChoiceField(
        queryset=TipoVehiculo.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    # texto libre (se usará cuando no haya catálogo o si eligen "Otro tipo...")
    tipo_texto = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Camión 3/4"})
    )

    evidencia = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )

    def clean_evidencia(self):
        f = self.cleaned_data.get("evidencia")
        if not f:
            return f
        name = f.name.lower()
        ok = any(name.endswith("." + ext) for ext in ALLOWED_EXTS)
        if not ok:
            raise forms.ValidationError("Solo se permiten JPG, JPEG, PNG o PDF.")
        return f

    def clean(self):
        """
        Validamos que haya:
        - un taller seleccionado, O
        - un nombre escrito en 'taller_otro'.
        """
        cleaned = super().clean()
        taller = cleaned.get("taller")
        taller_otro = (cleaned.get("taller_otro") or "").strip()

        if not taller and not taller_otro:
            self.add_error("taller", "Selecciona un taller o escribe uno nuevo.")

        # normalizamos el texto para usarlo en la vista
        cleaned["taller_otro"] = taller_otro
        return cleaned

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

class EventoOTForm(forms.Form):
    titulo = forms.CharField(max_length=140, widget=forms.TextInput(attrs={"class":"form-control"}))
    fecha = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type":"datetime-local", "class":"form-control"}))

class AsignarMecanicoForm(forms.Form):
    mecanico = forms.ModelChoiceField(
        queryset=User.objects.none(),   # se rellena en __init__
        required=False,
        label="Mecánico",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo usuarios activos con rol MECÁNICO
        self.fields["mecanico"].queryset = User.objects.filter(
            is_active=True,
            perfil__rol=Rol.MECANICO
        ).order_by("username")
