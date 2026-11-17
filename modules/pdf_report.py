"""
modules/pdf_report.py
Genera los PDF del POS con FPDF2. El corte de caja usa la identidad de Estudio Deco:
colores del logo, Fraunces para el veredicto y los totales, Figtree para las tablas.
"""

import logging
from fpdf import FPDF
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
LOGO_PATH = ROOT / "assets" / "logo.png"              # monocromático (tickets y PDF de nómina)
LOGO_SVG = ROOT / "assets" / "logo-estudio-deco.svg"  # logo a color para el corte
FONTS_DIR = ROOT / "assets" / "fonts"

# Colores pastel del branding (los usan nómina y ventas del día)
AZUL_PASTEL = (174, 198, 207)     # #AEC6CF
MORADO_PASTEL = (179, 157, 219)   # #B39DDB
GRIS_CLARO = (245, 245, 250)

# Paleta del logo de Estudio Deco para el corte
VIOLETA = (110, 95, 160)        # contorno de las letras
LAVANDA = (180, 156, 228)       # relleno de "estudio"
CIELO = (168, 204, 252)         # corazón y "deco"
CIELO_FUERTE = (61, 120, 201)
LILA = (243, 242, 252)          # fondo estrellado del logo
LINEA = (222, 217, 241)
TINTA = (43, 35, 80)
SUAVE = (112, 104, 145)
ROJO = (194, 65, 79)            # solo para "faltan"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

logging.getLogger("fpdf.svg").setLevel(logging.ERROR)  # el SVG trae <title>, que fpdf ignora


def _dinero(v) -> str:
    v = float(v or 0)
    return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"


def _fecha_larga(fecha: str) -> str:
    try:
        d = datetime.strptime(fecha[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return str(fecha)
    return f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]} de {d.year}"


