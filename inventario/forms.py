from django import forms
from .models import Repuesto, MovimientoStock

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
    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "motivo"]
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01","min":"0.01"}),
            "motivo": forms.TextInput(attrs={"class":"form-control","placeholder":"Compra/ingreso bodega..."})
        }

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.ENTRADA
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m

class MovimientoSalidaForm(forms.ModelForm):
    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "ot", "motivo"]
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01","min":"0.01"}),
            "ot": forms.Select(attrs={"class":"form-select"}),
            "motivo": forms.TextInput(attrs={"class":"form-control","placeholder":"Consumo OT, detalle..."})
        }

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.SALIDA
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m

class MovimientoAjusteForm(forms.ModelForm):
    class Meta:
        model = MovimientoStock
        fields = ["repuesto", "cantidad", "motivo"]
        widgets = {
            "repuesto": forms.Select(attrs={"class":"form-select"}),
            "cantidad": forms.NumberInput(attrs={"class":"form-control","step":"0.01"}),
            "motivo": forms.TextInput(attrs={"class":"form-control","placeholder":"Inventario físico / corrección..."})
        }

    def save(self, user=None, commit=True):
        m = super().save(commit=False)
        m.tipo = MovimientoStock.AJUSTE
        if user and not m.creado_por_id:
            m.creado_por = user
        if commit:
            m.save()
        return m
