"""
modules/database.py — Estudio Deco POS v2
"""
import sqlite3, hashlib
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "pos_estudio_deco.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    # Migrations para bases de datos existentes
    migrations = [
        "ALTER TABLE cortes_caja ADD COLUMN fondo_caja REAL NOT NULL DEFAULT 0.0",
        "ALTER TABLE cortes_caja ADD COLUMN desglose_billetes TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE venta_detalle ADD COLUMN sincronizado INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE gastos ADD COLUMN origen TEXT DEFAULT 'Caja'",
        """CREATE TABLE IF NOT EXISTS ingresos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id   INTEGER NOT NULL,
            concepto     TEXT NOT NULL DEFAULT 'Ingreso',
            monto        REAL NOT NULL,
            metodo_pago  TEXT NOT NULL DEFAULT 'Efectivo',
            sincronizado INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )""",
        "INSERT OR IGNORE INTO config (clave, valor) VALUES ('fondo_turno', '{\"monto\":0,\"fecha\":\"\"}')",
        "UPDATE tiendas SET nombre='Mack&M' WHERE nombre='Mack'",
        "ALTER TABLE productos ADD COLUMN es_precio_abierto INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE productos ADD COLUMN es_bundle INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE productos ADD COLUMN categoria_producto TEXT NOT NULL DEFAULT ''",
        """CREATE TABLE IF NOT EXISTS bundle_components (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_producto_id    INTEGER NOT NULL,
            componente_producto_id INTEGER NOT NULL,
            cantidad              INTEGER NOT NULL DEFAULT 1,
            precio_asignado       REAL    NOT NULL DEFAULT 0.0,
            FOREIGN KEY (bundle_producto_id)     REFERENCES productos(id),
            FOREIGN KEY (componente_producto_id) REFERENCES productos(id)
        )""",
        "INSERT OR IGNORE INTO tiendas (nombre, categoria, precio_abierto, es_barra) VALUES ('Promociones', 'Deco', 0, 0)",
        "UPDATE productos SET categoria_producto='productos' WHERE categoria_producto='individuales'",
        # Eliminar tienda "Mack" duplicada (renombrada a Mack&M pero pudo quedar duplicado)
        "UPDATE venta_detalle SET tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack&M' LIMIT 1) WHERE tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack' LIMIT 1)",
        "UPDATE orden_items SET tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack&M' LIMIT 1) WHERE tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack' LIMIT 1)",
        "UPDATE productos SET tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack&M' LIMIT 1) WHERE tienda_id=(SELECT id FROM tiendas WHERE nombre='Mack' LIMIT 1)",
        "DELETE FROM tiendas WHERE nombre='Mack'",
        # Registro de ventas canceladas
        "ALTER TABLE ventas ADD COLUMN cancelada INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ventas ADD COLUMN cancelada_at TEXT DEFAULT NULL",
        # Tabla para pagos a tiendas
        """CREATE TABLE IF NOT EXISTS pagos_tienda (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tienda_id     INTEGER NOT NULL,
            tienda_nombre TEXT NOT NULL,
            monto         REAL NOT NULL,
            metodo_pago   TEXT NOT NULL DEFAULT 'Efectivo',
            concepto      TEXT NOT NULL DEFAULT '',
            es_interno    INTEGER NOT NULL DEFAULT 0,
            semana_inicio TEXT NOT NULL,
            semana_fin    TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (tienda_id) REFERENCES tiendas(id)
        )""",
    ]
    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass
    conn.close()

# ── USUARIOS ──
def hash_nip(nip): return hashlib.sha256(nip.encode()).hexdigest()

def validar_nip(nip):
    h = hash_nip(nip)
    conn = get_connection()
    row = conn.execute("SELECT id, nombre, perfil FROM usuarios WHERE nip=? AND activo=1", (h,)).fetchone()
    conn.close()
    return dict(row) if row else None

def crear_usuario(nombre, perfil, nip):
    conn = get_connection()
    conn.execute("INSERT INTO usuarios (nombre,perfil,nip) VALUES (?,?,?)", (nombre, perfil, hash_nip(nip)))
    conn.commit(); conn.close()

