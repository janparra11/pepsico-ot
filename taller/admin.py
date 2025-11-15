from django.contrib import admin
from .models import Taller, Vehiculo, TipoVehiculo

@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "capacidad")
    search_fields = ("nombre",)

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ("id", "patente", "marca", "modelo", "estado")
    search_fields = ("patente", "marca", "modelo")
    list_filter = ("estado",)

@admin.register(TipoVehiculo)
class TipoVehiculoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)
