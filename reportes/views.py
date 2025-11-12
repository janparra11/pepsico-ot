from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Count, Q, Sum
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from core.auth import require_roles
from core.roles import Rol
from core.models import AuditLog, Config
from ot.models import OrdenTrabajo, EstadoOT
from inventario.models import MovimientoStock


# ---------- utilidades ----------
def _nombre_archivo_reporte(request, base):
    hoy = timezone.localdate().strftime("%Y%m%d")
    estado = (request.GET.get("estado") or "todos").lower()
    return f"{base}_{hoy}_{estado}"

def _to_naive(dt):
    if not dt:
        return ""
    # pasa a hora local y quita tzinfo (Excel no soporta tz)
    return timezone.localtime(dt).replace(tzinfo=None)

def _stats_dashboard(qs_ot):
    """Calcula KPIs, top repuestos y top vehículos con claves uniformes."""
    # KPI abiertas/cerradas
    abiertas = qs_ot.filter(activa=True).count()
    cerradas = qs_ot.filter(activa=False).count()

    # tiempo promedio (solo cerradas con fecha_cierre)
    horas = []
    for ot in qs_ot.filter(activa=False, fecha_cierre__isnull=False).only("fecha_ingreso", "fecha_cierre"):
        diff = (ot.fecha_cierre - ot.fecha_ingreso).total_seconds() / 3600.0
        if diff >= 0:
            horas.append(diff)
    t_promedio = round(sum(horas) / len(horas), 2) if horas else 0.0

    # Top repuestos (si tienes 'cantidad' usa Sum; si no, Count)
    fields = [f.name for f in MovimientoStock._meta.get_fields()]
    agg = Sum("cantidad") if "cantidad" in fields else Count("id")
    top_repuestos = (
        MovimientoStock.objects
        .filter(tipo=MovimientoStock.SALIDA)
        .values("repuesto__codigo", "repuesto__descripcion")
        .annotate(total=agg)                 # <--- SIEMPRE 'total'
        .order_by("-total")
    )

    # Top vehículos (por OTs)
    top_vehiculos = (
        qs_ot.values("vehiculo__patente")
        .annotate(total=Count("id"))         # <--- SIEMPRE 'total'
        .order_by("-total")
    )

    return {
        "kpi_abiertas": abiertas,
        "kpi_cerradas": cerradas,
        "kpi_tiempo_prom": t_promedio,
        "top_repuestos": top_repuestos,
        "top_vehiculos": top_vehiculos,
    }


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


# ---------- vistas ----------
@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def dashboard_reportes(request):
    qs_ot, filtros = _parse_filters(request)
    stats = _stats_dashboard(qs_ot)
    cfg = Config.get_solo()

    # Paginaciones (Top 20 por página)
    page_r = request.GET.get("page_r") or 1
    page_v = request.GET.get("page_v") or 1
    page_o = request.GET.get("page_o") or 1

    rep_paginator = Paginator(stats["top_repuestos"], 20)
    veh_paginator = Paginator(stats["top_vehiculos"], 20)

    top_repuestos_page = rep_paginator.get_page(page_r)
    top_vehiculos_page = veh_paginator.get_page(page_v)

    ots_qs = qs_ot.select_related("vehiculo", "taller").only(
        "folio", "estado_actual", "activa", "fecha_ingreso", "fecha_cierre",
        "vehiculo__patente", "taller__nombre"
    ).order_by("-fecha_ingreso")
    ots_paginator = Paginator(ots_qs, 15)
    ots_page = ots_paginator.get_page(page_o)

    # Listas auxiliares para selects
    from taller.models import Taller
    from django.contrib.auth.models import User
    talleres = Taller.objects.all().order_by("nombre")
    mecanicos = User.objects.filter(is_active=True).order_by("username")

    ctx = {
        "cfg": cfg,  # nombre del taller para encabezados
        "filtros": filtros,
        "estados": EstadoOT.choices,
        "talleres": talleres,
        "mecanicos": mecanicos,

        "kpi_abiertas": stats["kpi_abiertas"],
        "kpi_cerradas": stats["kpi_cerradas"],
        "kpi_tiempo_prom": stats["kpi_tiempo_prom"],

        # paginados
        "top_repuestos": top_repuestos_page,
        "top_vehiculos": top_vehiculos_page,
        "ots_page": ots_page,
    }
    # ojo con el path del template
    return render(request, "reportes_dashboard.html", ctx)


