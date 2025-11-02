from django.urls import path
from . import views

urlpatterns = [
    path("ingresos/nuevo/", views.ingreso_nuevo, name="ingreso_nuevo"),
    path("ot/<int:ot_id>/", views.ot_detalle, name="ot_detalle"),
    path("ot/<int:ot_id>/cambiar-estado/", views.ot_cambiar_estado, name="ot_cambiar_estado"),
    path("ot/<int:ot_id>/pausa/iniciar/", views.pausa_iniciar, name="pausa_iniciar"),
    path("ot/<int:ot_id>/pausa/finalizar/", views.pausa_finalizar, name="pausa_finalizar"),
    path("ot/<int:ot_id>/docs/subir/", views.ot_subir_documento, name="ot_subir_documento"),
    path("ot/<int:ot_id>/docs/<int:doc_id>/eliminar/", views.ot_eliminar_documento, name="ot_eliminar_documento"),
]
