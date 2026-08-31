"""
modules/printer.py — Tickets ESC/POS · Estudio Deco
"""
from pathlib import Path
from datetime import datetime
from PIL import Image
import json, os, random, sys, subprocess, tempfile

from modules.ticket_layout import (
    build_ticket_lines,
    lines_to_plaintext,
    get_effective_layers,
    DEFAULT_LAYERS,
    separator_line as _separator_line_layout,
)

ROOT          = Path(__file__).resolve().parent.parent
LOGO_PATH     = ROOT / "assets" / "logo.png"
CONFIG_PATH   = ROOT / "config" / "ticket_template.json"
ANCHO         = 48       # columnas Font-A (papel 80 mm)
ANCHO_PX      = 384      # pixeles imprimibles del rodillo

PRINTER_NAME = os.environ.get("ESTUDIO_PRINTER", "POS-80")

DEFAULT_TICKET_CONFIG = {
    "fallback_name": "ESTUDIO DECO",
    "slogan": "Crea y decora en Estudio Deco",
    "separator_style": "dot_star",
    "show_logo": True,
    "show_slogan": True,
    "show_info": True,
    "show_items": True,
    "show_total": True,
    "show_hearts": True,
    "hearts_line": " <3    <3    <3    <3    <3 ",
    "show_payment": True,
    "show_footer": True,
    "show_qr": True,
    "instagram_handle": "@estudiodecomx",
    "instagram_url": "https://instagram.com/estudiodecomx",
    "footer_messages": [
        "Hecho con amor en Estudio Deco",
        "Tu creatividad nos inspira",
        "Gracias por crear con nosotras",
        "Donde la creatividad cobra vida",
        "Nos vemos en la proxima creacion",
        "Cafe & journal <3",
        "Otro día, otra creación <3",
        "Tu espacio creativo favorito <3",
    ],
    "layers": DEFAULT_LAYERS,
}

SAMPLE_VENTA = {
    "folio": "A-0042",
    "total": 385.50,
    "metodo_pago": "Efectivo",
    "efectivo_recibido": 500.0,
    "cambio": 114.50,
    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "mesa": "Mesa 3 - Ana",
    "items": [
        {"nombre": "Latte vainilla", "cantidad": 2, "precio_unitario": 65.0},
        {"nombre": "Journal personalizado con flores", "cantidad": 1, "precio_unitario": 255.50},
    ],
}


