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


def generar_corte_pdf(resumen: dict, cajero: str) -> str:
    """
    Genera un PDF con el resumen del corte de caja.
    Retorna la ruta absoluta del archivo generado.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fecha = resumen["fecha"]
    filename = f"Corte_{fecha}.pdf"
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

    # ── GASTOS ──
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*MORADO_PASTEL)
    pdf.cell(0, 8, "Gastos / Salidas", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_fill_color(*AZUL_PASTEL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 8, "  Concepto", fill=True)
    pdf.cell(50, 8, "Categoría", fill=True, align="C")
    pdf.cell(50, 8, "Monto", fill=True, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(60, 60, 60)
    pdf.set_font("Helvetica", "", 10)
    fill = False
    for g in resumen.get("gastos_detalle", []):
        if fill:
            pdf.set_fill_color(*GRIS_CLARO)
        pdf.cell(90, 7, f"  {g['concepto'][:40]}", fill=fill)
        pdf.cell(50, 7, g["categoria"], fill=fill, align="C")
        pdf.cell(50, 7, f"${g['monto']:,.2f}  ", fill=fill, align="R",
                 new_x="LMARGIN", new_y="NEXT")
        fill = not fill

    if not resumen.get("gastos_detalle"):
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 7, "  Sin gastos registrados", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(220, 150, 150)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(140, 8, "  TOTAL GASTOS", fill=True)
    pdf.cell(50, 8, f"${resumen['total_gastos']:,.2f}  ", fill=True, align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

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
    return str(filepath)