# --- Exportaciones ---
@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def export_excel(request):
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter

    qs_ot, filtros = _parse_filters(request)
    stats = _stats_dashboard(qs_ot)
    cfg = Config.get_solo()

    wb = Workbook()

    # Hoja 1: Resumen
    ws = wb.active
    ws.title = "Resumen"
    ws.append([f"{cfg.nombre_taller} - Reporte de Órdenes de Trabajo"])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=7)
    ws.append([f"Generado: {timezone.localtime(timezone.now()).strftime('%d-%m-%Y %H:%M')}"])
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=7)
    ws.append([])

    ws.append(["Filtros"])
    ws.append(["Desde", filtros["fini"] or "(todos)"])
    ws.append(["Hasta", filtros["ffin"] or "(todos)"])
    ws.append(["Estado", filtros["estado"] or "(todos)"])
    ws.append(["Taller", filtros["taller"] or "(todos)"])
    ws.append(["Mecánico", filtros["mecanico"] or "(todos)"])
    ws.append([])

    ws.append(["KPIs"])
    ws.append(["OTs abiertas", stats["kpi_abiertas"]])
    ws.append(["OTs cerradas", stats["kpi_cerradas"]])
    ws.append(["Tiempo prom. reparación (h)", stats["kpi_tiempo_prom"]])

    # Hoja 2: OTs (detalle)
    ws2 = wb.create_sheet("OTs")
    headers = ["Folio", "Patente", "Estado", "Taller", "Ingreso", "Cierre", "Activa"]
    ws2.append(headers)

    for ot in qs_ot.select_related("vehiculo", "taller").only(
        "folio", "estado_actual", "activa", "fecha_ingreso", "fecha_cierre",
        "vehiculo__patente", "taller__nombre"
    ):
        ws2.append([
            ot.folio,
            getattr(ot.vehiculo, "patente", ""),
            ot.get_estado_actual_display(),
            getattr(ot.taller, "nombre", ""),
            _to_naive(ot.fecha_ingreso),
            _to_naive(ot.fecha_cierre),
            "Sí" if ot.activa else "No"
        ])

    for i in range(1, len(headers) + 1):
        ws2.column_dimensions[get_column_letter(i)].width = 18

    # Hoja 3: Top Repuestos
    ws3 = wb.create_sheet("Top Repuestos")
    ws3.append(["Código", "Descripción", "Total"])
    for r in stats["top_repuestos"][:50]:
        ws3.append([r["repuesto__codigo"], r["repuesto__descripcion"], r["total"]])
    ws3.column_dimensions["A"].width = 20
    ws3.column_dimensions["B"].width = 35
    ws3.column_dimensions["C"].width = 12

    # Hoja 4: Top Vehículos
    ws4 = wb.create_sheet("Top Vehículos")
    ws4.append(["Patente", "OTs"])
    for v in stats["top_vehiculos"][:50]:
        ws4.append([v["vehiculo__patente"], v["total"]])
    ws4.column_dimensions["A"].width = 20
    ws4.column_dimensions["B"].width = 10

    fname = _nombre_archivo_reporte(request, "reporte_ots") + ".xlsx"
    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    wb.save(resp)

    AuditLog.objects.create(app="REPORTES", action="EXPORT_EXCEL", user=request.user, extra=str(request.GET.dict()))
    return resp


@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def export_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import cm

    qs_ot, filtros = _parse_filters(request)
    stats = _stats_dashboard(qs_ot)
    cfg = Config.get_solo()

    resp = HttpResponse(content_type="application/pdf")
    fname = _nombre_archivo_reporte(request, "reporte_ots") + ".pdf"
    resp["Content-Disposition"] = f'attachment; filename="{fname}"'
    c = canvas.Canvas(resp, pagesize=A4)
    w, h = A4
    y = h - 2*cm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(2*cm, y, f"{cfg.nombre_taller} · Reporte de Órdenes de Trabajo")
    y -= 0.7*cm
    c.setFont("Helvetica", 10)
    c.drawString(2*cm, y, f"Generado: {timezone.localtime(timezone.now()).strftime('%d-%m-%Y %H:%M')}")
    y -= 0.6*cm

    # Filtros
    c.setFont("Helvetica-Bold", 10); c.drawString(2*cm, y, "Filtros:"); c.setFont("Helvetica", 10)
    y -= 0.5*cm
    c.drawString(2*cm, y, f"Desde: {filtros['fini'] or '(todos)'}   Hasta: {filtros['ffin'] or '(todos)'}")
    y -= 0.5*cm
    c.drawString(2*cm, y, f"Estado: {filtros['estado'] or '(todos)'}   Taller: {filtros['taller'] or '(todos)'}   Mecánico: {filtros['mecanico'] or '(todos)'}")
    y -= 0.8*cm

    # KPIs
    c.setFont("Helvetica-Bold", 10); c.drawString(2*cm, y, "KPIs:"); c.setFont("Helvetica", 10)
    y -= 0.5*cm
    c.drawString(2*cm, y, f"OTs abiertas: {stats['kpi_abiertas']}   OTs cerradas: {stats['kpi_cerradas']}   Tiempo prom: {stats['kpi_tiempo_prom']} h")
    y -= 0.8*cm

    # Top Repuestos
    c.setFont("Helvetica-Bold", 10); c.drawString(2*cm, y, "Top 10 Repuestos:"); c.setFont("Helvetica", 9)
    y -= 0.5*cm
    for r in stats["top_repuestos"][:10]:
        linea = f"{r['repuesto__codigo']} - {r['repuesto__descripcion']} ({r['total']})"
        c.drawString(2*cm, y, linea[:110]); y -= 0.45*cm
        if y < 2*cm:
            c.showPage(); y = h - 2*cm; c.setFont("Helvetica", 9)

    y -= 0.3*cm
    c.setFont("Helvetica-Bold", 10); c.drawString(2*cm, y, "Top 10 Vehículos:"); c.setFont("Helvetica", 9)
    y -= 0.5*cm
    for v in stats["top_vehiculos"][:10]:
        c.drawString(2*cm, y, f"{v['vehiculo__patente']} ({v['total']})"); y -= 0.45*cm
        if y < 2*cm:
            c.showPage(); y = h - 2*cm; c.setFont("Helvetica", 9)

    c.showPage()
    c.save()
    AuditLog.objects.create(app="REPORTES", action="EXPORT_PDF", user=request.user, extra=str(request.GET.dict()))
    return resp