def load_ticket_config() -> dict:
    cfg = dict(DEFAULT_TICKET_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception as e:
            print(f"[TICKET] No se pudo leer plantilla: {e}")
    return cfg


def save_ticket_config(data: dict) -> dict:
    cfg = dict(DEFAULT_TICKET_CONFIG)
    cfg.update(data)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def _separator_line(style: str) -> str:
    return _separator_line_layout(style)

# ── Comandos ESC/POS ─────────────────────────────────────────────────────────
_E = b'\x1b'
_G = b'\x1d'

INIT      = _E + b'@'           # inicializar impresora
CP437     = _E + b't\x00'       # codepage PC437 (acentos + box-drawing)
BOLD_ON   = _E + b'E\x01'
BOLD_OFF  = _E + b'E\x00'
ALIGN_L   = _E + b'a\x00'
ALIGN_C   = _E + b'a\x01'
ALIGN_R   = _E + b'a\x02'
NORMAL    = _E + b'!\x00'
DBL_H     = _E + b'!\x10'      # doble alto
DBL_HW    = _E + b'!\x30'      # doble alto + ancho
FONT_A    = _E + b'M\x00'      # fuente normal
FONT_B    = _E + b'M\x01'      # fuente pequeña
CUT       = _G  + b'V\x41\x05' # corte parcial + avance 5 mm

def _feed(n: int = 1) -> bytes:
    return _E + b'd' + bytes([n])

def _txt(s: str) -> bytes:
    """Codifica a CP437: soporta español y caracteres de caja."""
    return s.encode('cp437', errors='replace')

# ── Separadores decorativos (ASCII puro — siempre funciona) ──────────────────
_STARS    = ('* ' * (ANCHO // 2))[:ANCHO]           # * * * * * * * *
_DOT_STAR = ('. * ' * (ANCHO // 4))[:ANCHO]         # . * . * . * . *
_THIN_LINE = '-' * ANCHO                             # ----------------
_BOLD_LINE = '=' * ANCHO                             # ================

# ── QR Code → bytes ESC/POS ─────────────────────────────────────────────────
def _qr_escpos(url: str, max_w: int = 200) -> bytes:
    """Genera un QR como imagen raster ESC/POS."""
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('L')

        # Escalar al ancho deseado
        r = min(max_w / img.width, max_w / img.height)
        img = img.resize((int(img.width * r), int(img.height * r)),
                         Image.Resampling.NEAREST)

        w, h = img.size
        wb = (w + 7) // 8
        px = img.load()

        hdr  = _G + b'v0\x00'
        hdr += bytes([wb & 0xFF, wb >> 8, h & 0xFF, h >> 8])

        data = bytearray()
        for y in range(h):
            for bx in range(wb):
                byte = 0
                for bit in range(8):
                    x = bx * 8 + bit
                    if x < w and px[x, y] < 128:
                        byte |= (1 << (7 - bit))
                data.append(byte)

        return bytes(hdr) + bytes(data)
    except Exception as e:
        print(f"[QR] Error: {e}")
        return b''

# ── Imagen → bytes ESC/POS raster (GS v 0) ───────────────────────────────────
def _imagen_escpos(path: Path, max_w: int, max_h: int) -> bytes:
    """Convierte cualquier PNG a bytes GS v 0 para impresora termica."""
    if not path.exists():
        return b''
    try:
        raw = Image.open(path)
        if raw.mode in ('RGBA', 'P') or 'transparency' in raw.info:
            bg  = Image.new('RGB', raw.size, (255, 255, 255))
            src = raw.convert('RGBA')
            bg.paste(src, mask=src.split()[3])
            raw = bg
        img = raw.convert('L')

        r   = min(max_w / img.width, max_h / img.height)
        img = img.resize(
            (int(img.width * r), int(img.height * r)),
            Image.Resampling.LANCZOS,
        )

        w, h = img.size
        wb   = (w + 7) // 8
        px   = img.load()

        hdr  = _G + b'v0\x00'
        hdr += bytes([wb & 0xFF, wb >> 8, h & 0xFF, h >> 8])

        data = bytearray()
        for y in range(h):
            for bx in range(wb):
                byte = 0
                for b in range(8):
                    x = bx * 8 + b
                    if x < w and px[x, y] < 128:
                        byte |= (1 << (7 - b))
                data.append(byte)

        return bytes(hdr) + bytes(data)
    except Exception as e:
        print(f"[IMG] {path.name}: {e}")
        return b''

def _logo_escpos() -> bytes:
    return _imagen_escpos(LOGO_PATH, max_w=384, max_h=250)

# ── Envio ─────────────────────────────────────────────────────────────────────
def _win_raw(data: bytes) -> bool:
    try:
        import win32print
    except ImportError:
        print("[PRINTER] win32print no instalado — instala pywin32")
        return False
    try:
        h = win32print.OpenPrinter(PRINTER_NAME)
        try:
            win32print.StartDocPrinter(h, 1, ("Ticket Estudio Deco", None, "RAW"))
            win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, data)
            win32print.EndPagePrinter(h)
            win32print.EndDocPrinter(h)
        finally:
            win32print.ClosePrinter(h)
        return True
    except Exception as e:
        print(f"[PRINTER] win32print error: {e}")
        return False

def _usb(data: bytes) -> bool:
    port = os.environ.get("PRINTER_USB_PORT", "")
    if not port:
        for candidate in ["/dev/usb/lp0", "/dev/usb/lp1", "/dev/ttyUSB0", "/dev/ttyACM0"]:
            if os.path.exists(candidate):
                port = candidate
                break
    if not port:
        return False
    try:
        with open(port, 'wb') as f:
            f.write(data)
            f.flush()
        print(f"[PRINTER] ✓ Enviado a impresora USB en {port}")
        return True
    except Exception as e:
        print(f"[PRINTER] Error escribiendo en USB {port}: {e}")
        return False

def _linux_raw(data: bytes) -> bool:
    printer = os.environ.get("ESTUDIO_PRINTER", "")
    if printer:
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".bin")
            os.write(fd, data)
            os.close(fd)
            result = subprocess.run(
                ["lp", "-d", printer, "-o", "raw", path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                print(f"[PRINTER] lp enviado a {printer}")
                return True
        except Exception:
            pass
        finally:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    # Intentar puertos de impresora USB comunes en Linux
    for dev in ["/dev/usb/lp0", "/dev/usb/lp1", "/dev/ttyUSB0", "/dev/ttyACM0"]:
        if os.path.exists(dev):
            try:
                with open(dev, "wb") as f:
                    f.write(data)
                print(f"[PRINTER] Enviado a puerto USB Linux: {dev}")
                return True
            except Exception as e:
                print(f"[PRINTER] Error escribiendo en {dev}: {e}")

    # Fallback de simulación en Linux para desarrollo
    try:
        out_file = Path(tempfile.gettempdir()) / "ultimo_ticket_linux.bin"
        out_file.write_bytes(data)
        print(f"[PRINTER] (Simulación Linux) Ticket grabado en {out_file}")
        return True
    except Exception as e:
        print(f"[PRINTER] Simulación error: {e}")
        return False

def _enviar(data: bytes) -> bool:
    if _usb(data):
        return True
    if sys.platform != "win32" and _linux_raw(data):
        return True
    return _win_raw(data)

# ── Constructor del ticket ESC/POS ───────────────────────────────────────────
def _ticket_bytes(venta: dict, cajero: str, cfg: dict | None = None, footer_index: int | None = None) -> bytes:
    cfg = cfg or load_ticket_config()
    stars = ('* ' * (ANCHO // 2))[:ANCHO]
    footer_msgs = cfg.get("footer_messages") or DEFAULT_TICKET_CONFIG["footer_messages"]

    b = bytearray()
    b += INIT + CP437

    layers = get_effective_layers(cfg)
    for layer in layers:
        if not layer.get("enabled", True):
            continue

        ltype = layer.get("type")

        if ltype == "logo":
            logo = _logo_escpos()
            if logo:
                b += ALIGN_C + logo + _feed(1)
            else:
                b += ALIGN_C + BOLD_ON + DBL_HW
                b += _txt(f'{cfg.get("fallback_name", "ESTUDIO DECO")}\n')
                b += NORMAL + BOLD_OFF + _feed(1)

        elif ltype == "slogan":
            slogan = cfg.get("slogan", "")
            if slogan:
                b += ALIGN_C + FONT_B
                b += _txt(slogan.center(ANCHO) + '\n')
                b += FONT_A + _feed(2)

        elif ltype == "separator":
            style = layer.get("style") or cfg.get("separator_style", "dot_star")
            sep = _separator_line(style)
            b += _txt(sep + '\n') + _feed(1)

        elif ltype == "info":
            b += ALIGN_L + FONT_B
            fecha = str(venta.get('fecha', ''))[:16]
            b += _txt(f'  Fecha    : {fecha}\n')
            b += _txt(f'  Folio    : {venta.get("folio", "")}\n')
            b += _txt(f'  Atendio  : {cajero}\n')
            if venta.get('mesa'):
                b += _txt(f'  Mesa     : {venta["mesa"]}\n')
            b += FONT_A + _feed(2)

        elif ltype == "items":
            b += _txt(stars + '\n')
            b += BOLD_ON + FONT_B
            b += _txt(f"  {'ARTICULO':<24} {'CANT':>4}  {'TOTAL':>8}\n")
            b += BOLD_OFF + _txt(stars + '\n')
            b += ALIGN_L + FONT_B
            for item in venta.get('items', []):
                nombre = (item.get('nombre') or item.get('nombre_producto', ''))
                cant   = item['cantidad']
                sub    = cant * item['precio_unitario']
                n24    = nombre[:24]
                b += _txt(f'  {n24:<24} {cant:>4}  ${sub:>8,.2f}\n')
                if len(nombre) > 24:
                    b += _txt(f'    {nombre[24:46]}\n')
            b += FONT_A + _feed(1)

        elif ltype == "total":
            b += _txt(stars + '\n') + _feed(2)
            b += ALIGN_C + BOLD_ON + DBL_HW
            b += _txt(f'  ${venta.get("total", 0):,.2f}  \n')
            b += NORMAL + BOLD_OFF + _feed(1)

        elif ltype == "hearts":
            hearts = cfg.get("hearts_line", "")
            if hearts:
                b += ALIGN_C + _txt(hearts + '\n') + _feed(1)

        elif ltype == "payment":
            b += ALIGN_C + FONT_B
            mp = venta.get("metodo_pago", "")
            b += _txt(f'Forma de pago: {mp}\n')
            if mp == "Mixto":
                ef = venta.get("monto_efectivo", 0)
                tar = venta.get("monto_tarjeta", 0)
                b += _txt(f'  Efectivo : ${ef:,.2f}\n')
                b += _txt(f'  Tarjeta  : ${tar:,.2f}\n')
            elif mp == "Efectivo" and venta.get("efectivo_recibido", 0) > 0:
                recibido = venta.get("efectivo_recibido", 0)
                cambio = venta.get("cambio", 0)
                b += _txt(f'  Recibido : ${recibido:,.2f}\n')
                b += _txt(f'  Cambio   : ${cambio:,.2f}\n')
            b += FONT_A + _feed(1)
            b += _txt(stars + '\n') + _feed(2)

        elif ltype == "footer":
            if footer_msgs:
                b += ALIGN_C + FONT_B
                if footer_index is not None:
                    msg = footer_msgs[footer_index % len(footer_msgs)]
                else:
                    msg = random.choice(footer_msgs)
                b += _txt(msg.center(ANCHO) + '\n')
                b += FONT_A + _feed(2)

        elif ltype == "qr":
            ig_url = cfg.get("instagram_url", "https://instagram.com/estudiodecomx")
            qr = _qr_escpos(ig_url, max_w=180)
            if qr:
                b += ALIGN_C + qr + _feed(1)
            handle = cfg.get("instagram_handle", "@estudiodecomx")
            if handle:
                b += ALIGN_C + BOLD_ON + DBL_HW
                b += _txt(f'{handle}\n')
                b += NORMAL + BOLD_OFF + _feed(2)

    b += _feed(4)
    b += CUT
    return bytes(b)

# ── API publica ───────────────────────────────────────────────────────────────
def imprimir_ticket(venta: dict, cajero: str, cfg: dict | None = None, footer_index: int | None = None) -> bool:
    try:
        ok = _enviar(_ticket_bytes(venta, cajero, cfg, footer_index))
        print(f"[PRINTER] {'OK' if ok else 'SIN IMPRESORA'} — folio {venta['folio']}")
        return ok
    except Exception as e:
        print(f"[PRINTER] Error: {e}")
        return False


def imprimir_ticket_prueba(cajero: str = "Diana", cfg: dict | None = None, footer_index: int = 0) -> bool:
    """Imprime un ticket de muestra con la plantilla actual (para previsualizar en papel)."""
    cfg = cfg or load_ticket_config()
    venta = dict(SAMPLE_VENTA)
    venta["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return imprimir_ticket(venta, cajero, cfg, footer_index)


def preview_ticket_layout(
    venta: dict,
    cajero: str,
    cfg: dict | None = None,
    footer_index: int = 0,
) -> dict:
    cfg = cfg or load_ticket_config()
    lines = build_ticket_lines(
        venta, cajero, cfg,
        footer_index=footer_index,
        logo_exists=LOGO_PATH.exists(),
    )
    return {"width": ANCHO, "lines": lines, "plaintext": lines_to_plaintext(lines)}

def imprimir_comanda(mesa_numero, items) -> bool:
    if not items:
        return False
    try:
        b  = bytearray(INIT + CP437)
        b += ALIGN_C + BOLD_ON + DBL_HW
        b += _txt(f'{mesa_numero}\n')
        b += NORMAL + BOLD_OFF + ALIGN_C + FONT_B
        b += _txt(datetime.now().strftime('%d/%m/%Y  %H:%M') + '\n')
        b += FONT_A + ALIGN_L
        b += _txt(('─' * ANCHO) + '\n')
        for i in items:
            b += BOLD_ON  + _txt(f'  x{i["cantidad"]}  ')
            b += BOLD_OFF + _txt(f'{i["nombre_producto"]}\n')
        b += _feed(3) + CUT
        ok = _enviar(bytes(b))
        print(f"[PRINTER] {'OK' if ok else 'SIN IMPRESORA'} — comanda mesa {mesa_numero}")
        return ok
    except Exception as e:
        print(f"[PRINTER] Error comanda: {e}")
        return False

# ── Preview en pantalla (Unicode libre, se muestra en CTkTextbox / editor) ───
def preview_ticket_text(venta: dict, cajero: str, cfg: dict | None = None, footer_index: int = 0) -> str:
    layout = preview_ticket_layout(venta, cajero, cfg, footer_index)
    return layout["plaintext"]

def imprimir_corte_caja(resumen: dict, cajero: str) -> bool:
    try:
        b = bytearray()
        b += INIT + CP437

        # Header
        b += ALIGN_C + BOLD_ON + DBL_HW
        b += _txt('CORTE DE CAJA\n')
        b += NORMAL + BOLD_OFF + FONT_B
        b += _txt('ESTUDIO DECO\n\n')
        b += FONT_A

        # Info
        b += ALIGN_L
        b += _txt(f'Fecha   : {resumen["fecha"]}\n')
        b += _txt(f'Cajero  : {cajero}\n')
        b += _txt(f'Impreso : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        b += _txt(_THIN_LINE + '\n')

        # Ventas
        b += BOLD_ON + _txt('INGRESOS\n') + BOLD_OFF
        b += _txt(f'Total Ventas ({resumen["num_ventas"]} tkts): ${resumen["total_ventas"]:.2f}\n')
        for t in resumen.get("ventas_por_tienda", []):
            b += _txt(f'  {t["tienda"][:16]:<16}: ${t["total"]:.2f}\n')

        # Ingresos adicionales
        if resumen.get("total_ingresos", 0) > 0:
            b += _txt(f'Ingresos Extra       : ${resumen["total_ingresos"]:.2f}\n')
            for i in resumen.get("ingresos_detalle", []):
                b += _txt(f'  {i["concepto"][:14]:<14} ({i["metodo_pago"][:3]}): ${i["monto"]:.2f}\n')

        b += _txt(_THIN_LINE + '\n')

        # Gastos
        b += BOLD_ON + _txt('EGRESOS\n') + BOLD_OFF
        b += _txt(f'Total Gastos         : ${resumen["total_gastos"]:.2f}\n')
        if resumen.get("gastos_detalle"):
            for g in resumen["gastos_detalle"]:
                b += _txt(f'  {g["concepto"][:16]:<16}: ${g["monto"]:.2f}\n')

        b += _txt(_THIN_LINE + '\n')

        # Utilidad
        b += BOLD_ON + _txt('RENDIMIENTO DEL DIA\n') + BOLD_OFF
        inversion = resumen.get("inversion", 0)
        utilidad = resumen.get("utilidad", resumen["total_ventas"] - resumen["total_gastos"])
        b += _txt(f'Ingresos Totales     : ${resumen["total_ventas"]:.2f}\n')
        b += _txt(f'- Inversion Prod.    : ${inversion:.2f}\n')
        b += _txt(f'- Gastos Operativos  : ${resumen["total_gastos"]:.2f}\n')
        b += _txt('--------------------------------\n')
        b += _txt(f'UTILIDAD BRUTA       : ${utilidad:.2f}\n')

        b += _txt(_THIN_LINE + '\n')

        # Desglose por método de pago (efectivo + tarjeta por separado)
        b += BOLD_ON + _txt('DESGLOSE DE CAJA\n') + BOLD_OFF
        total_ef  = resumen.get("total_efectivo", resumen.get("efectivo_esperado", 0))
        total_tar = resumen.get("total_tarjeta", 0)
        total_gas = resumen.get("total_gastos", 0)
        tar_neto  = resumen.get("tarjeta_esperado", total_tar - total_gas)
        total_esp = resumen.get("total_esperado", total_ef + tar_neto)

        b += _txt(f'{"Efectivo (ventas)":<22}: ${total_ef:.2f}\n')
        b += _txt(f'{"Tarjeta/Transfer.":<22}: ${total_tar:.2f}\n')
        b += _txt(f'{"Gastos (se rest. tarj.)":<22}: -${total_gas:.2f}\n')
        b += _txt('--------------------------------\n')

        # Efectivo en caja
        b += BOLD_ON + _txt('EFECTIVO EN CAJA:\n') + BOLD_OFF
        b += DBL_HW + BOLD_ON + ALIGN_C + _txt(f'${total_ef:.2f}\n') + NORMAL + BOLD_OFF + ALIGN_L

        # Tarjeta neta
        b += BOLD_ON + _txt('TARJETA (descontando gastos):\n') + BOLD_OFF
        b += DBL_HW + BOLD_ON + ALIGN_C + _txt(f'${tar_neto:.2f}\n') + NORMAL + BOLD_OFF + ALIGN_L

        # Total general
        b += BOLD_ON + _txt('TOTAL GENERAL:\n') + BOLD_OFF
        b += DBL_HW + BOLD_ON + ALIGN_C + _txt(f'${total_esp:.2f}\n') + NORMAL + BOLD_OFF + ALIGN_L

        b += _feed(2)
        b += ALIGN_C
        b += _txt('Firma del Cajero\n')
        b += _txt('_________________________\n')
        b += _txt(cajero + '\n')

        b += _feed(4) + CUT

        ok = _enviar(bytes(b))
        print(f"[PRINTER] Corte {'OK' if ok else 'FALLO'}")
        return ok
    except Exception as e:
        print(f"[PRINTER] Error corte: {e}")
        return False
