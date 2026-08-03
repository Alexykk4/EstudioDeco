"""
modules/pdf_report.py
Genera el PDF del Corte de Caja diario usando FPDF2.
"""

from fpdf import FPDF
from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"

# Colores pastel del branding
AZUL_PASTEL = (174, 198, 207)     # #AEC6CF
MORADO_PASTEL = (179, 157, 219)   # #B39DDB
GRIS_CLARO = (245, 245, 250)


class CortePDF(FPDF):
    def header(self):
        # Logo
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=10, y=8, w=25)
        # Título
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*MORADO_PASTEL)
        self.cell(0, 10, "Estudio Deco", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, "Corte de Caja", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)
        # Línea decorativa
        self.set_draw_color(*AZUL_PASTEL)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="L")
        self.cell(0, 10, f"Página {self.page_no()}", align="R")


def generar_corte_pdf(resumen: dict, cajero: str, ventas_turno: list = None) -> str:
    """
    Genera un PDF con el resumen del corte de caja.
    ventas_turno: lista de dicts de ventas individuales del turno (opcional).
    Retorna la ruta absoluta del archivo generado.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fecha = resumen["fecha"]
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"Corte_{timestamp}.pdf"
    filepath = REPORTS_DIR / filename

    pdf = CortePDF()
    pdf.add_page()

    # ── INFO GENERAL ──
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(95, 8, f"Fecha: {fecha}")
    pdf.cell(95, 8, f"Cajero: {cajero}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 8, f"Num. Ventas: {resumen['num_ventas']}")
    pdf.ln(10)

    # ── VENTAS POR TIENDA ──
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 8, "Ventas por Tienda", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Encabezado tabla
    pdf.set_fill_color(*AZUL_PASTEL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(120, 8, "  Tienda", fill=True)
    pdf.cell(70, 8, "Total", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    # Filas
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 10)
    fill = False
    for vt in resumen.get("ventas_por_tienda", []):
        if fill:
            pdf.set_fill_color(*GRIS_CLARO)
        pdf.cell(120, 7, f"  {vt['tienda']}", fill=fill)
        pdf.cell(70, 7, f"${vt['total']:,.2f}  ", fill=fill, align="R",
                 new_x="LMARGIN", new_y="NEXT")
        fill = not fill

    # Total ventas
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(*MORADO_PASTEL)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(120, 8, "  TOTAL VENTAS", fill=True)
    pdf.cell(70, 8, f"${resumen['total_ventas']:,.2f}  ", fill=True, align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # ── DETALLE DE VENTAS DEL TURNO ──
    if ventas_turno:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*MORADO_PASTEL)
        pdf.cell(0, 8, "Detalle de Ventas del Turno", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Encabezados
        pdf.set_fill_color(*AZUL_PASTEL)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(18, 8, " FOLIO", fill=True)
        pdf.cell(13, 8, "FECHA", fill=True, align="C")
        pdf.cell(27, 8, "CUENTA", fill=True, align="C")
        pdf.cell(16, 8, "IRC DESC.", fill=True, align="R")
        pdf.cell(13, 8, "PROP.", fill=True, align="R")
        pdf.cell(17, 8, "IMPORTE", fill=True, align="R")
        pdf.cell(18, 8, "EFECTIVO", fill=True, align="R")
        pdf.cell(18, 8, "TARJETA", fill=True, align="R")
        pdf.cell(18, 8, "CXC", fill=True, align="R")
        pdf.cell(32, 8, "MONTO MENOS COMISIÓN", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 7)
        fill = False
        
        sum_importe = 0.0
        sum_efectivo = 0.0
        sum_tarjeta = 0.0
        sum_cxc = 0.0
        sum_neto = 0.0

        for v in ventas_turno:
            if fill:
                pdf.set_fill_color(*GRIS_CLARO)

            folio_short = v.get("folio", "")
            if len(folio_short) > 12:
                folio_short = folio_short[-8:]

            hora = ""
            created = v.get("created_at", "")
            if created and len(created) >= 16:
                hora = created[11:16]

            # Determine the account or table name
            if v.get("mesa_numero"):
                cuenta_str = f"Mesa {v['mesa_numero']}"
            else:
                cuenta_str = "Venta Directa"

            metodo = v.get("metodo_pago", "Efectivo")
            total_venta = v.get("total", 0)
            monto_tarjeta = v.get("monto_tarjeta", 0)
            monto_efectivo = v.get("monto_efectivo", 0)

            # Determine CXC / Efectivo / Tarjeta amounts based on method
            val_efvo = monto_efectivo if metodo in ["Efectivo", "Mixto"] else 0.0
            val_tarj = monto_tarjeta if metodo in ["Tarjeta", "Mixto"] else 0.0
            val_cxc  = total_venta if metodo in ["Transferencia", "Transfer"] else 0.0

            # Assuming 0 for these columns explicitly requested without DB support
            val_irc = 0.0
            val_prop = 0.0

            # Calcular comisión según método de pago
            if metodo == "Tarjeta":
                comision = round(total_venta * 0.04, 2)
            elif metodo == "Mixto" and total_venta > 0:
                comision = round(monto_tarjeta * 0.04, 2)
            else:
                comision = 0.0

            neto = total_venta - comision
            sum_importe += total_venta
            sum_efectivo += val_efvo
            sum_tarjeta += val_tarj
            sum_cxc += val_cxc
            sum_neto += neto

            pdf.cell(18, 7, f" {folio_short}", fill=fill)
            pdf.cell(13, 7, hora, fill=fill, align="C")
            pdf.cell(27, 7, cuenta_str[:15], fill=fill, align="C")
            
            pdf.cell(16, 7, f"${val_irc:,.2f}", fill=fill, align="R")
            pdf.cell(13, 7, f"${val_prop:,.2f}", fill=fill, align="R")
            
            pdf.cell(17, 7, f"${total_venta:,.2f}", fill=fill, align="R")
            pdf.cell(18, 7, f"${val_efvo:,.2f}", fill=fill, align="R")
            pdf.cell(18, 7, f"${val_tarj:,.2f}", fill=fill, align="R")
            pdf.cell(18, 7, f"${val_cxc:,.2f}", fill=fill, align="R")
            
            pdf.cell(32, 7, f"${neto:,.2f}", fill=fill, align="R", new_x="LMARGIN", new_y="NEXT")

            # Detallar items debajo
            items = v.get("items", [])
            if items:
                pdf.set_font("Helvetica", "I", 7)
                pdf.set_text_color(120, 120, 120)
                items_desc = ", ".join(
                    f"{i.get('nombre_producto', i.get('nombre','?'))} x{i.get('cantidad',1)}"
                    for i in items[:5]
                )
                if len(items) > 5:
                    items_desc += f" (+{len(items)-5} más)"
                pdf.cell(190, 5, f"    {items_desc}",
                         new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(60, 60, 60)

            fill = not fill

        # Totales del detalle
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(*MORADO_PASTEL)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(58, 8, "  TOTALES", fill=True)
        pdf.cell(16, 8, "$0.00", fill=True, align="R")
        pdf.cell(13, 8, "$0.00", fill=True, align="R")
        pdf.cell(17, 8, f"${sum_importe:,.2f}", fill=True, align="R")
        pdf.cell(18, 8, f"${sum_efectivo:,.2f}", fill=True, align="R")
        pdf.cell(18, 8, f"${sum_tarjeta:,.2f}", fill=True, align="R")
        pdf.cell(18, 8, f"${sum_cxc:,.2f}", fill=True, align="R")
        pdf.cell(32, 8, f"${sum_neto:,.2f}", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

    # ── INGRESOS ──
    ingresos_det = resumen.get("ingresos_detalle", [])
    if ingresos_det:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*MORADO_PASTEL)
        pdf.cell(0, 8, "Ingresos / Entradas", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_fill_color(*AZUL_PASTEL)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(65, 8, "  Concepto", fill=True)
        pdf.cell(45, 8, "Destino", fill=True, align="C")
        pdf.cell(40, 8, u"M\xe9todo", fill=True, align="C")
        pdf.cell(40, 8, "Monto", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 9)
        fill = False
        for ing in ingresos_det:
            if fill:
                pdf.set_fill_color(*GRIS_CLARO)
            pdf.cell(65, 7, f"  {ing['concepto'][:30]}", fill=fill)
            pdf.cell(45, 7, ing.get("tienda", "-"), fill=fill, align="C")
            pdf.cell(40, 7, ing.get("metodo_pago", "Efectivo"), fill=fill, align="C")
            pdf.cell(40, 7, f"${ing['monto']:,.2f}  ", fill=fill, align="R",
                     new_x="LMARGIN", new_y="NEXT")
            fill = not fill

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(150, 200, 150)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(150, 8, "  TOTAL INGRESOS", fill=True)
        pdf.cell(40, 8, f"${resumen.get('total_ingresos', 0):,.2f}  ", fill=True, align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

    # ── GASTOS ──
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 8, "Gastos / Salidas", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_fill_color(*AZUL_PASTEL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(55, 8, "  Concepto", fill=True)
    pdf.cell(40, 8, "Tienda", fill=True, align="C")
    pdf.cell(30, 8, u"Categor\xeda", fill=True, align="C")
    pdf.cell(25, 8, "Origen", fill=True, align="C")
    pdf.cell(40, 8, "Monto", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 9)
    fill = False
    for g in resumen.get("gastos_detalle", []):
        if fill:
            pdf.set_fill_color(*GRIS_CLARO)
        pdf.cell(55, 7, f"  {g['concepto'][:25]}", fill=fill)
        pdf.cell(40, 7, g.get("tienda", "General"), fill=fill, align="C")
        pdf.cell(30, 7, g["categoria"], fill=fill, align="C")
        pdf.cell(25, 7, g.get("origen", "Caja"), fill=fill, align="C")
        pdf.cell(40, 7, f"${g['monto']:,.2f}  ", fill=fill, align="R",
                 new_x="LMARGIN", new_y="NEXT")
        fill = not fill

    if not resumen.get("gastos_detalle"):
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "  Sin gastos registrados", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(220, 150, 150)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(150, 8, "  TOTAL GASTOS", fill=True)
    pdf.cell(40, 8, f"${resumen['total_gastos']:,.2f}  ", fill=True, align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # ── MÉTODOS DE PAGO ──
    metodos = resumen.get("metodos_pago", [])
    if metodos:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*MORADO_PASTEL)
        pdf.cell(0, 8, "Ingresos por Método de Pago", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_fill_color(*AZUL_PASTEL)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(120, 8, "  Método de Pago", fill=True)
        pdf.cell(70, 8, "Monto", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(60, 60, 60)
        pdf.set_font("Helvetica", "", 10)
        fill = False
        for m in metodos:
            if fill:
                pdf.set_fill_color(*GRIS_CLARO)
            pdf.cell(120, 7, f"  {m['metodo_pago']}", fill=fill)
            pdf.cell(70, 7, f"${m['monto']:,.2f}  ", fill=fill, align="R",
                     new_x="LMARGIN", new_y="NEXT")
            fill = not fill
        pdf.ln(8)

    # ── DESGLOSE DE EFECTIVO ──
    desglose = resumen.get("desglose_billetes", {})
    fondo    = resumen.get("fondo_caja", 0.0)

    if desglose or fondo > 0:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*MORADO_PASTEL)
        pdf.cell(0, 8, "Desglose de Efectivo Contado", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        NOMBRES = {}
        for d in [1000, 500, 200, 100, 50, 20]:
            NOMBRES[f"B{d}"] = f"Billete ${d:,}"
        for d in [10, 5, 2, 1]:
            NOMBRES[f"M{d}"] = f"Moneda ${d}"
        NOMBRES["M0.5"] = "Moneda $0.50"

        if desglose:
            # Encabezado tabla
            pdf.set_fill_color(*AZUL_PASTEL)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(100, 8, "  Denominación", fill=True)
            pdf.cell(45, 8, "Cantidad", fill=True, align="C")
            pdf.cell(45, 8, "Subtotal", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

            pdf.set_text_color(60, 60, 60)
            pdf.set_font("Helvetica", "", 10)
            fill = False
            total_contado = 0.0
            for key, qty in desglose.items():
                try:
                    denom = float(key[1:])
                except ValueError:
                    continue
                subtotal = denom * qty
                total_contado += subtotal
                nombre = NOMBRES.get(key, key)
                if fill:
                    pdf.set_fill_color(*GRIS_CLARO)
                pdf.cell(100, 7, f"  {nombre}", fill=fill)
                pdf.cell(45, 7, str(qty), fill=fill, align="C")
                pdf.cell(45, 7, f"${subtotal:,.2f}  ", fill=fill, align="R",
                         new_x="LMARGIN", new_y="NEXT")
                fill = not fill

            # Total contado
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(200, 230, 200)
            pdf.set_text_color(40, 100, 40)
            pdf.cell(100, 8, "  Total contado", fill=True)
            pdf.cell(45, 8, "", fill=True)
            pdf.cell(45, 8, f"${total_contado:,.2f}  ", fill=True, align="R",
                     new_x="LMARGIN", new_y="NEXT")
        else:
            total_contado = resumen.get("efectivo_real", 0.0) + fondo

        # Fondo de caja
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(145, 7, "  Menos fondo de caja inicial:")
        pdf.cell(45, 7, f"-${fondo:,.2f}  ", align="R", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(145, 7, "  Efectivo real (ventas):")
        pdf.cell(45, 7, f"${resumen.get('efectivo_real', 0):,.2f}  ", align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(8)

    # ── RESUMEN FINAL ──
    pdf.set_draw_color(*AZUL_PASTEL)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(120, 8, "Efectivo Esperado en Caja:")
    pdf.cell(70, 8, f"${resumen['efectivo_esperado']:,.2f}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    efectivo_real = resumen.get("efectivo_real", 0)
    pdf.cell(120, 8, "Efectivo Real (ventas):")
    pdf.cell(70, 8, f"${efectivo_real:,.2f}", align="R",
             new_x="LMARGIN", new_y="NEXT")

    dif = resumen.get("diferencia", 0)
    pdf.set_font("Helvetica", "B", 14)
    color_dif = (0, 150, 0) if dif >= 0 else (200, 50, 50)
    pdf.set_text_color(*color_dif)
    signo = "+" if dif >= 0 else ""
    pdf.cell(120, 10, "Diferencia:")
    pdf.cell(70, 10, f"{signo}${dif:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")

    # Guardar
    pdf.output(str(filepath))
    
    # Abrir el PDF de manera automática para la vista del usuario
    import os
    try:
        os.startfile(str(filepath))
    except Exception as e:
        print(f"No se pudo abrir automáticamente el PDF: {e}")
        
    return str(filepath)


def generar_nomina_pdf(nomina: dict, cajero: str) -> str:
    """Genera un comprobante PDF de pago de nomina."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_safe = nomina['nombre_empleado'].replace(' ', '_')
    filename = f"Nomina_{nombre_safe}_{timestamp}.pdf"
    filepath = REPORTS_DIR / filename

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=85, y=15, w=30)
    pdf.ln(35)

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 10, "Estudio Deco", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "Comprobante de Pago de Nomina", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_draw_color(*MORADO_PASTEL)
    pdf.set_line_width(1.0)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    pdf.set_fill_color(*GRIS_CLARO)
    pdf.set_draw_color(*AZUL_PASTEL)
    pdf.set_line_width(0.5)
    pdf.rect(20, pdf.get_y(), 170, 75, style='FD')
    pdf.ln(6)

    def fila(etiqueta, valor):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(120, 90, 180)
        pdf.cell(70, 10, f"  {etiqueta}:")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(100, 10, str(valor), new_x="LMARGIN", new_y="NEXT")

    fila("Empleado", nomina['nombre_empleado'])
    fila("Concepto", nomina['concepto'])
    fila("Fecha", nomina['created_at'][:16])
    fila("Metodo de Pago", nomina['metodo_pago'])
    fila("Registrado por", cajero)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, "MONTO PAGADO", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 34)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 18, f"${nomina['monto']:,.2f}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_draw_color(*AZUL_PASTEL)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 6, f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Folio #{nomina['id']}", align="C")

    pdf.output(str(filepath))
    return str(filepath)


