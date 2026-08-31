"""
Layout de ticket térmico — 48 columnas, sin dependencias de impresora.
Usado por la vista previa del editor y por printer.py.
Soporta Sistema de Capas / Bloques reordenables y personalizables.
"""
from __future__ import annotations

from pathlib import Path

ANCHO = 48

DEFAULT_LAYERS = [
    {"id": "logo", "type": "logo", "name": "🖼️ Logo / Nombre", "enabled": True},
    {"id": "slogan", "type": "slogan", "name": "💬 Slogan", "enabled": True},
    {"id": "sep_1", "type": "separator", "name": "➖ Separador", "enabled": True, "style": "dot_star"},
    {"id": "info", "type": "info", "name": "📝 Datos de Venta", "enabled": True},
    {"id": "items", "type": "items", "name": "🛒 Lista de Artículos", "enabled": True},
    {"id": "total", "type": "total", "name": "💵 Monto Total", "enabled": True},
    {"id": "hearts", "type": "hearts", "name": "❤️ Línea de Corazones", "enabled": True},
    {"id": "payment", "type": "payment", "name": "💳 Forma de Pago", "enabled": True},
    {"id": "footer", "type": "footer", "name": "📜 Mensaje del Pie", "enabled": True},
    {"id": "qr", "type": "qr", "name": "📱 Código QR e Instagram", "enabled": True},
    {"id": "sep_2", "type": "separator", "name": "➖ Separador Final", "enabled": True, "style": "dot_star"},
]


