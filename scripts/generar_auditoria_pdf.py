"""
Generador del Reporte de Auditoria Integral -- EstudioDeco POS v2
Ejecutar: python generar_auditoria_pdf.py
Produce:  assets/auditoria_EstudioDeco_POS.pdf
"""

from fpdf import FPDF, XPos, YPos
from pathlib import Path
from datetime import date

LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"
OUTPUT    = Path(__file__).parent / "assets" / "auditoria_EstudioDeco_POS.pdf"

# Paleta de colores
C_DARK      = (15,  23,  42)
C_ACCENT    = (37,  99, 235)
C_CRITICO   = (185, 28,  28)
C_ALTO      = (194, 65,   0)
C_MEDIO     = (161, 98,   7)
C_BLOQUE    = (30,  64, 175)
C_LIGHT_BG  = (241, 245, 249)
C_CODE_BG   = (30,  41,  59)
C_WHITE     = (255, 255, 255)
C_GRAY      = (100, 116, 139)
C_BORDER    = (203, 213, 225)

SEVERITY_COLOR = {
    "CRITICO": C_CRITICO,
    "ALTO":    C_ALTO,
    "MEDIO":   C_MEDIO,
}


def _lm():
    return {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

def _rt():
    return {"new_x": XPos.RIGHT, "new_y": YPos.TOP}


class AuditPDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=22)
        self.set_margins(18, 18, 18)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.4)
        self.line(18, 10, 192, 10)
        self.set_font("Helvetica", "B", 7.5)
        self.set_text_color(*C_GRAY)
        self.set_xy(18, 12)
        self.cell(0, 4, "Reporte de Auditoria Integral -- EstudioDeco POS v2",
                  **_rt())
        self.set_xy(18, 12)
        self.cell(0, 4, f"Pag. {self.page_no()}", **_lm())
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(18, self.get_y(), 192, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_GRAY)
        self.cell(0, 6,
                  f"Confidencial - Generado el {date.today().strftime('%d/%m/%Y')} - Solo para uso interno",
                  align="C")

    # ---- Cover ---------------------------------------------------------------

    def cover(self):
        self.add_page()

        # Banda superior oscura
        self.set_fill_color(*C_DARK)
        self.rect(0, 0, 210, 58, "F")

        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=79, y=8, w=52)

        self.set_xy(18, 60)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*C_DARK)
        self.cell(0, 10, "Reporte de Auditoria Integral", align="C", **_lm())

        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*C_ACCENT)
        self.cell(0, 8, "EstudioDeco POS v2", align="C", **_lm())

        self.ln(4)
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.8)
        self.line(50, self.get_y(), 160, self.get_y())
        self.ln(6)

        # Caja de metadata
        self.set_fill_color(*C_LIGHT_BG)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        box_x, box_y, box_w, box_h = 36, self.get_y(), 138, 38
        self.rect(box_x, box_y, box_w, box_h, "FD")

        self.set_xy(box_x + 6, box_y + 6)
        rows = [
            ("Fecha de emision",    date.today().strftime("%d/%m/%Y")),
            ("Clasificacion",       "CONFIDENCIAL -- Solo uso interno"),
            ("Stack auditado",      "FastAPI - SQLite - Python 3.x"),
            ("Modulos revisados",   "server.py - modules/database.py - sync_sheets.py"),
        ]
        self.set_font("Helvetica", "", 9)
        for label, val in rows:
            self.set_text_color(*C_GRAY)
            self.set_x(box_x + 6)
            self.cell(44, 6, label + ":", **_rt())
            self.set_text_color(*C_DARK)
            self.cell(0, 6, val, **_lm())
        self.ln(6)

        # Badges de resumen
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_DARK)
        self.cell(0, 6, "Resumen ejecutivo de hallazgos", align="C", **_lm())
        self.ln(2)

        badges = [
            ("3",  "CRITICOS",       C_CRITICO),
            ("5",  "ALTOS",          C_ALTO),
            ("4",  "MEDIOS",         C_MEDIO),
            ("4",  "BUGS DIA/SEM.",  C_ACCENT),
        ]
        bw = 40
        bx = (210 - len(badges) * bw - (len(badges) - 1) * 3) / 2
        by = self.get_y()
        for num, label, color in badges:
            self.set_fill_color(*color)
            self.set_draw_color(*color)
            self.rect(bx, by, bw, 16, "F")
            self.set_xy(bx, by + 1)
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(*C_WHITE)
            self.cell(bw, 7, num, align="C", **_rt())
            self.set_xy(bx, by + 9)
            self.set_font("Helvetica", "B", 5.5)
            self.cell(bw, 5, label, align="C", **_rt())
            bx += bw + 3

        self.ln(24)

        # Advertencia
        self.set_fill_color(254, 242, 242)
        self.set_draw_color(*C_CRITICO)
        self.set_line_width(0.5)
        aw = 158
        ax = (210 - aw) / 2
        ay = self.get_y()
        self.rect(ax, ay, aw, 14, "FD")
        self.set_xy(ax + 4, ay + 3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*C_CRITICO)
        self.cell(aw - 8, 5,
                  "ADVERTENCIA: Se identificaron vulnerabilidades CRITICAS de seguridad.",
                  align="C", **_lm())
        self.set_x(ax + 4)
        self.set_font("Helvetica", "", 8)
        self.cell(aw - 8, 4,
                  "No desplegar en produccion sin aplicar el Plan de Remediacion -- Bloque A.",
                  align="C", **_lm())
        self.ln(10)

        # Indice
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C_DARK)
        self.cell(0, 7, "Contenido", **_lm())
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(2)

        toc = [
            ("1.", "Fase 1 -- Hallazgos Financieros",               "F-1 a F-7"),
            ("2.", "Fase 2 -- Vulnerabilidades Administrativas",     "S-1 a S-10"),
            ("3.", "Plan de Remediacion Arquitectonica",             "Bloques A-D"),
            ("4.", "Analisis de Discrepancias Diario vs. Semanal",   "Bug #1 a #4"),
            ("5.", "Tabla resumen de causas raiz",                   ""),
        ]
        self.set_font("Helvetica", "", 9.5)
        for num, title, ref in toc:
            self.set_text_color(*C_ACCENT)
            self.cell(8, 6, num, **_rt())
            self.set_text_color(*C_DARK)
            self.cell(130, 6, title, **_rt())
            self.set_text_color(*C_GRAY)
            self.cell(0, 6, ref, align="R", **_lm())

    # ---- Section title -------------------------------------------------------

    def section_title(self, title, subtitle=""):
        self.add_page()
        self.set_fill_color(*C_DARK)
        self.rect(0, 0, 210, 28, "F")
        self.set_xy(18, 8)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*C_WHITE)
        self.cell(0, 8, title, **_lm())
        if subtitle:
            self.set_x(18)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(148, 163, 184)
            self.cell(0, 6, subtitle, **_lm())
        self.set_y(36)

    # ---- Hallazgo card -------------------------------------------------------

    def hallazgo(self, code, severity, title, file_ref, paragraphs,
                 code_snippet=None):
        color = SEVERITY_COLOR.get(severity, C_MEDIO)
        bx = 18
        by = self.get_y()

        est_h = 30 + len(paragraphs) * 14 + (12 if code_snippet else 0)
        if by + est_h > 270:
            self.add_page()
            by = self.get_y()

        # Encabezado
        self.set_fill_color(*C_LIGHT_BG)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.rect(bx, by, 174, 10, "FD")

        badge_w = 22
        self.set_fill_color(*color)
        self.rect(bx, by, badge_w, 10, "F")
        self.set_xy(bx, by + 1)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_WHITE)
        self.cell(badge_w, 8, severity, align="C", **_rt())

        self.set_xy(bx + badge_w + 3, by + 1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_DARK)
        self.cell(0, 4, f"{code} -- {title}", **_lm())

        self.set_x(bx + badge_w + 3)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*C_GRAY)
        self.cell(0, 4, f"Archivo: {file_ref}", **_lm())

        self.ln(2)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*C_DARK)
        for para in paragraphs:
            if para.startswith("  "):
                self.set_x(bx + 10)
                self.multi_cell(161, 4.5, para.strip())
            else:
                self.set_x(bx + 3)
                self.multi_cell(168, 4.5, para)
            self.ln(1)

        if code_snippet:
            self.ln(1)
            lines = code_snippet.strip().split("\n")
            ch = len(lines) * 4.5 + 6
            cx = bx + 3
            cy = self.get_y()
            if cy + ch > 270:
                self.add_page()
                cy = self.get_y()
            self.set_fill_color(*C_CODE_BG)
            self.rect(cx, cy, 168, ch, "F")
            self.set_xy(cx + 3, cy + 2.5)
            self.set_font("Courier", "", 7.5)
            self.set_text_color(186, 230, 253)
            for line in lines:
                self.set_x(cx + 3)
                self.cell(0, 4.5, line, **_lm())
            self.ln(2)

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(bx, self.get_y() + 1, bx + 174, self.get_y() + 1)
        self.ln(4)

    # ---- Bloque remediacion --------------------------------------------------

    def bloque_remediacion(self, letra, titulo, items):
        if self.get_y() > 240:
            self.add_page()

        self.set_fill_color(*C_BLOQUE)
        self.rect(18, self.get_y(), 174, 9, "F")
        self.set_xy(21, self.get_y() + 1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_WHITE)
        self.cell(0, 7, f"Bloque {letra} -- {titulo}", **_lm())
        self.ln(2)

        for num, item in items:
            if self.get_y() > 265:
                self.add_page()
            self.set_fill_color(*C_ACCENT)
            self.rect(18, self.get_y(), 7, 6, "F")
            self.set_xy(18, self.get_y())
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*C_WHITE)
            self.cell(7, 6, str(num), align="C", **_rt())

            self.set_x(27)
            parts = item.split(":", 1)
            if len(parts) == 2:
                self.set_font("Helvetica", "B", 8.5)
                self.set_text_color(*C_DARK)
                self.cell(0, 3, parts[0] + ":", **_lm())
                self.set_x(27)
                self.set_font("Helvetica", "", 8.5)
                self.multi_cell(163, 4, parts[1].strip())
            else:
                self.set_font("Helvetica", "", 8.5)
                self.set_text_color(*C_DARK)
                self.multi_cell(163, 4, item)
            self.ln(2)

        self.ln(3)

    # ---- Bug discrepancia ----------------------------------------------------

    def bug_discrepancia(self, num, severity, title, file_ref, paragraphs,
                         code_left=None, code_right=None,
                         label_left="", label_right=""):
        color = SEVERITY_COLOR.get(severity, C_MEDIO)
        bx = 18
        by = self.get_y()

        est_h = 30 + len(paragraphs) * 14 + (32 if code_left else 0)
        if by + est_h > 268:
            self.add_page()
            by = self.get_y()

        # Encabezado
        self.set_fill_color(*C_LIGHT_BG)
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.rect(bx, by, 174, 10, "FD")

        badge_w = 22
        self.set_fill_color(*color)
        self.rect(bx, by, badge_w, 10, "F")
        self.set_xy(bx, by + 1)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_WHITE)
        self.cell(badge_w, 8, severity, align="C", **_rt())

        self.set_xy(bx + badge_w + 3, by + 1)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_DARK)
        self.cell(0, 4, f"Bug #{num} -- {title}", **_lm())

        self.set_x(bx + badge_w + 3)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*C_GRAY)
        self.cell(0, 4, f"Referencia: {file_ref}", **_lm())

        self.ln(2)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*C_DARK)
        for para in paragraphs:
            self.set_x(bx + 3)
            self.multi_cell(168, 4.5, para)
            self.ln(1)

        if code_left and code_right:
            by2 = self.get_y()
            if by2 + 32 > 270:
                self.add_page()
                by2 = self.get_y()

            half_w = 82
            gap = 8

            for side, code_text, label in [
                (0, code_left,  label_left),
                (1, code_right, label_right)
            ]:
                cx = bx + 3 + side * (half_w + gap)
                lines = code_text.strip().split("\n")
                ch = len(lines) * 4.5 + 7
                bg = C_CODE_BG if side == 0 else (20, 51, 30)
                self.set_fill_color(*bg)
                self.rect(cx, by2, half_w, ch, "F")
                self.set_xy(cx + 2, by2 + 1)
                self.set_font("Helvetica", "B", 6.5)
                lc = (239, 68, 68) if side == 0 else (134, 239, 172)
                self.set_text_color(*lc)
                self.cell(half_w - 4, 4, label, **_lm())
                self.set_font("Courier", "", 7)
                self.set_text_color(186, 230, 253)
                for line in lines:
                    self.set_x(cx + 2)
                    self.cell(half_w - 4, 4.5, line, **_lm())

            max_lines = max(len(code_left.split("\n")), len(code_right.split("\n")))
            self.set_y(by2 + max_lines * 4.5 + 8)
            self.ln(2)

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.2)
        self.line(bx, self.get_y() + 1, bx + 174, self.get_y() + 1)
        self.ln(4)

    # ---- Tabla resumen -------------------------------------------------------

    def tabla_resumen(self, headers, rows, col_widths):
        bx = 18
        self.set_fill_color(*C_DARK)
        self.set_text_color(*C_WHITE)
        self.set_font("Helvetica", "B", 8)
        self.set_x(bx)
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, h, border=0, fill=True, align="C", **_rt())
        self.ln()

        alt = False
        for row in rows:
            if self.get_y() > 265:
                self.add_page()
            self.set_x(bx)
            bg = (241, 245, 249) if alt else C_WHITE
            self.set_fill_color(*bg)
            self.set_font("Helvetica", "", 8)
            for i, (cell_text, w) in enumerate(zip(row, col_widths)):
                if cell_text in SEVERITY_COLOR:
                    c = SEVERITY_COLOR[cell_text]
                    self.set_fill_color(*c)
                    self.set_text_color(*C_WHITE)
                    self.set_font("Helvetica", "B", 7.5)
                    self.cell(w, 6, cell_text, border=0, fill=True, align="C", **_rt())
                    self.set_fill_color(*bg)
                    self.set_text_color(*C_DARK)
                    self.set_font("Helvetica", "", 8)
                else:
                    self.set_text_color(*C_DARK)
                    self.cell(w, 6, cell_text, border=0, fill=True, **_rt())
            self.ln()
            alt = not alt

        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.3)
        self.line(bx, self.get_y(), bx + sum(col_widths), self.get_y())
        self.ln(4)