def generar_ventas_dia_pdf(fecha: str, ventas: list) -> str:
    """PDF de ventas de un día específico (activas + canceladas)."""
    REPORTS_DIR.mkdir(exist_ok=True)
    safe = fecha.replace("-", "")
    filepath = REPORTS_DIR / f"ventas_dia_{safe}.pdf"

    activas = [v for v in ventas if not v.get("cancelada")]
    total = sum(float(v.get("total") or 0) for v in activas)
    ef = sum(float(v.get("total") or 0) for v in activas if v.get("metodo_pago") == "Efectivo")
    tar = sum(float(v.get("total") or 0) for v in activas if v.get("metodo_pago") == "Tarjeta")
    trn = sum(float(v.get("total") or 0) for v in activas if v.get("metodo_pago") == "Transferencia")
    mix = sum(float(v.get("total") or 0) for v in activas if v.get("metodo_pago") == "Mixto")

    pdf = CortePDF()
    pdf.add_page()
    # Override subtitle area
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 8, f"Reporte de Ventas - {fecha}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, f"Tickets activos: {len(activas)}   |   Total: ${total:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Efectivo: ${ef:,.2f}   |   Tarjeta: ${tar:,.2f}   |   Transferencia: ${trn:,.2f}   |   Mixto: ${mix:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*AZUL_PASTEL)
    pdf.set_text_color(40, 40, 40)
    cols = [("Hora", 18), ("Folio", 38), ("Cajero", 32), ("Metodo", 28), ("Total", 28), ("Estado", 26)]
    for label, w in cols:
        pdf.cell(w, 8, label, border=0, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for v in ventas:
        hora = str(v.get("created_at") or "")[11:16]
        estado = "CANCELADA" if v.get("cancelada") else "OK"
        pdf.set_text_color(180, 40, 40) if v.get("cancelada") else pdf.set_text_color(40, 40, 40)
        pdf.cell(18, 6, hora)
        pdf.cell(38, 6, str(v.get("folio") or "")[:18])
        pdf.cell(32, 6, str(v.get("cajero_nombre") or "")[:16])
        pdf.cell(28, 6, str(v.get("metodo_pago") or "")[:14])
        pdf.cell(28, 6, f"${float(v.get('total') or 0):,.2f}")
        pdf.cell(26, 6, estado)
        pdf.ln()
        items = v.get("items") or []
        if items:
            pdf.set_text_color(110, 110, 110)
            desc = "; ".join(
                f"{it.get('nombre_producto','')} x{it.get('cantidad',1)}" for it in items
            )[:110]
            pdf.cell(0, 5, f"  {desc}", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(filepath))
    return str(filepath)


def generar_ventas_dia_csv(fecha: str, ventas: list) -> str:
    """CSV de ventas del día (UTF-8 BOM para Excel)."""
    import csv
    REPORTS_DIR.mkdir(exist_ok=True)
    safe = fecha.replace("-", "")
    filepath = REPORTS_DIR / f"ventas_dia_{safe}.csv"
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "fecha", "hora", "folio", "cajero", "metodo_pago",
            "monto_efectivo", "monto_tarjeta", "total", "cancelada", "items",
        ])
        for v in ventas:
            created = str(v.get("created_at") or "")
            items = v.get("items") or []
            items_txt = "; ".join(
                f"{it.get('nombre_producto','')} x{it.get('cantidad',1)} @{float(it.get('precio_unitario') or 0):.2f}"
                for it in items
            )
            w.writerow([
                created[:10],
                created[11:16],
                v.get("folio") or "",
                v.get("cajero_nombre") or "",
                v.get("metodo_pago") or "",
                f"{float(v.get('monto_efectivo') or 0):.2f}",
                f"{float(v.get('monto_tarjeta') or 0):.2f}",
                f"{float(v.get('total') or 0):.2f}",
                1 if v.get("cancelada") else 0,
                items_txt,
            ])
    return str(filepath)