def separator_line(style: str) -> str:
    if style == "stars":
        return ("* " * (ANCHO // 2))[:ANCHO]
    if style == "thin":
        return "-" * ANCHO
    if style == "bold":
        return "=" * ANCHO
    return (". * " * (ANCHO // 4))[:ANCHO]


def get_effective_layers(cfg: dict) -> list[dict]:
    """Retorna la lista de capas ordenadas. Si no existen en cfg, se genera dinámicamente."""
    if "layers" in cfg and isinstance(cfg["layers"], list) and len(cfg["layers"]) > 0:
        return cfg["layers"]

    layers = []
    if cfg.get("show_logo", True):
        layers.append({"id": "logo", "type": "logo", "name": "🖼️ Logo / Nombre", "enabled": True})
    if cfg.get("show_slogan", True):
        layers.append({"id": "slogan", "type": "slogan", "name": "💬 Slogan", "enabled": True})

    sep_style = cfg.get("separator_style", "dot_star")
    layers.append({"id": "sep_1", "type": "separator", "name": "➖ Separador", "enabled": True, "style": sep_style})

    if cfg.get("show_info", True):
        layers.append({"id": "info", "type": "info", "name": "📝 Datos de Venta", "enabled": True})
    if cfg.get("show_items", True):
        layers.append({"id": "items", "type": "items", "name": "🛒 Lista de Artículos", "enabled": True})
    if cfg.get("show_total", True):
        layers.append({"id": "total", "type": "total", "name": "💵 Monto Total", "enabled": True})
    if cfg.get("show_hearts", True):
        layers.append({"id": "hearts", "type": "hearts", "name": "❤️ Línea de Corazones", "enabled": True})
    if cfg.get("show_payment", True):
        layers.append({"id": "payment", "type": "payment", "name": "💳 Forma de Pago", "enabled": True})
    if cfg.get("show_footer", True):
        layers.append({"id": "footer", "type": "footer", "name": "📜 Mensaje del Pie", "enabled": True})
    if cfg.get("show_qr", True):
        layers.append({"id": "qr", "type": "qr", "name": "📱 Código QR e Instagram", "enabled": True})

    layers.append({"id": "sep_2", "type": "separator", "name": "➖ Separador Final", "enabled": True, "style": sep_style})
    return layers


def build_ticket_lines(
    venta: dict,
    cajero: str,
    cfg: dict,
    *,
    footer_index: int = 0,
    logo_exists: bool = False,
) -> list[dict]:
    """
    Líneas del ticket ordenadas por el sistema de capas.
    """
    stars = ("* " * (ANCHO // 2))[:ANCHO]
    footer_msgs = cfg.get("footer_messages") or []
    fecha = str(venta.get("fecha", ""))[:16]
    lines: list[dict] = []

    def add(text: str = "", align: str = "left", style: str = "normal") -> None:
        lines.append({"align": align, "style": style, "text": text})

    def blank() -> None:
        lines.append({"blank": True})

    layers = get_effective_layers(cfg)
    for layer in layers:
        if not layer.get("enabled", True):
            continue

        ltype = layer.get("type")

        if ltype == "logo":
            if logo_exists:
                lines.append({"type": "logo", "align": "center"})
            else:
                add(cfg.get("fallback_name", "ESTUDIO DECO").center(ANCHO), "left", "double")
            blank()

        elif ltype == "slogan":
            slogan = cfg.get("slogan", "")
            if slogan:
                add(str(slogan).center(ANCHO), "left", "small")
                blank()
                blank()

        elif ltype == "separator":
            style = layer.get("style") or cfg.get("separator_style", "dot_star")
            add(separator_line(style))
            blank()

        elif ltype == "info":
            add(f"  Fecha    : {fecha}", "left", "small")
            add(f"  Folio    : {venta.get('folio', '')}", "left", "small")
            add(f"  Atendio  : {cajero}", "left", "small")
            if venta.get("mesa"):
                add(f"  Mesa     : {venta['mesa']}", "left", "small")
            blank()
            blank()

        elif ltype == "items":
            add(stars, "left")
            add(f"  {'ARTICULO':<24} {'CANT':>4}  {'TOTAL':>8}", "left", "small-bold")
            add(stars, "left")
            for item in venta.get("items", []):
                nombre = item.get("nombre") or item.get("nombre_producto", "")
                cant = item["cantidad"]
                sub = cant * item["precio_unitario"]
                n24 = nombre[:24]
                add(f"  {n24:<24} {cant:>4}  ${sub:>8,.2f}", "left", "small")
                if len(nombre) > 24:
                    add(f"    {nombre[24:46]}", "left", "small")
            blank()

        elif ltype == "total":
            add(stars, "left")
            blank()
            blank()
            add(f"  ${venta.get('total', 0):,.2f}  ", "center", "double")
            blank()

        elif ltype == "hearts":
            hearts = cfg.get("hearts_line", "")
            if hearts:
                add(hearts, "center")
                blank()

        elif ltype == "payment":
            mp = venta.get("metodo_pago", "")
            add(f"Forma de pago: {mp}", "center", "small")
            if mp == "Mixto":
                add(f"  Efectivo : ${venta.get('monto_efectivo', 0):,.2f}", "center", "small")
                add(f"  Tarjeta  : ${venta.get('monto_tarjeta', 0):,.2f}", "center", "small")
            elif mp == "Efectivo" and venta.get("efectivo_recibido", 0) > 0:
                add(f"  Recibido : ${venta.get('efectivo_recibido', 0):,.2f}", "center", "small")
                add(f"  Cambio   : ${venta.get('cambio', 0):,.2f}", "center", "small")
            blank()
            add(stars, "left")
            blank()
            blank()

        elif ltype == "footer":
            if footer_msgs:
                idx = footer_index % len(footer_msgs)
                add(footer_msgs[idx].center(ANCHO), "center", "small")
                blank()
                blank()

        elif ltype == "qr":
            lines.append({"type": "qr", "align": "center"})
            handle = cfg.get("instagram_handle", "")
            if handle:
                add(handle, "center", "double")
            blank()
            blank()

    return lines


def lines_to_plaintext(lines: list[dict]) -> str:
    out: list[str] = []
    for row in lines:
        if row.get("blank"):
            out.append("")
            continue
        if row.get("type") in ("logo", "qr"):
            label = "[ LOGO ]" if row["type"] == "logo" else "[ QR ]"
            out.append(label.center(ANCHO))
            continue
        text = row.get("text", "")
        align = row.get("align", "left")
        if align == "center" and len(text) <= ANCHO and not text.startswith("  "):
            out.append(text)
        else:
            out.append(text[:ANCHO])
    return "\n".join(out)