# =============================================================================
# BUILD
# =============================================================================

def build():
    pdf = AuditPDF()

    # =========================================================================
    # PORTADA
    # =========================================================================
    pdf.cover()

    # =========================================================================
    # FASE 1 -- HALLAZGOS FINANCIEROS
    # =========================================================================
    pdf.section_title(
        "Fase 1 -- Hallazgos Financieros",
        "Integridad transaccional - Concurrencia - Reportes - Rendimiento"
    )

    pdf.hallazgo(
        "F-1", "CRITICO",
        "Sin proteccion transaccional atomica en cerrar_mesa",
        "modules/database.py:363-475",
        [
            "La funcion cerrar_mesa ejecuta entre 5 y 15+ sentencias SQL secuenciales "
            "(INSERT ventas -> INSERT venta_detalle x N -> UPDATE stock x N -> UPDATE ordenes "
            "-> INSERT gastos [comision]) sin ningun bloque try/except/rollback.",

            "Causa raiz: Si la operacion falla a mitad del camino (ej. error al descontar "
            "stock del item N), el registro en ventas ya existe pero faltan filas en "
            "venta_detalle. El conn.commit() de la linea 454 solo se ejecuta si no hay "
            "excepcion; SQLite en modo autocommit implicito puede crear estados parciales "
            "que quedan 'huerfanos'. El resumen del dia sumara una venta sin detalle.",

            "Patron faltante:",
        ],
        code_snippet=(
            "try:\n"
            "    # todas las operaciones\n"
            "    conn.commit()\n"
            "except Exception:\n"
            "    conn.rollback()\n"
            "    raise"
        )
    )

    pdf.hallazgo(
        "F-2", "CRITICO",
        "corregir_venta no reversa ni recalcula la comision de tarjeta",
        "modules/database.py:1283-1289",
        [
            "Cuando se corrige el metodo de pago de una venta (ej. de Efectivo a Tarjeta), "
            "la funcion solo actualiza metodo_pago, monto_efectivo y monto_tarjeta en la tabla "
            "ventas. No crea, elimina, ni ajusta el gasto de 'Comision Tarjeta 4%'.",

            "Impacto en cuadre: Si una venta de $1,000 Efectivo se corrige a Tarjeta, el "
            "balance registrara $1,000 en tarjeta pero no habra gasto de comision ($40). "
            "Al reves: una venta movida de Tarjeta a Efectivo mantendra un gasto fantasma "
            "de $40 que nunca corresponde a un cobro real.",
        ]
    )

    pdf.hallazgo(
        "F-3", "ALTO",
        "Condicion de carrera en descuento de stock",
        "modules/database.py:428-429 y 1184-1185",
        [
            "Ambas rutas (mesa y venta directa) usan la misma sentencia sin verificacion "
            "previa ni bloqueo. Si dos cajas procesan simultaneamente el ultimo item del stock, "
            "ambas UPDATE pasan y el stock queda en negativo. El reporte de inventario queda "
            "inconsistente con la realidad fisica.",
        ],
        code_snippet="UPDATE productos SET stock_local = stock_local - ? WHERE id=?"
    )

    pdf.hallazgo(
        "F-4", "ALTO",
        "Comision de tarjeta calculada dos veces para pagos mixtos",
        "modules/database.py:1187-1195 vs 440-451",
        [
            "En registrar_venta (ventas directas) la comision se aplica si "
            "metodo_pago in ('Tarjeta', 'Mixto'). En cerrar_mesa (ventas por mesa) la misma "
            "comision se calcula y registra de forma independiente. Cada ruta produce su "
            "propio INSERT en gastos, duplicando el cargo si ambas se invocan para la misma "
            "operacion.",
        ]
    )

    pdf.hallazgo(
        "F-5", "ALTO",
        "Folio no atomico: condicion de carrera en numeracion",
        "modules/database.py:496-500",
        [
            "El folio se genera con un COUNT(*) seguido de un INSERT independiente. Con dos "
            "requests concurrentes al mismo milisegundo, ambos obtienen COUNT=5, ambos generan "
            "VTA-20260413-0006. El segundo INSERT falla con violacion de unicidad (si existe "
            "UNIQUE) o genera folios duplicados silenciosamente (si no existe). Esto causa que "
            "los reportes cuenten ventas duplicadas o pierdan registros.",
        ],
        code_snippet=(
            "def _generar_folio(conn):\n"
            "    row = conn.execute(\n"
            "        'SELECT COUNT(*) as c FROM ventas'\n"
            "        ' WHERE folio LIKE ?', (f'VTA-{hoy}-%',)).fetchone()\n"
            "    num = (row['c'] if row else 0) + 1\n"
            "    return f'VTA-{hoy}-{num:04d}'"
        )
    )

    pdf.hallazgo(
        "F-6", "ALTO",
        "Fuga de tiempo: datetime mezcla localtime con comparaciones de fecha Python",
        "modules/database.py:755-891",
        [
            "Las ventas se guardan con created_at DEFAULT (datetime('now','localtime')) a "
            "nivel de SQLite, pero la comparacion en resumen usa DATE(v.created_at) = ? donde "
            "la fecha viene de Python (date.today()). Si el servidor corre en un timezone "
            "diferente al de SQLite o hay un cambio de horario de verano, ventas de las "
            "ultimas horas del dia pueden caer en la fecha 'equivocada' del resumen.",

            "Adicionalmente, obtener_resumen_semana en la linea 897 calcula la semana usando "
            "hoy.weekday() que asume lunes como dia 0. Las ventas del domingo podrian quedar "
            "excluidas hasta el cierre de semana dependiendo de la configuracion del negocio.",
        ]
    )

    pdf.hallazgo(
        "F-7", "MEDIO",
        "N+1 queries en obtener_ventas_dia y obtener_ventas_turno",
        "modules/database.py:1214-1224 y 1250-1258",
        [
            "Por cada venta del dia se ejecuta una query adicional para obtener sus items. "
            "Con 100 ventas en el dia = 101 queries. Esto ralentiza el reporte en horas pico "
            "y puede causar timeouts que el usuario interpreta como 'el reporte no cargo', "
            "llevando a recargas y potencialmente a estados inconsistentes.",
        ]
    )

    # =========================================================================
    # FASE 2 -- VULNERABILIDADES ADMINISTRATIVAS
    # =========================================================================
    pdf.section_title(
        "Fase 2 -- Vulnerabilidades Administrativas y de Seguridad",
        "Autenticacion - Autorizacion - Multitenancy - Audit Trail - Rendimiento"
    )

    pdf.hallazgo(
        "S-1", "CRITICO",
        "Credenciales en texto plano en el codigo fuente",
        "server.py:43-46",
        [
            "Las contrasenas estan en texto plano dentro del codigo versionado en git. "
            "Cualquier persona con acceso al repositorio (actual o historico) tiene las "
            "credenciales del sistema. No hay hashing, no hay rotacion, no hay revocacion "
            "posible sin redeploy.",
        ],
        code_snippet=(
            'SYSTEM_USERS = {\n'
            '    "estudiodeco": {"password": "19jul",    "role": "deco"},\n'
            '    "estacion304": {"password": "telefono", "role": "estacion"},\n'
            '}'
        )
    )

    pdf.hallazgo(
        "S-2", "CRITICO",
        "Sin autenticacion en la mayoria de los endpoints",
        "server.py:200-560",
        [
            "El endpoint /api/login existe (linea 193-198) pero su token/sesion nunca se "
            "valida en ningun otro endpoint. No existe Depends(get_current_user), middleware "
            "de sesion, ni header de autorizacion verificado en ningun endpoint.",

            "  - POST /api/estacion/gasto: cualquiera puede registrar un gasto sin autenticarse",
            "  - DELETE /api/ordenes/{oid}: cualquiera puede cancelar cualquier orden",
            "  - DELETE /api/catalog/{pid}: cualquiera puede eliminar productos del catalogo",
            "  - PUT /api/catalog/{pid}: cualquiera puede modificar precios",
        ]
    )

    pdf.hallazgo(
        "S-3", "CRITICO",
        "Escalada de privilegios por usuario_id controlado por el cliente",
        "server.py:67-69, 77-78, 80-86",
        [
            "Los modelos CerrarMesaReq, AbrirMesaReq, GastoReq y CorteReq aceptan usuario_id "
            "directamente del body del request. Un usuario puede enviar el usuario_id de un "
            "administrador para registrar transacciones bajo su nombre, manipular el historial, "
            "o atribuirse permisos de otro rol. El usuario autenticado debe derivarse del "
            "token, no del body.",
        ]
    )

    pdf.hallazgo(
        "S-4", "ALTO",
        "Sin aislamiento de datos entre tiendas (Multitenancy)",
        "modules/database.py:522-533 y 541-551",
        [
            "No hay filtrado por tienda_id ni por el usuario autenticado. El operador de "
            "Estacion 304 puede ver los gastos de Estudio Deco y viceversa. Aplica tambien "
            "a listar_nominas.",
        ],
        code_snippet=(
            "def listar_gastos(limit=200):\n"
            "    # Devuelve TODOS los gastos de TODAS las tiendas\n\n"
            "def listar_ingresos(limit=200):\n"
            "    # Devuelve TODOS los ingresos de TODOS los usuarios"
        )
    )

    pdf.hallazgo(
        "S-5", "ALTO",
        "Manipulacion de precios desde el cliente",
        "server.py:56-62",
        [
            "AddItemReq acepta precio_unitario: float sin validacion contra el catalogo. "
            "Cualquier cajero puede agregar un item de $1,000 a precio $0, o aplicar descuentos "
            "arbitrarios sin que el sistema lo rechace o registre como excepcion.",
        ]
    )

    pdf.hallazgo(
        "S-6", "ALTO",
        "Hard-delete en gastos e ingresos: sin audit trail",
        "modules/database.py:535-538 y 553-556",
        [
            "Las anulaciones eliminan fisicamente los registros. No hay campo anulado, no hay "
            "timestamp de quien anulo ni cuando. Esto rompe la trazabilidad contable: si un "
            "empleado registra un ingreso de $5,000, lo 'anula', y registra otro por $3,000, "
            "no hay evidencia de la discrepancia en la base de datos.",
        ],
        code_snippet=(
            "def anular_gasto(gasto_id):\n"
            "    conn.execute('DELETE FROM gastos WHERE id=?', (gasto_id,))\n\n"
            "def anular_ingreso(ingreso_id):\n"
            "    conn.execute('DELETE FROM ingresos WHERE id=?', (ingreso_id,))"
        )
    )

    pdf.hallazgo(
        "S-7", "ALTO",
        "anular_venta no reversa comision cuando el gasto ya fue sincronizado",
        "modules/database.py:1301",
        [
            "Si el sync worker de Google Sheets ya proceso y marco el gasto de comision como "
            "sincronizado=1, la query de anulacion lo borrara de SQLite pero el registro ya "
            "existe en Google Sheets. Los reportes de Google Sheets mostraran comisiones "
            "que no existen en la base local.",
        ],
        code_snippet=(
            "conn.execute(\n"
            "    'DELETE FROM gastos WHERE concepto LIKE ?',\n"
            "    (f'Comision Tarjeta 4% {venta[\"folio\"]}',)\n"
            ")"
        )
    )

    pdf.hallazgo(
        "S-8", "ALTO",
        "N+1 queries en listado de mesas (impacto en produccion)",
        "server.py:358-384",
        [
            "Con 20 mesas y 3 ordenes cada una = 80+ queries por cada poll del frontend. "
            "Si el frontend hace polling cada 5 segundos, son ~1,000 queries/minuto solo "
            "para la vista de mesas.",
        ],
        code_snippet=(
            "for m in mesas_raw:               # query 1: todas las mesas\n"
            "    ordenes = conn.execute(...)   # query por mesa\n"
            "    for o in ordenes:\n"
            "        items = conn.execute(...) # query por orden"
        )
    )

    pdf.hallazgo(
        "S-9", "MEDIO",
        "Paginacion hardcodeada y sin offset",
        "modules/database.py:522, 541, 719",
        [
            "No hay parametro offset ni cursor. Cuando el historial supere 200 registros, "
            "los mas antiguos son invisibles en la UI sin ningun aviso al usuario.",
        ],
        code_snippet=(
            "def listar_gastos(limit=200):   # sin offset\n"
            "def listar_ingresos(limit=200): # sin offset\n"
            "def listar_nominas(limit=100):  # sin offset"
        )
    )

    pdf.hallazgo(
        "S-10", "MEDIO",
        "Credencial de email en base de datos sin cifrar",
        "modules/database.py:1275-1281",
        [
            "La contrasena del email se guarda en texto plano en config WHERE "
            "clave='email_password'. SQLite no tiene cifrado nativo, por lo que cualquier "
            "backup, volcado de base de datos o acceso fisico al archivo .db expone las "
            "credenciales de email.",
        ]
    )

    # =========================================================================
    # PLAN DE REMEDIACION
    # =========================================================================
    pdf.section_title(
        "Plan de Remediacion Arquitectonica",
        "Secuencia de implementacion recomendada -- Bloques A -> B -> C -> D"
    )

    pdf.bloque_remediacion(
        "A", "Seguridad critica -- aplicar antes de continuar en produccion", [
            (1, "Hashear credenciales del sistema: Mover SYSTEM_USERS a variables de "
                "entorno o tabla config, hashear passwords con bcrypt o argon2."),
            (2, "Implementar sesiones/tokens en la API: Agregar FastAPI Depends con "
                "validacion de token en todos los endpoints sensibles. El /api/login "
                "debe emitir un JWT o cookie firmada."),
            (3, "Eliminar usuario_id del request body en operaciones privilegiadas: "
                "El usuario autenticado debe derivarse del token, no del body. "
                "Eliminar usuario_id de CerrarMesaReq, GastoReq, CorteReq, etc."),
            (4, "Soft-delete para gastos e ingresos: Reemplazar DELETE FROM "
                "gastos/ingresos por UPDATE ... SET anulado=1, anulado_at=..., "
                "anulado_por=.... Agregar WHERE anulado IS NULL OR anulado=0 en "
                "todas las consultas de resumen."),
        ]
    )

    pdf.bloque_remediacion(
        "B", "Integridad transaccional financiera", [
            (5, "Envolver cerrar_mesa y registrar_venta en transacciones atomicas: "
                "try/except con conn.rollback() en el bloque except y re-raise de "
                "la excepcion."),
            (6, "Corregir corregir_venta para manejar comisiones: Al cambiar metodo "
                "de pago, eliminar el gasto de comision previo y, si el nuevo metodo "
                "es Tarjeta, crear uno nuevo con el monto correcto."),
            (7, "Folio atomico con secuencia en config: Usar UPDATE config SET "
                "valor=valor+1 + SELECT en la misma transaccion para garantizar "
                "unicidad sin condicion de carrera."),
            (8, "Proteger stock contra negativos: Agregar AND stock_local >= ? al "
                "UPDATE y verificar rowcount == 1; si es 0, abortar la transaccion."),
        ]
    )

    pdf.bloque_remediacion(
        "C", "Correccion de reportes financieros", [
            (9,  "Unificar zona horaria: Elegir un solo origen de timestamps -- "
                 "datetime('now') UTC en SQLite + conversion en Python, o "
                 "datetime('now','localtime') consistente. No mezclar ambos."),
            (10, "Corregir obtener_resumen_semana -- Bug #1: Alinear el filtro "
                 "'desde' (ultimo corte) en el desglose diario del semanal para "
                 "que sea consistente con obtener_resumen_dia."),
            (11, "Corregir obtener_resumen_semana -- Bug #2: Restar gastos_caja del "
                 "total_efectivo semanal con la misma logica que el diario."),
            (12, "Corregir obtener_resumen_semana -- Bug #3: Incluir inv "
                 "(inversion/costo de mercancia) en la formula de utilidad semanal."),
            (13, "Corregir obtener_resumen_semana -- Bug #4: Evitar doble-conteo de "
                 "transferencias separando monto_tarjeta_puro y monto_transferencia "
                 "en la consulta."),
        ]
    )

    pdf.bloque_remediacion(
        "D", "Rendimiento y observabilidad", [
            (14, "Eliminar N+1 en api_mesas: Reemplazar el triple loop con dos queries "
                 "(todas las ordenes abiertas + todos sus items) y agrupar en Python."),
            (15, "Agregar paginacion real: Parametros offset: int = 0, limit: int = 50 "
                 "en listar_gastos, listar_ingresos, listar_nominas. Retornar "
                 "{\"total\": N, \"items\": [...]}."),
            (16, "Agregar tabla de auditoria: Crear audit_log (id, tabla, registro_id, "
                 "accion, usuario_id, datos_anteriores, datos_nuevos, created_at) y "
                 "escribir en cada anulacion, correccion y eliminacion."),
        ]
    )

    # =========================================================================
    # ANALISIS DISCREPANCIAS DIARIO vs SEMANAL
    # =========================================================================
    pdf.section_title(
        "Analisis de Discrepancias: Diario vs. Semanal",
        "Causa raiz de los reportes financieros inconsistentes -- modules/database.py"
    )

    pdf.bug_discrepancia(
        1, "CRITICO",
        "El filtro 'desde' (corte) existe en el diario pero no en el semanal",
        "database.py:764-767 vs 954-958",
        [
            "El reporte diario filtra desde el ultimo corte de caja (turno actual). "
            "El desglose diario dentro del semanal filtra el dia completo sin considerar "
            "los cortes intermedios.",

            "Efecto concreto: Si el lunes hubo dos turnos con corte a las 2pm --"
            " Turno 1 (8am-2pm): $5,000 / Turno 2 (2pm-10pm): $3,000 -- el reporte "
            "diario del lunes mostrara $3,000. El semanal mostrara $8,000 para ese "
            "mismo lunes. Son datos distintos del mismo dia.",
        ],
        code_left=(
            "# obtener_resumen_dia\n"
            "# Solo el turno actual\n"
            "desde = last_corte['created_at']\n"
            "WHERE DATE(created_at)=?\n"
            "  AND created_at > ?"
        ),
        code_right=(
            "# obtener_resumen_semana\n"
            "# Dia entero, sin filtro\n"
            "# de turno/corte\n"
            "WHERE DATE(created_at)\n"
            "  BETWEEN ? AND ?"
        ),
        label_left="DIARIO (turno actual)",
        label_right="SEMANAL (dia completo)"
    )

    pdf.bug_discrepancia(
        2, "ALTO",
        "Formula del efectivo esperado es diferente entre diario y semanal",
        "database.py:854-858 vs 1103-1104",
        [
            "El diario resta los gastos de caja del total de efectivo para obtener el "
            "'efectivo_esperado'. El semanal retorna el total de efectivo sin restar ningun "
            "gasto. Si en la semana hubo $2,000 en gastos pagados en efectivo, el acumulado "
            "semanal de efectivo estara $2,000 por encima de la suma de los diarios.",
        ],
        code_left=(
            "# DIARIO -- resta gastos\n"
            "efectivo_esperado =\n"
            "  total_ef - gastos_caja"
        ),
        code_right=(
            "# SEMANAL -- sin restar\n"
            "'total_efectivo':\n"
            "  rv['total_efectivo']\n"
            "  + ingresos['ef']"
        ),
        label_left="Diario (correcto)",
        label_right="Semanal (falta gastos_caja)"
    )

    pdf.bug_discrepancia(
        3, "ALTO",
        "Formula de utilidad incompatible entre diario y semanal",
        "database.py:885 vs 1108",
        [
            "El diario descuenta el costo de los productos vendidos (inversion) de la "
            "utilidad. El semanal no. Si el costo de mercancia de la semana es $10,000, "
            "la utilidad semanal aparecera $10,000 mas alta que la suma de las "
            "utilidades diarias.",
        ],
        code_left=(
            "# DIARIO -- incluye costo\n"
            "utilidad =\n"
            "  total_ventas\n"
            "  - inv['inversion']\n"
            "  - total_gastos"
        ),
        code_right=(
            "# SEMANAL -- sin costo\n"
            "utilidad =\n"
            "  total_semana\n"
            "  + total_ingresos\n"
            "  - gastos['total']"
        ),
        label_left="Diario (correcto)",
        label_right="Semanal (falta inversion)"
    )

    pdf.bug_discrepancia(
        4, "MEDIO",
        "Transferencias contadas dos veces en el semanal",
        "database.py:921-922 y 1112",
        [
            "Las transferencias se guardan en monto_tarjeta al momento de registrar la "
            "venta. El semanal expone tanto total_tarjeta (que incluye transferencias via "
            "monto_tarjeta) como total_transferencia (que las suma de nuevo por "
            "metodo_pago='Transferencia'). Ambos campos se muestran simultaneamente en "
            "la UI, inflando el total aparente.",
        ],
        code_left=(
            "# En registrar_venta\n"
            "monto_tarjeta = total\n"
            "# Transfer guardada\n"
            "# en monto_tarjeta"
        ),
        code_right=(
            "# En resumen_semana\n"
            "total_tarjeta =\n"
            "  SUM(monto_tarjeta) # incl. transfer\n"
            "total_transferencia =\n"
            "  SUM(total) WHERE\n"
            "  metodo='Transfer' # duplicado"
        ),
        label_left="Origen del dato",
        label_right="Doble conteo en semanal"
    )

    # Tabla resumen
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*C_DARK)
    pdf.cell(0, 8, "Tabla resumen -- Causas raiz de discrepancias", **_lm())
    pdf.ln(1)

    pdf.tabla_resumen(
        headers=["Bug", "Fuente de discrepancia", "Sev.", "Impacto en numeros"],
        col_widths=[12, 72, 18, 72],
        rows=[
            ["#1", "Diario = turno actual / Semanal = dia completo",    "CRITICO",
             "Diferencia = suma de turnos anteriores del dia"],
            ["#2", "Efectivo: semanal no resta gastos de caja",          "ALTO",
             "Diferencia = total gastos caja de la semana"],
            ["#3", "Utilidad: semanal no resta costo de mercancia",      "ALTO",
             "Diferencia = inversion/costo total de la semana"],
            ["#4", "Transferencias doble-contadas en semanal",           "MEDIO",
             "Diferencia = total transferencias de la semana"],
        ]
    )

    # Nota final
    pdf.ln(4)
    if pdf.get_y() > 250:
        pdf.add_page()
    self_y = pdf.get_y()
    self_x = 18
    pdf.set_fill_color(240, 249, 255)
    pdf.set_draw_color(*C_ACCENT)
    pdf.set_line_width(0.4)
    pdf.rect(self_x, self_y, 174, 22, "FD")
    pdf.set_xy(self_x + 4, self_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_ACCENT)
    pdf.cell(0, 5,
             "Los Bugs #1-#4 estan localizados exclusivamente en obtener_resumen_semana",
             **_lm())
    pdf.set_x(self_x + 4)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*C_DARK)
    pdf.multi_cell(
        166, 4.5,
        "No requieren cambios en el esquema de base de datos. Son correcciones de "
        "logica en consultas SQL y calculos Python, correspondientes a los pasos "
        "10-13 del Plan de Remediacion (Bloque C). Una vez aplicados, los totales "
        "diarios y el acumulado semanal deberan cuadrar exactamente."
    )

    # Guardar
    pdf.output(str(OUTPUT))
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build()
