#!/usr/bin/env python3
"""
Editor visual de tickets — solo Linux (desarrollo).

No modifica ni depende del servidor Windows del POS.
Guarda la plantilla en config/ticket_template.json (súbela a git para que Windows la use).

Uso:
    python ticket_editor_linux.py
    → http://localhost:8765
"""
from __future__ import annotations

import json
import mimetypes
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "ticket_template.json"
HTML_PATH = Path(__file__).with_name("ticket_editor_linux.html")
from modules.ticket_layout import DEFAULT_LAYERS, get_effective_layers

ASSETS_DIR = ROOT / "assets"
PORT = 8765

DEFAULT_CONFIG: dict = {
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


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg.update(saved)
        except Exception as exc:
            print(f"[ticket-editor] No se pudo leer {CONFIG_PATH}: {exc}")
    return cfg


def save_config(data: dict) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    allowed = set(DEFAULT_CONFIG.keys())
    cfg.update({k: v for k, v in data.items() if k in allowed})
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"[ticket-editor] Plantilla guardada → {CONFIG_PATH}")
    return cfg


class TicketEditorHandler(BaseHTTPRequestHandler):
    server_version = "TicketEditorLinux/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print(f"[ticket-editor] {self.address_string()} - {fmt % args}")

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            if not HTML_PATH.exists():
                self.send_error(500, f"Falta {HTML_PATH.name}")
                return
            self._send_bytes(HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            return

        if path == "/api/ticket-template":
            cfg = load_config()
            self._send_json({
                "config": cfg,
                "sample_venta": SAMPLE_VENTA,
                "sample_cajero": "Diana",
            })
            return

        if path.startswith("/assets/"):
            rel = unquote(path[len("/assets/"):])
            target = (ASSETS_DIR / rel).resolve()
            if not str(target).startswith(str(ASSETS_DIR.resolve())) or not target.is_file():
                self.send_error(404)
                return
            mime, _ = mimetypes.guess_type(str(target))
            self._send_bytes(target.read_bytes(), mime or "application/octet-stream")
            return

        self.send_error(404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/ticket-template":
            try:
                cfg = save_config(self._read_json_body())
                self._send_json({"ok": True, "config": cfg})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/ticket-template/reset":
            cfg = save_config(DEFAULT_CONFIG)
            self._send_json({"ok": True, "config": cfg})
            return

        if path == "/api/ticket-preview":
            try:
                body = self._read_json_body()
                cfg = body.get("config") or load_config()
                footer_index = int(body.get("footer_index", 0))
                from modules.printer import preview_ticket_layout
                layout = preview_ticket_layout(
                    venta=SAMPLE_VENTA,
                    cajero="Diana",
                    cfg=cfg,
                    footer_index=footer_index,
                )
                self._send_json({"ok": True, "layout": layout})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        if path == "/api/print-test":
            try:
                body = self._read_json_body()
                cfg = body.get("config") or load_config()
                footer_index = int(body.get("footer_index", 0))
                from modules.printer import imprimir_ticket_prueba
                ok = imprimir_ticket_prueba(cajero="Diana", cfg=cfg, footer_index=footer_index)
                msg = "Ticket de prueba enviado a la impresora." if ok else "No se detectó impresora física (se simuló en la consola/sistema)."
                self._send_json({"ok": ok, "message": msg})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return

        self.send_error(404)


def main() -> None:
    if sys.platform == "win32":
        print("Este editor es solo para Linux. En Windows usa el POS normal.")
        sys.exit(1)

    if not HTML_PATH.exists():
        print(f"Error: no se encontró {HTML_PATH}")
        sys.exit(1)

    server = ThreadingHTTPServer(("127.0.0.1", PORT), TicketEditorHandler)
    url = f"http://localhost:{PORT}"
    print()
    print("  🖨️  Editor de Tickets (Linux)")
    print(f"  {url}")
    print(f"  Plantilla: {CONFIG_PATH}")
    print("  Ctrl+C para salir")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Editor detenido.")
        server.server_close()


if __name__ == "__main__":
    main()
