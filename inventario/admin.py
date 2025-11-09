from django.contrib import admin
from .models import Repuesto, MovimientoStock

@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descripcion", "unidad", "stock_actual", "stock_minimo", "activo")
    search_fields = ("codigo", "descripcion")
    list_filter = ("activo", "unidad")

@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ("repuesto", "tipo", "cantidad", "ot", "creado_por", "creado_en")
    search_fields = ("repuesto__codigo", "repuesto__descripcion", "motivo")
    list_filter = ("tipo", "creado_en")
    autocomplete_fields = ("repuesto", "ot", "creado_por")
