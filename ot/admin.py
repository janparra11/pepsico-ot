from django.contrib import admin
from .models import OrdenTrabajo, HistorialEstadoOT, PausaOT, DocumentoOT

@admin.register(OrdenTrabajo)
class OTAdmin(admin.ModelAdmin):
    list_display = ("id", "folio", "vehiculo", "taller", "estado_actual", "activa", "fecha_ingreso")
    search_fields = ("folio", "vehiculo__patente")
    list_filter = ("estado_actual", "taller", "activa")

@admin.register(HistorialEstadoOT)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("id", "ot", "estado", "inicio", "fin")
    list_filter = ("estado",)

@admin.register(PausaOT)
class PausaAdmin(admin.ModelAdmin):
    list_display = ("id", "ot", "motivo", "inicio", "fin")

@admin.register(DocumentoOT)
class DocAdmin(admin.ModelAdmin):
    list_display = ("id", "ot", "tipo", "ts", "creado_por")
