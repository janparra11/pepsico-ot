from django import forms
from .models import Repuesto, MovimientoStock

MOTIVOS_ENTRADA = [
    ("COMPRA", "Compra"),
    ("DEVOLUCION", "Devolución a stock"),
    ("AJUSTE_INICIAL", "Ajuste inicial"),
    ("OTRO", "Otro (especificar)"),
]

MOTIVOS_SALIDA = [
    ("CONSUMO_OT", "Consumo en OT"),
    ("PRESTAMO", "Préstamo a otro taller"),
    ("DEVOLUCION_PROV", "Devolución a proveedor"),
    ("OTRO", "Otro (especificar)"),
]

MOTIVOS_AJUSTE = [
    ("AJUSTE_INVENTARIO", "Ajuste por inventario físico"),
    ("ROTURA_MERMA", "Rotura / Merma"),
    ("OTRO", "Otro (especificar)"),
]

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = ["codigo", "descripcion", "unidad", "stock_minimo", "activo"]
        widgets = {f: forms.TextInput(attrs={"class":"form-control"}) for f in ["codigo","descripcion"]}
        widgets.update({
            "unidad": forms.Select(attrs={"class":"form-select"}),
            "stock_minimo": forms.NumberInput(attrs={"class":"form-control","step":"0.01"}),
            "activo": forms.CheckboxInput(attrs={"class":"form-check-input"}),
        })

class MovimientoEntradaForm(forms.ModelForm):
    motivo = forms.ChoiceField(choices=MOTIVOS_ENTRADA, widget=forms.Select(attrs={"class":"form-select"}))
    motivo_otro = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Especifica el motivo"}))

    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "motivo"]  # 'motivo_otro' no es del modelo
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01","min":"0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        mot = cleaned.get("motivo")
        mot_otro = (cleaned.get("motivo_otro") or "").strip()
        if mot == "OTRO":
            if not mot_otro:
                self.add_error("motivo_otro", "Debes especificar el motivo.")
            else:
                cleaned["motivo"] = mot_otro  # guardaremos el texto libre
        else:
            # guardamos la ETIQUETA legible (no el código)
            label = dict(MOTIVOS_ENTRADA).get(mot, mot)
            cleaned["motivo"] = label
        return cleaned

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.ENTRADA
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m


class MovimientoSalidaForm(forms.ModelForm):
    motivo = forms.ChoiceField(choices=MOTIVOS_SALIDA, widget=forms.Select(attrs={"class":"form-select"}))
    motivo_otro = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Especifica el motivo"}))

    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "ot", "motivo"]
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01","min":"0.01"}),
            "ot": forms.Select(attrs={"class":"form-select"}),
        }

    def clean(self):
        cleaned = super().clean()
        mot = cleaned.get("motivo")
        mot_otro = (cleaned.get("motivo_otro") or "").strip()
        if mot == "OTRO":
            if not mot_otro:
                self.add_error("motivo_otro", "Debes especificar el motivo.")
            else:
                cleaned["motivo"] = mot_otro
        else:
            label = dict(MOTIVOS_SALIDA).get(mot, mot)
            cleaned["motivo"] = label
        return cleaned

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.SALIDA
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m


class MovimientoAjusteForm(forms.ModelForm):
    motivo = forms.ChoiceField(choices=MOTIVOS_AJUSTE, widget=forms.Select(attrs={"class":"form-select"}))
    motivo_otro = forms.CharField(required=False, widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Especifica el motivo"}))

    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "motivo"]
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        mot = cleaned.get("motivo")
        mot_otro = (cleaned.get("motivo_otro") or "").strip()
        if mot == "OTRO":
            if not mot_otro:
                self.add_error("motivo_otro", "Debes especificar el motivo.")
            else:
                cleaned["motivo"] = mot_otro
        else:
            label = dict(MOTIVOS_AJUSTE).get(mot, mot)
            cleaned["motivo"] = label
        return cleaned

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.AJUSTE
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m

