from django.urls import path
from . import views

urlpatterns = [
    path("repuestos/", views.repuesto_list, name="inv_repuesto_list"),
    path("repuestos/nuevo/", views.repuesto_create, name="inv_repuesto_create"),
    path("repuestos/<int:pk>/editar/", views.repuesto_edit, name="inv_repuesto_edit"),

    path("movimientos/", views.mov_list, name="inv_mov_list"),
    path("mov/entrada/", views.mov_entrada, name="inv_mov_entrada"),
    path("mov/salida/", views.mov_salida, name="inv_mov_salida"),
    path("mov/ajuste/", views.mov_ajuste, name="inv_mov_ajuste"),
]