def _inicio_turno(desde: str, fecha: str) -> str:
    """'desde las 09:00' o, si el turno empezó otro día, 'desde el 15 de noviembre, 18:00'."""
    try:
        d = datetime.strptime(str(desde)[:16], "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ""
    if str(desde)[:10] == str(fecha)[:10]:
        return "Turno del día completo" if d.strftime("%H:%M") == "00:00" else f"Turno desde las {d:%H:%M}"
    return f"Turno desde el {d.day} de {MESES[d.month - 1]}, {d:%H:%M}"


class CortePDF(FPDF):
    """Hoja del corte de caja. Sin las fuentes de marca cae a Helvetica y sigue funcionando."""

    def __init__(self, fecha: str = ""):
        super().__init__(format="A4")
        self.fecha_corte = fecha
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, 20)
        self.alias_nb_pages()
        self.marca = self._cargar_fuentes()

    def _cargar_fuentes(self) -> bool:
        archivos = {
            ("Figtree", ""): "Figtree-Regular.ttf",
            ("Figtree", "B"): "Figtree-Bold.ttf",
            ("FigtreeSemi", ""): "Figtree-SemiBold.ttf",
            ("FigtreeExtra", ""): "Figtree-ExtraBold.ttf",
            ("FrauncesDisplay", ""): "Fraunces-Display.ttf",
            ("FrauncesText", ""): "Fraunces-Text.ttf",
        }
        try:
            for (familia, estilo), archivo in archivos.items():
                self.add_font(familia, estilo, str(FONTS_DIR / archivo))
            return True
        except Exception as e:
            logging.error(f"Fuentes del corte no disponibles, uso Helvetica: {e}")
            return False

    def fuente(self, rol: str, tam: float):
        """rol: texto, texto_b, semi, extra, display, titulo."""
        if self.marca:
            familia, estilo = {
                "texto": ("Figtree", ""), "texto_b": ("Figtree", "B"), "semi": ("FigtreeSemi", ""),
                "extra": ("FigtreeExtra", ""), "display": ("FrauncesDisplay", ""), "titulo": ("FrauncesText", ""),
            }[rol]
        else:
            familia, estilo = "Helvetica", ("" if rol == "texto" else "B")
        self.set_font(familia, estilo, tam)

    def header(self):
        if self.page_no() == 1:
            return  # la primera página lleva el encabezado grande
        self.fuente("semi", 8.5)
        self.set_text_color(*SUAVE)
        self.cell(0, 6, f"Corte de caja del {_fecha_larga(self.fecha_corte).lower()}", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINEA)
        self.set_line_width(0.3)
        self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.fuente("texto", 8)
        self.set_text_color(*SUAVE)
        self.cell(0, 6, f"Estudio Deco, generado el {datetime.now():%d/%m/%Y a las %H:%M}", align="L")
        self.set_x(self.l_margin)
        self.cell(0, 6, f"Página {self.page_no()} de {{nb}}", align="R")

    # ── piezas ──
    def caja(self, x, y, w, h, radio):
        """Rectángulo relleno con esquinas redondeadas; fpdf2 viejo no tiene round_corners y dibuja uno recto."""
        try:
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=radio)
        except TypeError:
            self.rect(x, y, w, h, style="F")

    @property
    def ancho(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def titulo(self, texto: str, extra: str = "", necesita: float = 30):
        """necesita: alto en mm que la sección quiere mantener junto a su título."""
        if self.get_y() + 14 + necesita > self.h - self.b_margin:
            self.add_page()
        self.ln(4)
        self.fuente("titulo", 13)
        self.set_text_color(*VIOLETA)
        self.cell(self.ancho - 60, 8, texto)
        if extra:
            self.fuente("texto", 9)
            self.set_text_color(*SUAVE)
            self.cell(60, 8, extra, align="R")
        self.ln(10)

    def tabla(self, columnas, filas, total=None, tam=9.5, alto=7.2, detalle=None):
        """columnas: [(etiqueta, ancho_mm, 'L'|'C'|'R')]; detalle(i) devuelve una línea gris bajo la fila."""
        def encabezado():
            self.fuente("semi", tam - 1.5)
            self.set_text_color(*SUAVE)
            for etiqueta, w, al in columnas:
                self.cell(w, 6, etiqueta, align=al)
            self.ln(6)
            self.set_draw_color(*VIOLETA)
            self.set_line_width(0.4)
            self.line(self.l_margin, self.get_y(), self.l_margin + sum(c[1] for c in columnas), self.get_y())
            self.ln(1)
        encabezado()
        for i, fila in enumerate(filas):
            if self.get_y() > self.h - 28:
                self.add_page()
                encabezado()
            self.fuente("texto", tam)
            self.set_text_color(*TINTA)
            for (etiqueta, w, al), valor in zip(columnas, fila):
                self.cell(w, alto, str(valor), align=al)
            self.ln(alto)
            if detalle:
                linea = detalle(i)
                if linea:
                    self.fuente("texto", tam - 2)
                    self.set_text_color(*SUAVE)
                    self.cell(self.ancho, 4.5, linea, new_x="LMARGIN", new_y="NEXT")
                    self.ln(0.8)
            self.set_draw_color(*LINEA)
            self.set_line_width(0.2)
            self.line(self.l_margin, self.get_y(), self.l_margin + sum(c[1] for c in columnas), self.get_y())
        if total:
            self.set_draw_color(*TINTA)
            self.set_line_width(0.5)
            self.line(self.l_margin, self.get_y(), self.l_margin + sum(c[1] for c in columnas), self.get_y())
            self.fuente("texto_b", tam)
            self.set_text_color(*TINTA)
            for (etiqueta, w, al), valor in zip(columnas, total):
                self.cell(w, alto + 1, str(valor), align=al)
            self.ln(alto + 1)

    def barras(self, items, total):
        """Una fila por concepto: nombre y monto, y debajo una barra fina proporcional al total."""
        total = total or 1
        for nombre, monto, color in items:
            self.fuente("texto", 10)
            self.set_text_color(*TINTA)
            self.cell(self.ancho - 50, 6, nombre)
            self.fuente("texto_b", 10)
            self.cell(50, 6, _dinero(monto), align="R")
            self.ln(6.5)
            y = self.get_y()
            self.set_fill_color(*LILA)
            self.caja(self.l_margin, y, self.ancho, 2.2, 1.1)
            w = max(1.6, self.ancho * max(0, monto) / total) if monto else 0
            if w:
                self.set_fill_color(*color)
                self.caja(self.l_margin, y, w, 2.2, 1.1)
            self.ln(5.5)


def generar_corte_pdf(resumen: dict, cajero: str, ventas_turno: list = None) -> str:
    """
    Genera el PDF del corte de caja que se envía por correo.
    ventas_turno: lista de dicts de ventas individuales del turno (opcional).
    Retorna la ruta absoluta del archivo generado.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fecha = resumen["fecha"]
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filepath = REPORTS_DIR / f"Corte_{timestamp}.pdf"

    pdf = CortePDF(fecha)
    pdf.add_page()
    x0 = pdf.l_margin

    # ── Encabezado: logo, título y datos del turno ──
    try:
        pdf.image(str(LOGO_SVG), x=x0, y=14, w=26)
    except Exception:
        if LOGO_PATH.exists():
            pdf.image(str(LOGO_PATH), x=x0, y=14, w=24)
    pdf.set_xy(x0 + 32, 15)
    pdf.fuente("display", 24)
    pdf.set_text_color(*VIOLETA)
    pdf.cell(0, 11, "Corte de caja", new_x="LEFT", new_y="NEXT")
    pdf.fuente("texto_b", 10.5)
    pdf.set_text_color(*TINTA)
    pdf.cell(0, 6, _fecha_larga(fecha), new_x="LEFT", new_y="NEXT")
    pdf.fuente("texto", 9.5)
    pdf.set_text_color(*SUAVE)
    turno = _inicio_turno(resumen.get("desde", ""), fecha)
    pdf.cell(0, 5.2, f"Cajero: {cajero}", new_x="LEFT", new_y="NEXT")
    if turno:
        pdf.cell(0, 5.2, turno, new_x="LEFT", new_y="NEXT")
    pdf.set_y(max(pdf.get_y(), 14 + 26 * 311 / 323) + 7)

    # ── Veredicto: lo primero que se necesita saber es si la caja cuadró ──
    dif = float(resumen.get("diferencia", 0) or 0)
    esperado = float(resumen.get("efectivo_esperado", 0) or 0)
    real = float(resumen.get("efectivo_real", 0) or 0)
    if abs(dif) < 0.005:
        veredicto, color_v = "La caja cuadró", VIOLETA
    elif dif > 0:
        veredicto, color_v = f"Sobran {_dinero(dif)}", CIELO_FUERTE
    else:
        veredicto, color_v = f"Faltan {_dinero(abs(dif))}", ROJO

    y = pdf.get_y()
    alto_panel = 46
    pdf.set_fill_color(*LILA)
    pdf.caja(x0, y, pdf.ancho, alto_panel, 4)
    pdf.set_fill_color(*color_v)
    pdf.caja(x0, y, 2.4, alto_panel, 1.2)
    pdf.set_xy(x0 + 10, y + 7)
    pdf.fuente("display", 30)
    pdf.set_text_color(*color_v)
    pdf.cell(pdf.ancho - 20, 14, veredicto)
    col = (pdf.ancho - 20) / 3
    for i, (etiqueta, valor) in enumerate([("Efectivo esperado", esperado), ("Efectivo contado", real),
                                           ("Diferencia", dif)]):
        cx = x0 + 10 + i * col
        pdf.set_xy(cx, y + 26)
        pdf.fuente("texto", 9)
        pdf.set_text_color(*SUAVE)
        pdf.cell(col, 5, etiqueta)
        pdf.set_xy(cx, y + 31.5)
        pdf.fuente("titulo", 15)
        pdf.set_text_color(*(color_v if etiqueta == "Diferencia" else TINTA))
        pdf.cell(col, 8, ("+" if dif > 0.005 and etiqueta == "Diferencia" else "") + _dinero(valor))
    pdf.set_y(y + alto_panel + 4)
    pdf.fuente("texto", 8.5)
    pdf.set_text_color(*SUAVE)
    fondo = float(resumen.get("fondo_caja", 0) or 0)
    pdf.multi_cell(pdf.ancho, 4.4, f"El efectivo contado no incluye el fondo de caja inicial ({_dinero(fondo)}). "
                                   f"Esperado = ventas en efectivo + ingresos en efectivo - gastos pagados de caja.")

    # ── Ventas del turno por método de pago ──
    total_ventas = float(resumen.get("total_ventas", 0) or 0)
    num = resumen.get("num_ventas", 0)
    canceladas = resumen.get("num_canceladas", 0)
    extra = f"{num} ticket{'s' if num != 1 else ''}" + (f", {canceladas} cancelado{'s' if canceladas != 1 else ''}" if canceladas else "")
    pdf.titulo("Ventas del turno", extra)
    pdf.fuente("display", 22)
    pdf.set_text_color(*TINTA)
    pdf.cell(0, 11, _dinero(total_ventas), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    colores = {"Efectivo": LAVANDA, "Tarjeta": CIELO, "Transferencia": VIOLETA}
    metodos = [(m["metodo_pago"], float(m["monto"] or 0), colores.get(m["metodo_pago"], LAVANDA))
               for m in resumen.get("metodos_pago", [])]
    if metodos:
        pdf.barras(metodos, max(total_ventas, sum(m[1] for m in metodos)))

    # ── Ventas por tienda ──
    vpt = resumen.get("ventas_por_tienda", [])
    if vpt:
        pdf.titulo("Ventas por tienda")
        w = pdf.ancho
        pdf.tabla(
            [("Tienda", w * 0.46, "L"), ("Vendido", w * 0.18, "R"), ("Comisión tarjeta", w * 0.18, "R"), ("Neto", w * 0.18, "R")],
            [(t["tienda"], _dinero(t["total"]), _dinero(t.get("comision", 0)), _dinero(t.get("neto", t["total"]))) for t in vpt],
            total=("Total", _dinero(total_ventas), _dinero(sum(t.get("comision", 0) for t in vpt)),
                   _dinero(sum(t.get("neto", t["total"]) for t in vpt))),
        )

    # ── Ingresos y gastos ──
    ingresos = resumen.get("ingresos_detalle", [])
    if ingresos:
        pdf.titulo("Ingresos", _dinero(resumen.get("total_ingresos", 0)))
        w = pdf.ancho
        pdf.tabla([("Concepto", w * 0.6, "L"), ("Método", w * 0.2, "L"), ("Monto", w * 0.2, "R")],
                  [(i["concepto"], i.get("metodo_pago", "Efectivo"), _dinero(i["monto"])) for i in ingresos])

    gastos = resumen.get("gastos_detalle", [])
    pdf.titulo("Gastos", _dinero(resumen.get("total_gastos", 0)))
    if gastos:
        w = pdf.ancho
        pdf.tabla([("Concepto", w * 0.42, "L"), ("Tienda", w * 0.22, "L"), ("Sale de", w * 0.16, "L"), ("Monto", w * 0.2, "R")],
                  [(g["concepto"], g.get("tienda", "General"), g.get("origen", "Caja"), _dinero(g["monto"])) for g in gastos])
    else:
        pdf.fuente("texto", 10)
        pdf.set_text_color(*SUAVE)
        pdf.cell(0, 7, "No hubo gastos en este turno.", new_x="LMARGIN", new_y="NEXT")

    # ── Desglose del efectivo contado ──
    desglose = resumen.get("desglose_billetes", {}) or {}
    if desglose or fondo > 0:
        renglones = sum(1 for k, c in desglose.items() if c)
        pdf.titulo("Efectivo contado", necesita=(renglones + 2) * 7.4 + 20)
        nombres = {f"B{d}": f"Billete de ${d:,}" for d in [1000, 500, 200, 100, 50, 20]}
        nombres.update({f"M{d}": f"Moneda de ${d}" for d in [10, 5, 2, 1]})
        nombres["M0.5"] = "Moneda de $0.50"
        filas, total_contado = [], 0.0
        for clave, cant in desglose.items():
            try:
                denom = float(clave[1:])
            except ValueError:
                continue
            if not cant:
                continue
            total_contado += denom * cant
            filas.append((nombres.get(clave, clave), cant, _dinero(denom * cant)))
        w = pdf.ancho
        if not filas:
            total_contado = real + fondo
        else:
            pdf.tabla([("Denominación", w * 0.5, "L"), ("Cantidad", w * 0.2, "R"), ("Subtotal", w * 0.3, "R")],
                      filas, total=("Total en caja", "", _dinero(total_contado)))
        pdf.ln(2)
        for etiqueta, valor, fuerte in [("Menos fondo de caja inicial", -fondo, False),
                                        ("Efectivo de ventas del turno", real, True)]:
            pdf.fuente("texto_b" if fuerte else "texto", 10)
            pdf.set_text_color(*TINTA if fuerte else SUAVE)
            pdf.cell(w * 0.7, 6.5, etiqueta)
            pdf.cell(w * 0.3, 6.5, _dinero(valor), align="R", new_x="LMARGIN", new_y="NEXT")

    # ── Detalle de tickets ──
    if ventas_turno:
        pdf.titulo("Tickets del turno", f"{len(ventas_turno)} en total")
        cols = [("Folio", 20, "L"), ("Hora", 12, "L"), ("Cuenta", 26, "L"), ("IRC desc.", 15, "R"), ("Prop.", 13, "R"),
                ("Importe", 18, "R"), ("Efectivo", 18, "R"), ("Tarjeta", 18, "R"), ("CxC", 16, "R"), ("Neto", 18, "R")]
        filas, detalles = [], []
        s_imp = s_ef = s_tar = s_cxc = s_neto = 0.0
        for v in ventas_turno:
            folio = v.get("folio", "")
            folio = folio[-8:] if len(folio) > 12 else folio
            creado = v.get("created_at", "") or ""
            hora = creado[11:16] if len(creado) >= 16 else ""
            cuenta = f"Mesa {v['mesa_numero']}" if v.get("mesa_numero") else "Venta directa"
            metodo = v.get("metodo_pago", "Efectivo")
            total_v = float(v.get("total", 0) or 0)
            m_tar = float(v.get("monto_tarjeta", 0) or 0)
            m_ef = float(v.get("monto_efectivo", 0) or 0)
            ef = m_ef if metodo in ("Efectivo", "Mixto") else 0.0
            tar = m_tar if metodo in ("Tarjeta", "Mixto") else 0.0
            cxc = total_v if metodo in ("Transferencia", "Transfer") else 0.0
            if metodo == "Tarjeta":
                comision = round(total_v * 0.04, 2)
            elif metodo == "Mixto" and total_v > 0:
                comision = round(m_tar * 0.04, 2)
            else:
                comision = 0.0
            neto = total_v - comision
            s_imp += total_v; s_ef += ef; s_tar += tar; s_cxc += cxc; s_neto += neto
            filas.append((folio, hora, cuenta[:15], _dinero(0), _dinero(0), _dinero(total_v), _dinero(ef),
                          _dinero(tar), _dinero(cxc), _dinero(neto)))
            items = v.get("items", []) or []
            desc = ", ".join(f"{i.get('nombre_producto', i.get('nombre', '?'))} x{i.get('cantidad', 1)}" for i in items[:5])
            if len(items) > 5:
                desc += f" y {len(items) - 5} más"
            detalles.append(desc)
        pdf.tabla(cols, filas, tam=8.5, alto=6.2, detalle=lambda i: detalles[i],
                  total=("Totales", "", "", _dinero(0), _dinero(0), _dinero(s_imp), _dinero(s_ef),
                         _dinero(s_tar), _dinero(s_cxc), _dinero(s_neto)))

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
