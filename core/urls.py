from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.healthcheck, name="healthcheck"),
    path("notificaciones/", views.notificaciones_lista, name="core_notificaciones"),
    path("notificaciones/<int:notif_id>/", views.notificacion_detalle, name="core_notificacion_detalle"),  # ← nuevo
    path("notificaciones/<int:notif_id>/leida/", views.notificacion_marcar_leida, name="core_notificacion_leida"),
    path("notificaciones/leidas/todas/", views.notificaciones_marcar_todas_leidas, name="core_notificaciones_todas_leidas"),
]
