from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Count, Q, Sum
from django.contrib.auth.decorators import login_required

from core.auth import require_roles
from core.roles import Rol
from ot.models import OrdenTrabajo, EstadoOT
from inventario.models import MovimientoStock

# --- Filtros utilitarios ---
def _parse_filters(request):
    # yyyy-mm-dd
    f_ini = request.GET.get("fini", "").strip()
    f_fin = request.GET.get("ffin", "").strip()
    estado = request.GET.get("estado", "").strip()
    taller = request.GET.get("taller", "").strip()
    mecanico_id = request.GET.get("mecanico", "").strip()

    qs_ot = OrdenTrabajo.objects.all()

    if f_ini:
        qs_ot = qs_ot.filter(fecha_ingreso__date__gte=f_ini)
    if f_fin:
        qs_ot = qs_ot.filter(fecha_ingreso__date__lte=f_fin)
    if estado:
        qs_ot = qs_ot.filter(estado_actual=estado)
    if taller:
        qs_ot = qs_ot.filter(taller_id=taller)
    if mecanico_id:
        qs_ot = qs_ot.filter(mecanico_asignado_id=mecanico_id)

    return qs_ot, {"fini": f_ini, "ffin": f_fin, "estado": estado, "taller": taller, "mecanico": mecanico_id}

@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def dashboard_reportes(request):
    qs_ot, filtros = _parse_filters(request)

    # Totales
    abiertas = qs_ot.filter(activa=True).count()
    cerradas = qs_ot.filter(activa=False).count()

    # Tiempo promedio de reparación (solo cerradas con fecha_cierre válida)
    cerradas_qs = qs_ot.filter(activa=False, fecha_cierre__isnull=False).only("fecha_ingreso", "fecha_cierre")
    horas = []
    for ot in cerradas_qs:
        diff = (ot.fecha_cierre - ot.fecha_ingreso).total_seconds() / 3600.0
        if diff >= 0:
            horas.append(diff)
    t_promedio = round(sum(horas) / len(horas), 2) if horas else 0.0

    # Repuestos más usados
    # Preferimos sumar la "cantidad" si tu modelo la tiene (Decimal/Float). Si no, cae en conteo.
    try:
        top_repuestos = (
            MovimientoStock.objects
            .filter(tipo=MovimientoStock.SALIDA)
            .values("repuesto__codigo", "repuesto__descripcion")
            .annotate(movs=Count("id"), cantidad_total=Sum("cantidad"))
            .order_by("-cantidad_total", "-movs")[:10]
        )
    except Exception:
        # Fallback si no existe el campo cantidad
        top_repuestos = (
            MovimientoStock.objects
            .filter(tipo=MovimientoStock.SALIDA)
            .values("repuesto__codigo", "repuesto__descripcion")
            .annotate(movs=Count("id"))
            .order_by("-movs")[:10]
        )

    # Vehículos más frecuentes (por OTs)
    top_vehiculos = (
        qs_ot.values("vehiculo__patente")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # Listas auxiliares para selects
    from taller.models import Taller
    from django.contrib.auth.models import User
    talleres = Taller.objects.all().order_by("nombre")
    mecanicos = User.objects.filter(is_active=True).order_by("username")

    ctx = {
        "filtros": filtros,
        "estados": EstadoOT.choices,
        "talleres": talleres,
        "mecanicos": mecanicos,

        "kpi_abiertas": abiertas,
        "kpi_cerradas": cerradas,
        "kpi_tiempo_prom": t_promedio,

        "top_repuestos": top_repuestos,
        "top_vehiculos": top_vehiculos,
    }
    return render(request, "reportes_dashboard.html", ctx)


# --- Exportaciones ---
@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def export_excel(request):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    def _naive(dt):
        if not dt:
            return ""
        # Convierte a zona local y elimina tzinfo
        return timezone.localtime(dt).replace(tzinfo=None)

    qs_ot, _ = _parse_filters(request)
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte OTs"

    headers = ["Folio", "Patente", "Estado", "Taller", "Ingreso", "Cierre", "Activa"]
    ws.append(headers)

    for ot in qs_ot.select_related("vehiculo", "taller"):
        ws.append([
            ot.folio,
            getattr(ot.vehiculo, "patente", ""),
            ot.get_estado_actual_display(),
            getattr(ot.taller, "nombre", ""),
            _naive(ot.fecha_ingreso),
            _naive(ot.fecha_cierre),
            "Sí" if ot.activa else "No",
        ])

    for i, _ in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(i)].width = 18

    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    resp["Content-Disposition"] = 'attachment; filename="reporte_ots.xlsx"'
    wb.save(resp)
    return resp


@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def export_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm

    qs_ot, _ = _parse_filters(request)

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="reporte_ots.pdf"'
    c = canvas.Canvas(resp, pagesize=A4)
    w, h = A4

    y = h - 2*cm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, "Reporte de Órdenes de Trabajo")
    y -= 0.7*cm

    c.setFont("Helvetica", 10)
    c.drawString(2*cm, y, f"Total: {qs_ot.count()}  ·  Generado: {timezone.now().strftime('%d-%m-%Y %H:%M')}")
    y -= 1.0*cm

    c.setFont("Helvetica", 9)
    for ot in qs_ot.select_related("vehiculo", "taller")[:40]:
        linea = f"{ot.folio} · {getattr(ot.vehiculo,'patente','')} · {ot.get_estado_actual_display()} · {getattr(ot.taller,'nombre','')} · {ot.fecha_ingreso.strftime('%d-%m-%Y %H:%M')}"
        c.drawString(2*cm, y, linea[:110])
        y -= 0.55*cm
        if y < 2*cm:
            c.showPage(); y = h - 2*cm
            c.setFont("Helvetica", 9)

    c.showPage()
    c.save()
    return resp
