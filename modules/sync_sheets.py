"""
modules/sync_sheets.py
Hilo en segundo plano que sincroniza ventas locales → Google Sheets.

Requisitos:
  1. Archivo de credenciales: assets/credentials.json (Service Account de Google)
  2. Hoja de cálculo ya creada y compartida con el correo del Service Account.
  3. ID del spreadsheet guardado en la tabla config (clave 'sheets_id').

Hojas esperadas dentro del Spreadsheet:
  - "Ventas"        → registro de cada venta
  - "Detalle"       → desglose de artículos por venta
  - "Gastos"        → salidas de dinero
  - "Cortes"        → cortes de caja diarios
  - "Productos"     → catálogo / stock (lectura para stock_minimo)
"""

import threading
import time
import traceback
from pathlib import Path

CREDENTIALS_PATH = Path(__file__).resolve().parent.parent / "assets" / "credentials.json"
SYNC_INTERVAL = 60  # segundos entre cada intento de sync


class SyncWorker:
    """Hilo daemon que sube datos pendientes a Google Sheets."""

    def __init__(self):
        self._running = False
        self._thread = None
        self._sheets_id = ""

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[SYNC] Worker iniciado.")

    def stop(self):
        self._running = False
        print("[SYNC] Worker detenido.")

    def _get_client(self):
        """Conecta a Google Sheets usando gspread."""
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=scopes)
        client = gspread.authorize(creds)
        return client

    def _get_sheets_id(self):
        from modules.database import get_connection
        conn = get_connection()
        row = conn.execute("SELECT valor FROM config WHERE clave = 'sheets_id'").fetchone()
        conn.close()
        return row["valor"] if row and row["valor"] else ""

    def _loop(self):
        while self._running:
            try:
                self._sync_ventas()
                self._sync_gastos()
            except Exception:
                traceback.print_exc()
            time.sleep(SYNC_INTERVAL)

    def _sync_ventas(self):
        from modules.database import get_connection, marcar_sincronizado

        sheets_id = self._get_sheets_id()
        if not sheets_id:
            return

        conn = get_connection()
        ventas = conn.execute(
            """SELECT v.id, v.folio, v.metodo_pago, v.total, v.created_at,
                      u.nombre as cajero
               FROM ventas v
               JOIN usuarios u ON u.id = v.usuario_id
               WHERE v.sincronizado = 0"""
        ).fetchall()

        if not ventas:
            conn.close()
            return

        client = self._get_client()
        spreadsheet = client.open_by_key(sheets_id)

        # ── Hoja "Ventas" ──
        try:
            ws_ventas = spreadsheet.worksheet("Ventas")
        except Exception:
            ws_ventas = spreadsheet.add_worksheet("Ventas", rows=1000, cols=10)
            ws_ventas.append_row(["ID", "Folio", "Cajero", "Método Pago", "Total", "Fecha"])

        rows_ventas = []
        venta_ids = []

        for v in ventas:
            v = dict(v)
            rows_ventas.append([
                v["id"], v["folio"], v["cajero"],
                v["metodo_pago"], v["total"], v["created_at"]
            ])
            venta_ids.append(v["id"])

        if rows_ventas:
            ws_ventas.append_rows(rows_ventas, value_input_option="USER_ENTERED")

        # ── Hoja "Detalle" ──
        try:
            ws_det = spreadsheet.worksheet("Detalle")
        except Exception:
            ws_det = spreadsheet.add_worksheet("Detalle", rows=5000, cols=10)
            ws_det.append_row([
                "Venta ID", "Folio", "Tienda", "Producto",
                "Cantidad", "Precio Unit.", "Subtotal", "Precio Abierto"
            ])

        detalles = conn.execute(
            f"""SELECT vd.*, v.folio, t.nombre as tienda
                FROM venta_detalle vd
                JOIN ventas v ON v.id = vd.venta_id
                JOIN tiendas t ON t.id = vd.tienda_id
                WHERE vd.sincronizado = 0
                AND vd.venta_id IN ({','.join('?' * len(venta_ids))})""",
            venta_ids,
        ).fetchall()

        rows_det = []
        det_ids = []
        for d in detalles:
            d = dict(d)
            rows_det.append([
                d["venta_id"], d["folio"], d["tienda"],
                d["nombre_producto"], d["cantidad"],
                d["precio_unitario"], d["subtotal"],
                "Sí" if d["es_precio_abierto"] else "No"
            ])
            det_ids.append(d["id"])

        if rows_det:
            ws_det.append_rows(rows_det, value_input_option="USER_ENTERED")

        conn.close()

        # Marcar como sincronizados
        for vid in venta_ids:
            marcar_sincronizado("ventas", vid)
        for did in det_ids:
            marcar_sincronizado("venta_detalle", did)

        print(f"[SYNC] {len(venta_ids)} ventas sincronizadas.")

    def _sync_gastos(self):
        from modules.database import get_connection, marcar_sincronizado

        sheets_id = self._get_sheets_id()
        if not sheets_id:
            return

        conn = get_connection()
        gastos = conn.execute(
            """SELECT g.id, g.concepto, g.monto, g.categoria, g.created_at,
                      u.nombre as cajero
               FROM gastos g
               JOIN usuarios u ON u.id = g.usuario_id
               WHERE g.sincronizado = 0"""
        ).fetchall()
        conn.close()

        if not gastos:
            return

        client = self._get_client()
        spreadsheet = client.open_by_key(sheets_id)

        try:
            ws = spreadsheet.worksheet("Gastos")
        except Exception:
            ws = spreadsheet.add_worksheet("Gastos", rows=1000, cols=8)
            ws.append_row(["ID", "Concepto", "Monto", "Categoría", "Cajero", "Fecha"])

        rows = []
        ids = []
        for g in gastos:
            g = dict(g)
            rows.append([
                g["id"], g["concepto"], g["monto"],
                g["categoria"], g["cajero"], g["created_at"]
            ])
            ids.append(g["id"])

        if rows:
            ws.append_rows(rows, value_input_option="USER_ENTERED")

        for gid in ids:
            marcar_sincronizado("gastos", gid)

        print(f"[SYNC] {len(ids)} gastos sincronizados.")


# Instancia global del worker
sync_worker = SyncWorker()
