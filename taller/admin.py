from django.contrib import admin
from .models import Taller, Vehiculo

@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "capacidad")
    search_fields = ("nombre",)

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("id", "patente", "marca", "modelo", "estado")
    search_fields = ("patente", "marca", "modelo")
    list_filter = ("estado",)
