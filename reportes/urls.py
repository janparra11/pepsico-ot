from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_reportes, name="reportes_dashboard"),
    path("export/excel/", views.export_excel, name="reportes_export_excel"),
    path("export/pdf/", views.export_pdf, name="reportes_export_pdf"),
]
