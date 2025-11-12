from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.healthcheck, name="healthcheck"),
    path("notificaciones/", views.notificaciones_lista, name="core_notificaciones"),
    path("notificaciones/<int:notif_id>/", views.notificacion_detalle, name="core_notificacion_detalle"),  # ← nuevo
    path("notificaciones/<int:notif_id>/leida/", views.notificacion_marcar_leida, name="core_notificacion_leida"),
    path("notificaciones/leidas/todas/", views.notificaciones_marcar_todas_leidas, name="core_notificaciones_todas_leidas"),
    path("logout/", views.logout_view, name="logout"),
    path("agenda/", views.agenda_view, name="core_agenda"),
    path("agenda/events/", views.agenda_events_api, name="core_agenda_api"),
    path("agenda/create/", views.agenda_crear_api, name="core_agenda_crear_api"),
    path("agenda/event/<int:ev_id>/", views.agenda_detalle_api, name="core_agenda_detalle_api"),
    path("notificaciones/unread-count/", views.notif_unread_count, name="core_notif_unread_count"),
    path("redir/", views.redir_por_rol, name="redir_por_rol"),
    path("usuarios/", views.users_admin_list, name="users_admin_list"),
    path("usuarios/nuevo/", views.users_admin_create, name="users_admin_create"),
    path("usuarios/<int:user_id>/rol/", views.users_admin_set_role, name="users_admin_set_role"),
    path("usuarios/<int:user_id>/activar/", views.users_admin_toggle_active, name="users_admin_toggle_active"),
    path("usuarios/<int:user_id>/reset-pass/", views.users_admin_reset_password, name="users_admin_reset_password"),
    path("config/", admin_views.config_view, name="core_config"),
    path("logs/", admin_views.logs_view, name="core_logs"),
    path("backup/media.zip", admin_views.backup_media_zip, name="core_backup_media"),
    path("core/logs/<int:pk>/", admin_views.logs_detail, name="core_logs_detail"),
]
