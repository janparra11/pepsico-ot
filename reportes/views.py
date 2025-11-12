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
from django.db.models.functions import TruncDate
from django.db.models import Count, Avg
from django.db.models import DurationField, ExpressionWrapper, F


# ---------- utilidades ----------
def _nombre_archivo_reporte(request, base, filtros=None):
    hoy = timezone.localdate().strftime("%Y%m%d")
    estado = (request.GET.get("estado") or "todos").lower()
    extra = ""
    if filtros:
        fi = (filtros.get("fini") or "").replace("-", "")
        ff = (filtros.get("ffin") or "").replace("-", "")
        if fi or ff:
            extra += f"_{fi or 'all'}-{ff or 'all'}"
        rango = filtros.get("rango") or ""
        if rango:
            extra += f"_{rango}"
    return f"{base}_{hoy}_{estado}{extra}"

def _to_naive(dt):
    if not dt:
        return ""
    # pasa a hora local y quita tzinfo (Excel no soporta tz)
    return timezone.localtime(dt).replace(tzinfo=None)

def _stats_dashboard(qs_ot, global_top_veh=False):
    """
    Calcula KPIs y tops.
    - Top repuestos siempre usa clave 'total' (Sum(cantidad) o Count(id)).
    - Top vehículos:
        * Si global_top_veh=True -> ignora filtros (histórico).
        * Si global_top_veh=False -> respeta filtros (qs_ot).
    """
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

    # Top repuestos (si tienes 'cantidad' usa Sum; si no, Count) -> SIEMPRE 'total'
    fields = [f.name for f in MovimientoStock._meta.get_fields()]
    agg = Sum("cantidad", default=0) if "cantidad" in fields else Count("id")
    top_repuestos = (
        MovimientoStock.objects
        .filter(tipo=MovimientoStock.SALIDA)
        .values("repuesto__codigo", "repuesto__descripcion")
        .annotate(total=agg)
        .order_by("-total")
    )

    # Top vehículos (por OTs) -> 'total'
    base_veh = OrdenTrabajo.objects.all() if global_top_veh else qs_ot
    top_vehiculos = (
        base_veh.values("vehiculo__patente")
        .annotate(total=Count("id"))
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
    f_ini = (request.GET.get("fini") or "").strip()
    f_fin = (request.GET.get("ffin") or "").strip()
    rango = (request.GET.get("rango") or "").strip()  # 'hoy' | 'ult7' | 'mes' | ''

    # si NO vienen fechas manuales, aplicamos rango rápido
    if not f_ini and not f_fin and rango:
        hoy = timezone.localdate()
        if rango == "hoy":
            f_ini = hoy.isoformat()
            f_fin = hoy.isoformat()
        elif rango == "ult7":
            f_ini = (hoy - timezone.timedelta(days=6)).isoformat()
            f_fin = hoy.isoformat()
        elif rango == "mes":
            primero_mes = hoy.replace(day=1)
            f_ini = primero_mes.isoformat()
            f_fin = hoy.isoformat()

    estado = (request.GET.get("estado") or "").strip()
    taller = (request.GET.get("taller") or "").strip()
    mecanico_id = (request.GET.get("mecanico") or "").strip()

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

    filtros = {
        "fini": f_ini, "ffin": f_fin, "rango": rango,
        "estado": estado, "taller": taller, "mecanico": mecanico_id
    }
    return qs_ot, filtros


# ---------- vistas ----------
@login_required
@require_roles(Rol.SUPERVISOR, Rol.JEFE_TALLER, Rol.ADMIN)
def dashboard_reportes(request):
    qs_ot, filtros = _parse_filters(request)
    # En pantalla: Top vehículos respetando filtros
    stats = _stats_dashboard(qs_ot, global_top_veh=False)
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
    # ojo con el path del template (carpeta reportes/)
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
    # Si hay rango rápido, muéstralo
    if filtros.get("rango"):
        ws.append(["Rango rápido", {"hoy":"Hoy","ult7":"Últimos 7 días","mes":"Este mes"}.get(filtros["rango"], filtros["rango"])])
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

    # anchos + formato de fecha
    for i in range(1, len(headers) + 1):
        ws2.column_dimensions[get_column_letter(i)].width = 18
    # Formato fecha/hora ISO
    for row in ws2.iter_rows(min_row=2, min_col=5, max_col=6):
        for cell in row:
            if cell.value:
                cell.number_format = "yyyy-mm-dd hh:mm"

    # Hoja 3: Top Repuestos
    ws3 = wb.create_sheet("Top Repuestos")
    ws3.append(["Código", "Descripción", "Total"])
    for r in stats["top_repuestos"][:50]:
        ws3.append([r["repuesto__codigo"], r["repuesto__descripcion"], r["total"]])
    ws3.column_dimensions["A"].width = 20
    ws3.column_dimensions["B"].width = 35
    ws3.column_dimensions["C"].width = 14
    # formato con miles y hasta 2 decimales
    for cell in ws3["C"][1:]:
        cell.number_format = "#,##0.##"

    # Hoja 4: Top Vehículos
    ws4 = wb.create_sheet("Top Vehículos")
    ws4.append(["Patente", "OTs"])
    for v in stats["top_vehiculos"][:50]:
        ws4.append([v["vehiculo__patente"], v["total"]])
    ws4.column_dimensions["A"].width = 20
    ws4.column_dimensions["B"].width = 10
    for cell in ws4["B"][1:]:
        cell.number_format = "#,##0"

    # === Hoja 5: Resumen por estado ===
    from django.db.models import DurationField, ExpressionWrapper, F, Avg

    ws5 = wb.create_sheet("Resumen por estado")
    ws5.append(["Estado", "OTs", "Tiempo prom. (h)"])

    # Solo OTs cerradas con fechas válidas; calculamos duración como timedelta
    cerradas = qs_ot.filter(
        activa=False,
        fecha_cierre__isnull=False,
        fecha_cierre__gte=F("fecha_ingreso")
    ).annotate(
        dur_td=ExpressionWrapper(F("fecha_cierre") - F("fecha_ingreso"), output_field=DurationField())
    )

    # Agrupamos por estado_actual (usa SIEMPRE la clave 'total' y una media de dur_td)
    resumen = (
        cerradas.values("estado_actual")
        .annotate(total=Count("id"), prom_td=Avg("dur_td"))
        .order_by("estado_actual")
    )

    # Mapeo para mostrar el label del estado
    estado_map = dict(EstadoOT.choices)

    for r in resumen:
        # prom_td es timedelta o None
        if r["prom_td"] is None:
            prom_h = ""
        else:
            prom_h = round(r["prom_td"].total_seconds() / 3600.0, 2)
        ws5.append([
            estado_map.get(r["estado_actual"], r["estado_actual"]),
            r["total"],
            prom_h
        ])

    # Anchos y formatos
    ws5.column_dimensions["A"].width = 28
    ws5.column_dimensions["B"].width = 10
    ws5.column_dimensions["C"].width = 18
    for cell in ws5["B"][2:]:
        cell.number_format = "#,##0"
    for cell in ws5["C"][2:]:
        cell.number_format = "#,##0.00"
    
    # --- Hoja 6: Resumen por taller ---
    # Promedio de duración solo sobre OTs cerradas válidas (sin negativas)
    cerradas_ok = qs_ot.filter(
        activa=False,
        fecha_cierre__isnull=False,
        fecha_cierre__gte=F("fecha_ingreso"),
    ).annotate(
        dur_td=ExpressionWrapper(F("fecha_cierre") - F("fecha_ingreso"), output_field=DurationField())
    )

    # Agregados por taller
    agg_base = qs_ot.values("taller__nombre").annotate(
        total_ots=Count("id"),
        abiertas=Count("id", filter=Q(activa=True)),
        cerradas=Count("id", filter=Q(activa=False)),
    ).order_by("taller__nombre")

    # Promedio de duración (timedelta) por taller, lo convertimos a horas
    dur_prom_map = {
        r["taller__nombre"] or "—": (r["avg_dur"].total_seconds() / 3600.0) if r["avg_dur"] else 0.0
        for r in cerradas_ok.values("taller__nombre").annotate(avg_dur=Avg("dur_td"))
    }

    wsT = wb.create_sheet("Resumen por taller")
    wsT.append(["Taller", "OTs totales", "Abiertas", "Cerradas", "Tiempo prom. (h)"])

    for row in agg_base:
        nombre = row["taller__nombre"] or "—"
        wsT.append([
            nombre,
            row["total_ots"],
            row["abiertas"],
            row["cerradas"],
            round(dur_prom_map.get(nombre, 0.0), 2),
        ])

    # Anchos + formatos
    from openpyxl.utils import get_column_letter as _gcl
    for i, w in enumerate([30, 14, 12, 12, 18], start=1):
        wsT.column_dimensions[_gcl(i)].width = w

    for cell in wsT["B"][1:]:
        cell.number_format = "#,##0"
    for cell in wsT["C"][1:]:
        cell.number_format = "#,##0"
    for cell in wsT["D"][1:]:
        cell.number_format = "#,##0"
    for cell in wsT["E"][1:]:
        cell.number_format = "0.00"

    # nombre con rango/fechas
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
    fname = _nombre_archivo_reporte(request, "reporte_ots", filtros) + ".pdf"
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
    if filtros.get("rango"):
        etiqueta = {"hoy":"Hoy","ult7":"Últimos 7 días","mes":"Este mes"}.get(filtros["rango"], filtros["rango"])
        c.drawString(2*cm, y, f"Rango rápido: {etiqueta}")
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