def listar_usuarios():
    conn = get_connection()
    rows = conn.execute("SELECT id,nombre,perfil,activo FROM usuarios ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── TIENDAS ──
def listar_tiendas():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tiendas ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── PRODUCTOS ──
def obtener_productos(tienda_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM productos WHERE tienda_id=? AND activo=1 ORDER BY nombre", (tienda_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obtener_stock(producto_id):
    conn = get_connection()
    row = conn.execute("SELECT stock_local FROM productos WHERE id=?", (producto_id,)).fetchone()
    conn.close()
    return row["stock_local"] if row else 0

def obtener_todos_los_productos():
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, t.nombre as tienda_nombre 
        FROM productos p 
        JOIN tiendas t ON p.tienda_id = t.id 
        WHERE p.activo=1 
        ORDER BY t.nombre, p.nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def crear_producto(tienda_id, nombre, precio, costo, stock_local, stock_minimo, codigo="", es_precio_abierto=0, es_bundle=0, categoria_producto=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO productos (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto)
    )
    conn.commit()
    prod_id = cur.lastrowid
    conn.close()
    return prod_id

def actualizar_producto(id, tienda_id, nombre, precio, costo, stock_local, stock_minimo, codigo="", es_precio_abierto=0, es_bundle=0, categoria_producto=""):
    conn = get_connection()
    conn.execute(
        "UPDATE productos SET tienda_id=?, codigo=?, nombre=?, precio=?, costo=?, stock_local=?, stock_minimo=?, es_precio_abierto=?, es_bundle=?, categoria_producto=?, updated_at=datetime('now','localtime') WHERE id=?",
        (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto, id)
    )
    conn.commit()
    conn.close()

def eliminar_producto(id):
    conn = get_connection()
    conn.execute("UPDATE productos SET activo=0, updated_at=datetime('now','localtime') WHERE id=?", (id,))
    conn.commit()
    conn.close()

# ── MESAS ──
def listar_mesas():
    conn = get_connection()
    rows = conn.execute("""
        SELECT m.*, o.id as orden_id,
        (SELECT COALESCE(SUM(oi.cantidad * oi.precio_unitario),0)
         FROM orden_items oi WHERE oi.orden_id = o.id) as total_orden,
        (SELECT COUNT(*) FROM orden_items oi WHERE oi.orden_id = o.id) as num_items
        FROM mesas m
        LEFT JOIN ordenes o ON o.mesa_id = m.id AND o.estado = 'abierta'
        ORDER BY m.numero
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def abrir_mesa(mesa_id, usuario_id, nombre_cliente=""):
    conn = get_connection()
    conn.execute("UPDATE mesas SET estado='ocupada' WHERE id=?", (mesa_id,))
    conn.execute("INSERT INTO ordenes (mesa_id, usuario_id, nombre_cliente) VALUES (?,?,?)", (mesa_id, usuario_id, nombre_cliente))
    orden_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return orden_id

def renombrar_orden(orden_id, nombre):
    conn = get_connection()
    conn.execute("UPDATE ordenes SET nombre_cliente=? WHERE id=?", (nombre, orden_id))
    conn.commit()
    conn.close()

def obtener_ordenes_mesa(mesa_id):
    conn = get_connection()
    ordenes = conn.execute("SELECT * FROM ordenes WHERE mesa_id=? AND estado='abierta' ORDER BY id ASC", (mesa_id,)).fetchall()
    
    # Enrich with items and totals just like we did for the single order
    res = []
    for o in ordenes:
        # Need to fetch items for each order
        items = conn.execute("""
            SELECT oi.*, t.nombre as tienda_nombre, t.es_barra
            FROM orden_items oi
            JOIN tiendas t ON t.id = oi.tienda_id
            WHERE oi.orden_id=? ORDER BY oi.created_at
        """, (o["id"],)).fetchall()
        
        total = sum((i["cantidad"] * i["precio_unitario"]) for i in items)
        
        # We simulate the old `obtener_orden_mesa` single-ordendict, but return a list
        o_dict = dict(o)
        o_dict["items"] = [dict(i) for i in items]
        o_dict["total"] = total
        res.append(o_dict)
        
    conn.close()
    return res

def agregar_item_orden(orden_id, producto_id, tienda_id, nombre_producto, cantidad, precio_unitario, es_precio_abierto=False):
    conn = get_connection()

            
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO orden_items (orden_id, producto_id, tienda_id, nombre_producto, cantidad, precio_unitario, es_precio_abierto) VALUES (?,?,?,?,?,?,?)",
        (orden_id, producto_id, tienda_id, nombre_producto, cantidad, precio_unitario, 1 if es_precio_abierto else 0)
    )
    conn.commit()
    item_id = cur.lastrowid
    conn.close()
    return item_id

def actualizar_item_orden(item_id, nombre_producto, precio_unitario):
    conn = get_connection()
    conn.execute(
        "UPDATE orden_items SET nombre_producto=?, precio_unitario=? WHERE id=?",
        (nombre_producto, precio_unitario, item_id)
    )
    conn.commit()
    conn.close()

def quitar_item_orden(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM orden_items WHERE id=?", (item_id,))
    conn.commit(); conn.close()

def obtener_items_comanda(orden_id):
    """Get items from barra (tienda 1) that haven't been printed as comanda yet.
    Also expands bundle products that contain components from tienda 1."""
    conn = get_connection()

    # 1. Regular barra items (tienda_id=1)
    regular = conn.execute("""
        SELECT oi.id, oi.nombre_producto, oi.cantidad, oi.producto_id
        FROM orden_items oi
        WHERE oi.orden_id=? AND oi.comanda_impresa=0 AND oi.tienda_id=1
    """, (orden_id,)).fetchall()
    regular = [dict(i) for i in regular]

    # 2. Bundle items that have at least one component from tienda 1
    bundles = conn.execute("""
        SELECT DISTINCT oi.id, oi.nombre_producto, oi.cantidad, oi.producto_id
        FROM orden_items oi
        JOIN bundle_components bc ON bc.bundle_producto_id = oi.producto_id
        JOIN productos p ON p.id = bc.componente_producto_id
        WHERE oi.orden_id=? AND oi.comanda_impresa=0 AND p.tienda_id=1
    """, (orden_id,)).fetchall()
    bundles = [dict(b) for b in bundles]

    # Expand bundles into their tienda-1 components for the comanda
    comanda_items = list(regular)
    for b in bundles:
        comps = conn.execute("""
            SELECT p.nombre, bc.cantidad AS cant_comp
            FROM bundle_components bc
            JOIN productos p ON p.id = bc.componente_producto_id
            WHERE bc.bundle_producto_id=? AND p.tienda_id=1
        """, (b["producto_id"],)).fetchall()
        for c in comps:
            comanda_items.append({
                "nombre_producto": c["nombre"],
                "cantidad": c["cant_comp"] * b["cantidad"],
            })

    # Mark all processed orden_items as printed
    all_ids = [i["id"] for i in regular] + [b["id"] for b in bundles]
    if all_ids:
        conn.execute(
            f"UPDATE orden_items SET comanda_impresa=1 WHERE id IN ({','.join('?'*len(all_ids))})",
            all_ids
        )
        conn.commit()
    conn.close()
    return comanda_items

def cerrar_mesa(orden_id, usuario_id, metodo_pago="Efectivo", monto_efectivo=0.0, monto_tarjeta=0.0, efectivo_recibido=0.0):
    conn = get_connection()
    # 1. Recuperar info de la orden específica
    orden = conn.execute("SELECT * FROM ordenes WHERE id=?", (orden_id,)).fetchone()
    if not orden or orden["estado"] != "abierta":
        conn.close()
        return None
        
    mesa_id = orden["mesa_id"]

    # 2. Obtener items
    # Note: This call to obtener_items_comanda is not ideal for closing an order
    # as it only gets items not yet printed as comanda. We need ALL items.
    # Let's fetch all items directly.
    items = conn.execute("SELECT * FROM orden_items WHERE orden_id=?", (orden_id,)).fetchall()
    items = [dict(i) for i in items]

    if not items:
        conn.close()
        return None

    total = sum((i["cantidad"] * i["precio_unitario"]) for i in items)
    
    cur = conn.cursor()
    folio = _generar_folio(conn)
    
    # 3. Guardar en 'ventas'
    if metodo_pago == "Mixto":
        cur.execute("""
            INSERT INTO ventas (folio, mesa_id, usuario_id, metodo_pago, monto_efectivo, monto_tarjeta, subtotal, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (folio, mesa_id, usuario_id, metodo_pago, monto_efectivo, monto_tarjeta, total, total))
    else:
        m_efectivo = total if metodo_pago == "Efectivo" else 0.0
        m_tarjeta = total if metodo_pago in ("Tarjeta", "Transferencia") else 0.0
        cur.execute("""
            INSERT INTO ventas (folio, mesa_id, usuario_id, metodo_pago, monto_efectivo, monto_tarjeta, subtotal, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (folio, mesa_id, usuario_id, metodo_pago, m_efectivo, m_tarjeta, total, total))
        
    venta_id = cur.execute("SELECT last_insert_rowid()").fetchone()[0]

    # ... move items to venta_detalle
    for item in items:
        pid = item["producto_id"]
        # ¿Es bundle? → expandir en componentes
        is_bundle = False
        if pid:
            br = cur.execute("SELECT es_bundle FROM productos WHERE id=?", (pid,)).fetchone()
            is_bundle = br and br["es_bundle"]

        if is_bundle:
            _expandir_bundle(conn, cur, venta_id, pid, item["cantidad"])
        else:
            costo_u = 0.0
            if pid:
                row_prod = cur.execute("SELECT costo FROM productos WHERE id=?", (pid,)).fetchone()
                if row_prod: costo_u = row_prod["costo"]
            cur.execute("""
                INSERT INTO venta_detalle (venta_id, producto_id, tienda_id, nombre_producto, cantidad, precio_unitario, costo_unitario, subtotal, es_precio_abierto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (venta_id, pid, item["tienda_id"], item["nombre_producto"],
                  item["cantidad"], item["precio_unitario"], costo_u,
                  item["cantidad"]*item["precio_unitario"], item["es_precio_abierto"]))
            if not item["es_precio_abierto"] and pid:
                cur.execute("UPDATE productos SET stock_local = stock_local - ? WHERE id=?",
                            (item["cantidad"], pid))

    # 4. Cerrar la orden actual
    cur.execute("UPDATE ordenes SET estado='cerrada' WHERE id=?", (orden_id,))
    
    # 5. ¿Es la última orden abierta en esta mesa?
    abiertas_restantes = cur.execute("SELECT count(*) FROM ordenes WHERE mesa_id=? AND estado='abierta'", (mesa_id,)).fetchone()[0]
    if abiertas_restantes == 0:
        cur.execute("UPDATE mesas SET estado='libre', nombre=CAST(numero AS TEXT) WHERE id=?", (mesa_id,))
        
    # --- CALCULAR COMISIÓN TARJETA (4%) --- solo método Tarjeta
    if metodo_pago == 'Tarjeta':
        comision = round(total * 0.04, 2)
        if comision > 0:
            concepto_comision = f"Comisión Tarjeta 4% {folio}"
            cur.execute("""
                INSERT INTO gastos (usuario_id, categoria, tienda_id, concepto, monto, origen)
                VALUES (?, 'General', NULL, ?, ?, 'Banco')
            """, (usuario_id, concepto_comision, comision))
    # --------------------------------------

    conn.commit()
    conn.close()
    
    conn = get_connection()
    m = conn.execute("SELECT numero FROM mesas WHERE id=?", (mesa_id,)).fetchone()
    conn.close()
    
    lbl_mesa = m["numero"] if m else mesa_id
    nombre_c = orden["nombre_cliente"]
    label_completo = f"Mesa {lbl_mesa}"
    if nombre_c: label_completo += f" - {nombre_c}"

    cambio = max(0.0, efectivo_recibido - total)

    return {
        "folio": folio, "venta_id": venta_id, "total": total,
        "items": items, "metodo_pago": metodo_pago,
        "monto_efectivo": monto_efectivo, "monto_tarjeta": monto_tarjeta,
        "efectivo_recibido": efectivo_recibido, "cambio": cambio,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mesa": label_completo
    }

def cancelar_orden_mesa(orden_id):
    conn = get_connection()
    orden = conn.execute("SELECT mesa_id FROM ordenes WHERE id=?", (orden_id,)).fetchone()
    if not orden:
        conn.close()
        return False
        
    mesa_id = orden["mesa_id"]
    conn.execute("DELETE FROM orden_items WHERE orden_id=?", (orden_id,))
    conn.execute("DELETE FROM ordenes WHERE id=?", (orden_id,))
    
    abiertas_restantes = conn.execute("SELECT count(*) FROM ordenes WHERE mesa_id=? AND estado='abierta'", (mesa_id,)).fetchone()[0]
    if abiertas_restantes == 0:
        conn.execute("UPDATE mesas SET estado='libre', nombre=CAST(numero AS TEXT) WHERE id=?", (mesa_id,))
        
    conn.commit()
    conn.close()
    return True

def _generar_folio(conn):
    hoy = date.today().strftime("%Y%m%d")
    row = conn.execute("SELECT COUNT(*) as c FROM ventas WHERE folio LIKE ?", (f"VTA-{hoy}-%",)).fetchone()
    num = (row["c"] if row else 0) + 1
    return f"VTA-{hoy}-{num:04d}"

# ── GASTOS ──
def registrar_gasto(usuario_id, tienda_id, concepto, monto, origen="Caja"):
    categoria = "General"
    if tienda_id:
        conn = get_connection()
        row = conn.execute("SELECT categoria FROM tiendas WHERE id=?", (tienda_id,)).fetchone()
        conn.close()
        if row: categoria = row["categoria"]
    conn = get_connection()
    conn.execute("INSERT INTO gastos (usuario_id,categoria,tienda_id,concepto,monto,origen) VALUES (?,?,?,?,?,?)",
                 (usuario_id, categoria, tienda_id, concepto, monto, origen))
    conn.commit(); conn.close()

# ── INGRESOS ──
def registrar_ingreso(usuario_id, concepto, monto, metodo_pago="Efectivo"):
    conn = get_connection()
    conn.execute("INSERT INTO ingresos (usuario_id, concepto, monto, metodo_pago) VALUES (?,?,?,?)",
                 (usuario_id, concepto, monto, metodo_pago))
    conn.commit(); conn.close()

# ── FONDO DE APERTURA ──
def set_fondo_apertura(monto):
    import json
    valor = json.dumps({"monto": float(monto), "fecha": date.today().strftime("%Y-%m-%d")})
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('fondo_turno', ?)", (valor,))
    conn.commit(); conn.close()

def get_fondo_apertura():
    import json
    conn = get_connection()
    row = conn.execute("SELECT valor FROM config WHERE clave='fondo_turno'").fetchone()
    conn.close()
    if not row or not row["valor"]:
        return 0.0
    try:
        data = json.loads(row["valor"])
        if data.get("fecha") == date.today().strftime("%Y-%m-%d"):
            return float(data.get("monto", 0))
    except Exception:
        pass
    return 0.0

# ── CORTE ──
def obtener_resumen_dia(fecha=None):
    if not fecha: fecha = date.today().strftime("%Y-%m-%d")
    conn = get_connection()

    # Inicio del turno actual: desde el último corte de hoy, o desde medianoche
    last_corte = conn.execute(
        "SELECT created_at FROM cortes_caja WHERE fecha=? ORDER BY id DESC LIMIT 1",
        (fecha,)
    ).fetchone()
    desde = last_corte["created_at"] if last_corte else f"{fecha} 00:00:00"

    rv = conn.execute(
        "SELECT COALESCE(SUM(total),0) as total_ventas, COALESCE(SUM(monto_efectivo),0) as total_efectivo, COUNT(*) as num_ventas FROM ventas WHERE DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()
    canceladas_dia = conn.execute(
        "SELECT COUNT(*) as n FROM ventas WHERE DATE(created_at)=? AND created_at > ? AND cancelada=1",
        (fecha, desde)
    ).fetchone()
    vt = conn.execute(
        """SELECT COALESCE(t.nombre,'Sin Tienda') as tienda,
                  COALESCE(SUM(vd.subtotal),0) as total,
                  COALESCE(SUM(vd.subtotal * CASE
                      WHEN v.metodo_pago='Tarjeta' THEN 0.04
                      WHEN v.metodo_pago='Mixto' AND v.total>0 THEN (CAST(v.monto_tarjeta AS REAL)/v.total)*0.04
                      ELSE 0 END), 0) as comision
           FROM venta_detalle vd
           JOIN ventas v ON v.id=vd.venta_id
           LEFT JOIN tiendas t ON t.id=vd.tienda_id
           WHERE DATE(v.created_at)=? AND v.created_at>? AND (v.cancelada IS NULL OR v.cancelada=0)
           GROUP BY COALESCE(t.nombre,'Sin Tienda')""",
        (fecha, desde)
    ).fetchall()
    # Sabrodulce: roles vendidos; pago = sum(cantidad * (precio - 15))
    sabro = conn.execute(
        """SELECT COALESCE(SUM(vd.cantidad),0) as roles,
                  COALESCE(SUM(vd.cantidad * vd.costo_unitario), 0) as pago_total
           FROM venta_detalle vd
           JOIN ventas v ON v.id=vd.venta_id
           LEFT JOIN productos p ON p.id=vd.producto_id
           LEFT JOIN tiendas t ON t.id=p.tienda_id
           WHERE LOWER(COALESCE(t.nombre,'')) LIKE '%sabro%'
             AND LOWER(COALESCE(p.categoria_producto,''))='roles'
             AND DATE(v.created_at)=? AND v.created_at>?
             AND (v.cancelada IS NULL OR v.cancelada=0)""",
        (fecha, desde)
    ).fetchone()
    # Todos los gastos (para utilidad)
    rg = conn.execute(
        "SELECT COALESCE(SUM(monto),0) as total_gastos FROM gastos WHERE DATE(created_at)=? AND created_at > ?",
        (fecha, desde)
    ).fetchone()
    gd = conn.execute(
        "SELECT g.concepto, g.monto, g.categoria, g.origen, COALESCE(t.nombre,'General') as tienda FROM gastos g LEFT JOIN tiendas t ON t.id = g.tienda_id WHERE DATE(g.created_at)=? AND g.created_at > ? ORDER BY g.created_at",
        (fecha, desde)
    ).fetchall()
    # Solo gastos que salen de la caja física (excluye comisiones de tarjeta y los que salen del banco)
    gc = conn.execute(
        "SELECT COALESCE(SUM(monto),0) as gastos_caja FROM gastos WHERE DATE(created_at)=? AND created_at > ? AND concepto NOT LIKE 'Comisión Tarjeta%' AND origen='Caja'",
        (fecha, desde)
    ).fetchone()
    inv = conn.execute(
        "SELECT COALESCE(SUM(vd.cantidad * vd.costo_unitario),0) as inversion FROM venta_detalle vd JOIN ventas v ON v.id=vd.venta_id WHERE DATE(v.created_at)=? AND v.created_at > ? AND (v.cancelada IS NULL OR v.cancelada=0)",
        (fecha, desde)
    ).fetchone()
    efectivo_row = conn.execute(
        "SELECT COALESCE(SUM(monto_efectivo), 0) as monto FROM ventas WHERE DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()
    tarjeta_row = conn.execute(
        "SELECT COALESCE(SUM(monto_tarjeta), 0) as monto FROM ventas WHERE DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()
    transferencia_row = conn.execute(
        "SELECT COALESCE(SUM(total), 0) as monto FROM ventas WHERE metodo_pago='Transferencia' AND DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()

    # Ingresos del día (pagos recibidos fuera de ventas)
    ing_row = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN metodo_pago='Efectivo' THEN monto ELSE 0 END),0) as ef,"
        " COALESCE(SUM(CASE WHEN metodo_pago='Tarjeta' THEN monto ELSE 0 END),0) as tar,"
        " COALESCE(SUM(monto),0) as total"
        " FROM ingresos WHERE DATE(created_at)=? AND created_at > ?",
        (fecha, desde)
    ).fetchone()
    ing_det = conn.execute(
        "SELECT concepto, monto, metodo_pago FROM ingresos WHERE DATE(created_at)=? AND created_at > ? ORDER BY created_at",
        (fecha, desde)
    ).fetchall()

    metodos = []
    if efectivo_row["monto"] > 0: metodos.append({"metodo_pago": "Efectivo", "monto": efectivo_row["monto"]})
    if tarjeta_row["monto"] > 0: metodos.append({"metodo_pago": "Tarjeta", "monto": tarjeta_row["monto"]})
    if transferencia_row["monto"] > 0: metodos.append({"metodo_pago": "Transferencia", "monto": transferencia_row["monto"]})

    # Totales con ingresos incluidos
    total_ef  = efectivo_row["monto"] + (ing_row["ef"] if ing_row else 0)
    total_tar = tarjeta_row["monto"] + (ing_row["tar"] if ing_row else 0)
    # Gastos de Caja se restan de efectivo, gastos de Banco se restan de tarjeta
    gastos_caja  = gc["gastos_caja"] if gc else 0
    gastos_banco = rg["total_gastos"] - gastos_caja
    efectivo_esperado = total_ef - gastos_caja
    tarjeta_esperado  = total_tar - gastos_banco
    total_esperado    = efectivo_esperado + tarjeta_esperado

    sabro_roles = int(sabro["roles"]) if sabro else 0
    sabro_pago  = round(sabro["pago_total"], 2) if sabro else 0.0

    ventas_por_tienda = []
    for row in vt:
        r = dict(row)
        r["neto"] = round(r["total"] - r["comision"], 2)
        r["comision"] = round(r["comision"], 2)
        ventas_por_tienda.append(r)

    conn.close()
    return {
        "fecha": fecha, "desde": desde,
        "total_ventas": rv["total_ventas"], "num_ventas": rv["num_ventas"],
        "ventas_por_tienda": ventas_por_tienda,
        "total_gastos": rg["total_gastos"],
        "gastos_detalle": [dict(r) for r in gd],
        "total_ingresos": ing_row["total"] if ing_row else 0,
        "ingresos_detalle": [dict(r) for r in ing_det],
        "total_efectivo": total_ef,
        "total_tarjeta": total_tar,
        "efectivo_esperado": efectivo_esperado,
        "tarjeta_esperado": tarjeta_esperado,
        "total_esperado": total_esperado,
        "inversion": inv["inversion"],
        "utilidad": rv["total_ventas"] - inv["inversion"] - rg["total_gastos"],
        "metodos_pago": metodos,
        "fondo_apertura": get_fondo_apertura(),
        "sabrodulce_roles": sabro_roles,
        "sabrodulce_pago": sabro_pago,
        "num_canceladas": canceladas_dia["n"] if canceladas_dia else 0,
    }

def obtener_resumen_semana(fecha_inicio=None, fecha_fin=None):
    from datetime import timedelta
    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=hoy.weekday())).strftime("%Y-%m-%d")
    if not fecha_fin:
        fecha_fin = (hoy - timedelta(days=hoy.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")

    conn = get_connection()

    # ── Saldo acumulado de semanas anteriores ──
    prev_ventas = conn.execute("""
        SELECT COALESCE(SUM(total),0) as total
        FROM ventas WHERE DATE(created_at) < ? AND (cancelada IS NULL OR cancelada=0)
    """, (fecha_inicio,)).fetchone()
    prev_ingresos = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total
        FROM ingresos WHERE DATE(created_at) < ?
    """, (fecha_inicio,)).fetchone()
    prev_gastos = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total
        FROM gastos WHERE DATE(created_at) < ?
    """, (fecha_inicio,)).fetchone()
    saldo_anterior = (prev_ventas['total'] + prev_ingresos['total']) - prev_gastos['total']

    rv = conn.execute("""
        SELECT COALESCE(SUM(total),0) as total_ventas,
               COALESCE(SUM(monto_efectivo),0) as total_efectivo,
               COALESCE(SUM(monto_tarjeta),0) as total_tarjeta,
               COALESCE(SUM(CASE WHEN metodo_pago='Transferencia' THEN total ELSE 0 END),0) as total_transferencia,
               COUNT(*) as num_ventas
        FROM ventas
        WHERE DATE(created_at) BETWEEN ? AND ? AND (cancelada IS NULL OR cancelada=0)
    """, (fecha_inicio, fecha_fin)).fetchone()

    canceladas_row = conn.execute(
        "SELECT COUNT(*) as n FROM ventas WHERE DATE(created_at) BETWEEN ? AND ? AND cancelada=1",
        (fecha_inicio, fecha_fin)
    ).fetchone()

    vt = conn.execute("""
        SELECT COALESCE(t.nombre,'Sin Tienda') as tienda,
               COALESCE(SUM(vd.subtotal),0) as total,
               COALESCE(SUM(vd.subtotal * CASE
                   WHEN v.metodo_pago='Tarjeta' THEN 0.04
                   WHEN v.metodo_pago='Mixto' AND v.total>0 THEN (CAST(v.monto_tarjeta AS REAL)/v.total)*0.04
                   ELSE 0 END), 0) as comision
        FROM venta_detalle vd
        JOIN ventas v ON v.id=vd.venta_id
        LEFT JOIN tiendas t ON t.id=vd.tienda_id
        WHERE DATE(v.created_at) BETWEEN ? AND ? AND (v.cancelada IS NULL OR v.cancelada=0)
        GROUP BY COALESCE(t.nombre,'Sin Tienda')
        ORDER BY total DESC
    """, (fecha_inicio, fecha_fin)).fetchall()

    diario_rows = conn.execute("""
        SELECT DATE(created_at) as fecha,
               COALESCE(SUM(total),0) as total,
               COALESCE(SUM(monto_efectivo),0) as efectivo,
               COALESCE(SUM(monto_tarjeta),0) as tarjeta,
               COUNT(*) as ventas
        FROM ventas
        WHERE DATE(created_at) BETWEEN ? AND ? AND (cancelada IS NULL OR cancelada=0)
        GROUP BY DATE(created_at)
        ORDER BY fecha
    """, (fecha_inicio, fecha_fin)).fetchall()

    # Por-tienda por día (para vista semanal existente)
    dt_rows = conn.execute("""
        SELECT DATE(v.created_at) as fecha,
               COALESCE(t.nombre,'Sin Tienda') as tienda,
               COALESCE(SUM(vd.subtotal),0) as total
        FROM venta_detalle vd
        JOIN ventas v ON v.id=vd.venta_id
        LEFT JOIN tiendas t ON t.id=vd.tienda_id
        WHERE DATE(v.created_at) BETWEEN ? AND ? AND (v.cancelada IS NULL OR v.cancelada=0)
        GROUP BY DATE(v.created_at), COALESCE(t.nombre,'Sin Tienda')
        ORDER BY fecha, total DESC
    """, (fecha_inicio, fecha_fin)).fetchall()

    gastos_rows = conn.execute("""
        SELECT DATE(created_at) as fecha, COALESCE(SUM(monto),0) as gastos
        FROM gastos WHERE DATE(created_at) BETWEEN ? AND ?
        GROUP BY DATE(created_at)
    """, (fecha_inicio, fecha_fin)).fetchall()

    gastos = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total,
               COALESCE(SUM(CASE WHEN origen='Banco' THEN monto ELSE 0 END),0) as banco
        FROM gastos WHERE DATE(created_at) BETWEEN ? AND ?
    """, (fecha_inicio, fecha_fin)).fetchone()

    sabro = conn.execute("""
        SELECT COALESCE(SUM(vd.cantidad),0) as roles,
               COALESCE(SUM(vd.cantidad * (vd.precio_unitario - 15.0)), 0) as pago_total
        FROM venta_detalle vd
        JOIN ventas v ON v.id=vd.venta_id
        LEFT JOIN productos p ON p.id=vd.producto_id
        LEFT JOIN tiendas t ON t.id=p.tienda_id
        WHERE LOWER(COALESCE(t.nombre,'')) LIKE '%sabro%'
          AND LOWER(COALESCE(p.categoria_producto,''))='roles'
          AND DATE(v.created_at) BETWEEN ? AND ?
          AND (v.cancelada IS NULL OR v.cancelada=0)
    """, (fecha_inicio, fecha_fin)).fetchone()

    # Merge por-tienda and gastos into diario
    tiendas_map = {}
    for row in dt_rows:
        tiendas_map.setdefault(row["fecha"], []).append({"tienda": row["tienda"], "total": row["total"]})
    gastos_map = {row["fecha"]: row["gastos"] for row in gastos_rows}

    # ── Ingresos (pagos recibidos fuera de ventas) ──
    ingresos_total_row = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total,
               COALESCE(SUM(CASE WHEN metodo_pago='Efectivo' THEN monto ELSE 0 END),0) as ef,
               COALESCE(SUM(CASE WHEN metodo_pago='Tarjeta' THEN monto ELSE 0 END),0) as tar
        FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?
    """, (fecha_inicio, fecha_fin)).fetchone()

    ingresos_diario_rows = conn.execute("""
        SELECT DATE(created_at) as fecha, COALESCE(SUM(monto),0) as ingresos
        FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?
        GROUP BY DATE(created_at)
    """, (fecha_inicio, fecha_fin)).fetchall()

    ingresos_det = conn.execute("""
        SELECT concepto, monto, metodo_pago, DATE(created_at) as fecha
        FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?
        ORDER BY created_at
    """, (fecha_inicio, fecha_fin)).fetchall()

    ingresos_map = {row["fecha"]: row["ingresos"] for row in ingresos_diario_rows}

    diario = []
    for row in diario_rows:
        d = dict(row)
        d["total_ventas"] = d["total"]   # alias for legacy loadSemanal
        d["num_ventas"]   = d["ventas"]  # alias
        d["por_tienda"]   = tiendas_map.get(d["fecha"], [])
        d["gastos"]       = gastos_map.get(d["fecha"], 0)
        d["ingresos"]     = ingresos_map.get(d["fecha"], 0)
        diario.append(d)

    ventas_por_tienda = []
    for row in vt:
        r2 = dict(row)
        r2['neto'] = round(r2['total'] - r2['comision'], 2)
        r2['comision'] = round(r2['comision'], 2)
        ventas_por_tienda.append(r2)

    sabro_roles = int(sabro['roles']) if sabro else 0
    sabro_pago_semana = round(sabro['pago_total'], 2) if sabro else 0.0
    total_semana = rv['total_ventas']
    total_ingresos = ingresos_total_row['total'] if ingresos_total_row else 0

    # ── Pagos a tiendas de esta semana ──
    pagos_rows = conn.execute("""
        SELECT pt.*, t.nombre as tienda_nombre_actual
        FROM pagos_tienda pt
        LEFT JOIN tiendas t ON t.id = pt.tienda_id
        WHERE pt.semana_inicio = ? AND pt.semana_fin = ?
        ORDER BY pt.created_at
    """, (fecha_inicio, fecha_fin)).fetchall()
    pagos_semana = [dict(r) for r in pagos_rows]

    # ── Balances por tienda ──
    # 304 = sus ventas propias + transferencias internas recibidas
    # Estudio Deco = acumulado total - balance 304
    estacion_ventas = sum(
        t_row['total'] for t_row in vt if 'estaci' in t_row['tienda'].lower()
    )
    total_pagos_internos = sum(p['monto'] for p in pagos_semana if p.get('es_interno'))
    acumulado_semana = total_semana + total_ingresos - gastos['total']
    balance_estacion = estacion_ventas + total_pagos_internos
    balance_estudio = acumulado_semana - balance_estacion

    conn.close()
    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'saldo_anterior': saldo_anterior,
        # Legacy fields for loadSemanal view
        'total_semana': total_semana,
        'total_efectivo': rv['total_efectivo'] + (ingresos_total_row['ef'] if ingresos_total_row else 0),
        'total_tarjeta': rv['total_tarjeta'] + (ingresos_total_row['tar'] if ingresos_total_row else 0),
        'total_gastos': gastos['total'],
        'total_ingresos': total_ingresos,
        'ingresos_detalle': [dict(r) for r in ingresos_det],
        'utilidad': total_semana + total_ingresos - gastos['total'],
        'dias': diario,
        # New fields for Corte Semanal modal
        'total_ventas': total_semana,
        'total_transferencia': rv['total_transferencia'],
        'num_ventas': rv['num_ventas'],
        'num_canceladas': canceladas_row['n'] if canceladas_row else 0,
        'total_gastos_banco': gastos['banco'],
        'ventas_por_tienda': ventas_por_tienda,
        'diario': diario,
        'sabrodulce_roles': sabro_roles,
        'sabrodulce_pago': sabro_pago_semana,
        # Balances y pagos
        'balance_estudio_deco': balance_estudio,
        'balance_estacion_304': balance_estacion,
        'pagos_semana': pagos_semana,
    }

def registrar_corte(usuario_id, efectivo_real, fondo_caja=0.0, desglose=None):
    import json
    resumen = obtener_resumen_dia()
    dif = efectivo_real - resumen["efectivo_esperado"]
    desglose_str = json.dumps(desglose or {})
    conn = get_connection()
    conn.execute(
        "INSERT INTO cortes_caja (usuario_id,fecha,total_ventas,total_gastos,efectivo_esperado,efectivo_real,diferencia,fondo_caja,desglose_billetes) VALUES (?,?,?,?,?,?,?,?,?)",
        (usuario_id, resumen["fecha"], resumen["total_ventas"], resumen["total_gastos"],
         resumen["efectivo_esperado"], efectivo_real, dif, fondo_caja, desglose_str),
    )
    conn.commit(); conn.close()
    resumen["efectivo_real"] = efectivo_real
    resumen["diferencia"] = dif
    resumen["fondo_caja"] = fondo_caja
    resumen["desglose_billetes"] = desglose or {}
    return resumen

def generar_folio():
    conn = get_connection()
    f = _generar_folio(conn)
    conn.close()
    return f

def registrar_venta(usuario_id, metodo_pago, items, monto_efectivo=0.0, monto_tarjeta=0.0, efectivo_recibido=0.0):
    conn = get_connection()
    folio = _generar_folio(conn)
    total = sum(i["precio_unitario"] * i["cantidad"] for i in items)

    if metodo_pago == "Efectivo":
        monto_efectivo = total
        monto_tarjeta = 0.0
    elif metodo_pago in ("Tarjeta", "Transferencia", "Transfer"):
        monto_efectivo = 0.0
        monto_tarjeta = total

    cur = conn.cursor()
    cur.execute("INSERT INTO ventas (folio,usuario_id,metodo_pago,monto_efectivo,monto_tarjeta,subtotal,total) VALUES (?,?,?,?,?,?,?)",
                (folio, usuario_id, metodo_pago, monto_efectivo, monto_tarjeta, total, total))
    venta_id = cur.lastrowid
    for item in items:
        pid = item.get("producto_id")
        is_bundle = False
        if pid:
            br = cur.execute("SELECT es_bundle FROM productos WHERE id=?", (pid,)).fetchone()
            is_bundle = br and br["es_bundle"]

        if is_bundle:
            _expandir_bundle(conn, cur, venta_id, pid, item["cantidad"])
        else:
            sub = item["precio_unitario"] * item["cantidad"]
            costo = 0.0
            if pid:
                cr = cur.execute("SELECT costo FROM productos WHERE id=?", (pid,)).fetchone()
                if cr: costo = cr["costo"] or 0.0
            cur.execute("INSERT INTO venta_detalle (venta_id,producto_id,tienda_id,nombre_producto,cantidad,precio_unitario,costo_unitario,subtotal,es_precio_abierto) VALUES (?,?,?,?,?,?,?,?,?)",
                        (venta_id, pid, item["tienda_id"], item["nombre"], item["cantidad"], item["precio_unitario"], costo, sub, 1 if item.get("es_precio_abierto") else 0))
            if pid and not item.get("es_precio_abierto"):
                cur.execute("UPDATE productos SET stock_local=stock_local-?, sincronizado=0 WHERE id=?", (item["cantidad"], pid))
            
    # --- CALCULAR COMISIÓN TARJETA (4%) --- solo Tarjeta/Mixto, NO Transferencia
    if monto_tarjeta > 0 and metodo_pago == 'Tarjeta':
        comision = round(monto_tarjeta * 0.04, 2)
        if comision > 0:
            concepto_comision = f"Comisión Tarjeta 4% {folio}"
            cur.execute("""
                INSERT INTO gastos (usuario_id, categoria, tienda_id, concepto, monto, origen)
                VALUES (?, 'General', NULL, ?, ?, 'Banco')
            """, (usuario_id, concepto_comision, comision))
    # --------------------------------------
            
    conn.commit(); conn.close()
    cambio = max(0.0, efectivo_recibido - total)
    return {"folio": folio, "venta_id": venta_id, "total": total, "items": items, "metodo_pago": metodo_pago, "monto_efectivo": monto_efectivo, "monto_tarjeta": monto_tarjeta, "efectivo_recibido": efectivo_recibido, "cambio": cambio, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def obtener_ventas_dia(fecha=None):
    if not fecha: fecha = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    ventas = conn.execute("""
        SELECT v.*, u.nombre as cajero_nombre,
               COALESCE(v.cancelada, 0) as cancelada,
               v.cancelada_at
        FROM ventas v
        JOIN usuarios u ON u.id = v.usuario_id
        WHERE DATE(v.created_at) = ?
        ORDER BY v.cancelada ASC, v.created_at DESC
    """, (fecha,)).fetchall()
    result = []
    for v in ventas:
        v_dict = dict(v)
        items = conn.execute("""
            SELECT vd.*, COALESCE(t.nombre,'Sin Tienda') as tienda_nombre
            FROM venta_detalle vd
            LEFT JOIN tiendas t ON t.id = vd.tienda_id
            WHERE vd.venta_id = ?
        """, (v["id"],)).fetchall()
        v_dict["items"] = [dict(i) for i in items]
        result.append(v_dict)
    conn.close()
    return result

def obtener_ventas_turno(fecha=None):
    """Obtiene las ventas del turno actual (desde el último corte)."""
    if not fecha: fecha = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    last_corte = conn.execute(
        "SELECT created_at FROM cortes_caja WHERE fecha=? ORDER BY id DESC LIMIT 1",
        (fecha,)
    ).fetchone()
    desde = last_corte["created_at"] if last_corte else f"{fecha} 00:00:00"
    ventas = conn.execute("""
        SELECT v.*, u.nombre as cajero_nombre,
               COALESCE(v.cancelada, 0) as cancelada,
               m.numero as mesa_numero
        FROM ventas v
        JOIN usuarios u ON u.id = v.usuario_id
        LEFT JOIN mesas m ON m.id = v.mesa_id
        WHERE DATE(v.created_at) = ? AND v.created_at > ?
          AND (v.cancelada IS NULL OR v.cancelada=0)
        ORDER BY v.created_at ASC
    """, (fecha, desde)).fetchall()
    result = []
    for v in ventas:
        v_dict = dict(v)
        items = conn.execute("""
            SELECT vd.*, COALESCE(t.nombre,'Sin Tienda') as tienda_nombre
            FROM venta_detalle vd
            LEFT JOIN tiendas t ON t.id = vd.tienda_id
            WHERE vd.venta_id = ?
        """, (v["id"],)).fetchall()
        v_dict["items"] = [dict(i) for i in items]
        result.append(v_dict)
    conn.close()
    return result

def get_email_config():
    """Lee la configuración de email desde la tabla config."""
    conn = get_connection()
    email_from = conn.execute("SELECT valor FROM config WHERE clave='email_from'").fetchone()
    email_pass = conn.execute("SELECT valor FROM config WHERE clave='email_password'").fetchone()
    email_dest = conn.execute("SELECT valor FROM config WHERE clave='email_destino'").fetchone()
    conn.close()
    return {
        "email_from": email_from["valor"] if email_from else "",
        "email_password": email_pass["valor"] if email_pass else "",
        "email_destino": email_dest["valor"] if email_dest else "estudiodecomx@gmail.com",
    }

def set_email_config(email_from, password, destino="estudiodecomx@gmail.com"):
    """Guarda la configuración de email en la tabla config."""
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('email_from', ?)", (email_from,))
    conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('email_password', ?)", (password,))
    conn.execute("INSERT OR REPLACE INTO config (clave, valor) VALUES ('email_destino', ?)", (destino,))
    conn.commit(); conn.close()

def corregir_venta(venta_id, metodo_pago, monto_efectivo, monto_tarjeta):
    conn = get_connection()
    conn.execute(
        "UPDATE ventas SET metodo_pago=?, monto_efectivo=?, monto_tarjeta=?, sincronizado=0 WHERE id=?",
        (metodo_pago, monto_efectivo, monto_tarjeta, venta_id)
    )
    conn.commit(); conn.close()

def anular_venta(venta_id):
    conn = get_connection()
    venta = conn.execute("SELECT folio FROM ventas WHERE id=?", (venta_id,)).fetchone()
    if not venta:
        conn.close(); return
    items = conn.execute("SELECT * FROM venta_detalle WHERE venta_id=?", (venta_id,)).fetchall()
    for item in items:
        if item["producto_id"] and not item["es_precio_abierto"]:
            conn.execute("UPDATE productos SET stock_local = stock_local + ? WHERE id=?",
                         (item["cantidad"], item["producto_id"]))
    conn.execute("DELETE FROM gastos WHERE concepto LIKE ?", (f"Comisión Tarjeta 4% {venta['folio']}",))
    # Marcar como cancelada (no eliminar, para historial)
    conn.execute(
        "UPDATE ventas SET cancelada=1, cancelada_at=datetime('now','localtime'), sincronizado=0 WHERE id=?",
        (venta_id,)
    )
    conn.commit(); conn.close()

def obtener_bundle_components(bundle_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT bc.id, bc.cantidad, bc.precio_asignado,
               p.id as producto_id, p.nombre, p.precio, p.tienda_id,
               t.nombre as tienda_nombre
        FROM bundle_components bc
        JOIN productos p ON p.id = bc.componente_producto_id
        JOIN tiendas  t ON t.id = p.tienda_id
        WHERE bc.bundle_producto_id = ?
        ORDER BY bc.id
    """, (bundle_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def agregar_bundle_component(bundle_id, componente_id, cantidad, precio_asignado):
    conn = get_connection()
    conn.execute(
        "INSERT INTO bundle_components (bundle_producto_id, componente_producto_id, cantidad, precio_asignado) VALUES (?,?,?,?)",
        (bundle_id, componente_id, cantidad, precio_asignado)
    )
    conn.commit(); conn.close()

def eliminar_bundle_component(comp_id):
    conn = get_connection()
    conn.execute("DELETE FROM bundle_components WHERE id=?", (comp_id,))
    conn.commit(); conn.close()

def _expandir_bundle(conn, cur, venta_id, producto_id, cantidad_bundle):
    """Inserta venta_detalle para cada componente del bundle y resta su stock."""
    comps = conn.execute("""
        SELECT bc.componente_producto_id, bc.cantidad, bc.precio_asignado,
               p.nombre, p.tienda_id, p.costo
        FROM bundle_components bc
        JOIN productos p ON p.id = bc.componente_producto_id
        WHERE bc.bundle_producto_id = ?
    """, (producto_id,)).fetchall()
    for c in comps:
        qty = c["cantidad"] * cantidad_bundle
        sub = qty * c["precio_asignado"]
        cur.execute("""
            INSERT INTO venta_detalle
              (venta_id, producto_id, tienda_id, nombre_producto, cantidad, precio_unitario, costo_unitario, subtotal, es_precio_abierto)
            VALUES (?,?,?,?,?,?,?,?,0)
        """, (venta_id, c["componente_producto_id"], c["tienda_id"],
               c["nombre"], qty, c["precio_asignado"], c["costo"], sub))
        cur.execute("UPDATE productos SET stock_local=stock_local-?, sincronizado=0 WHERE id=?",
                    (qty, c["componente_producto_id"]))

def marcar_sincronizado(tabla, record_id):
    conn = get_connection()
    conn.execute(f"UPDATE {tabla} SET sincronizado=1 WHERE id=?", (record_id,))
    conn.commit(); conn.close()

# ── PAGOS A TIENDAS ──
def registrar_pago_tienda(tienda_id, tienda_nombre, monto, metodo_pago, concepto, es_interno, semana_inicio, semana_fin):
    """Registra un pago a una tienda. Si es_interno=True (Estación 304), solo es contable.
    Si es_interno=False, también registra un gasto real."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO pagos_tienda (tienda_id, tienda_nombre, monto, metodo_pago, concepto, es_interno, semana_inicio, semana_fin)
        VALUES (?,?,?,?,?,?,?,?)
    """, (tienda_id, tienda_nombre, monto, metodo_pago, concepto, 1 if es_interno else 0, semana_inicio, semana_fin))
    conn.commit()
    conn.close()

def obtener_pagos_semana(semana_inicio, semana_fin):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM pagos_tienda
        WHERE semana_inicio = ? AND semana_fin = ?
        ORDER BY created_at
    """, (semana_inicio, semana_fin)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
