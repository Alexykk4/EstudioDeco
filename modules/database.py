import logging
logging.basicConfig(filename="errores.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
"""
modules/database.py — Estudio Deco POS v2
"""
import sqlite3, hashlib
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "pos_estudio_deco.db"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _write_audit_log(conn, tabla, registro_id, accion, usuario_id=None, datos_anteriores=None, datos_nuevos=None):
    """Escribe una entrada en audit_log dentro de la conexión activa (sin commit)."""
    import json
    conn.execute(
        "INSERT INTO audit_log (tabla, registro_id, accion, usuario_id, datos_anteriores, datos_nuevos) VALUES (?,?,?,?,?,?)",
        (tabla, registro_id, accion, usuario_id,
         json.dumps(datos_anteriores, ensure_ascii=False) if datos_anteriores is not None else None,
         json.dumps(datos_nuevos,     ensure_ascii=False) if datos_nuevos     is not None else None)
    )

def _asegurar_columna(conn, tabla, columna, definicion):
    cursor = conn.execute(f"PRAGMA table_info({tabla})")
    columnas_existentes = [row["name"] for row in cursor.fetchall()]
    if columna not in columnas_existentes:
        logging.info(f"Migración: Columna {columna} agregada a {tabla}.")

def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    # Migrations para bases de datos existentes
    migrations = [
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
        """CREATE TABLE IF NOT EXISTS nominas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empleado TEXT NOT NULL,
            concepto        TEXT NOT NULL DEFAULT 'Nómina',
            monto           REAL NOT NULL,
            metodo_pago     TEXT NOT NULL DEFAULT 'Efectivo',
            usuario_id      INTEGER,
            created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )""",
        """CREATE TABLE IF NOT EXISTS estacion_movimientos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT    NOT NULL DEFAULT 'ingreso',
            concepto    TEXT    NOT NULL,
            monto       REAL    NOT NULL,
            metodo_pago TEXT    NOT NULL DEFAULT 'Efectivo',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )""",
        # ── Inventario Estación 304 ──
        """CREATE TABLE IF NOT EXISTS inv_ingredientes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre       TEXT    NOT NULL UNIQUE,
            unidad       TEXT    NOT NULL DEFAULT 'g',
            stock_actual REAL    NOT NULL DEFAULT 0,
            stock_minimo REAL    NOT NULL DEFAULT 0,
            updated_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )""",
        """CREATE TABLE IF NOT EXISTS inv_consumo_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_bebida TEXT    NOT NULL,
            concepto      TEXT    NOT NULL DEFAULT 'venta',
            created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )""",
        # Receta asignada a un producto (para descuento automático de inventario)
        # Historial de compras de insumos
        """CREATE TABLE IF NOT EXISTS inv_entradas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente_id INTEGER NOT NULL,
            cantidad       REAL    NOT NULL,
            costo_total    REAL    NOT NULL,
            costo_unitario REAL    NOT NULL DEFAULT 0,
            nota           TEXT    NOT NULL DEFAULT '',
            created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (ingrediente_id) REFERENCES inv_ingredientes(id)
        )""",
        # Costo unitario promedio en la tabla maestra
        # Recetas dinámicas
        """CREATE TABLE IF NOT EXISTS inv_recetas (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT    NOT NULL UNIQUE,
            activo     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )""",
        """CREATE TABLE IF NOT EXISTS inv_receta_ingredientes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            receta_id      INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            cantidad       REAL    NOT NULL,
            UNIQUE(receta_id, ingrediente_id),
            FOREIGN KEY (receta_id)      REFERENCES inv_recetas(id),
            FOREIGN KEY (ingrediente_id) REFERENCES inv_ingredientes(id)
        )""",
        # ── Soft-delete para gastos (S-6 / auditoria) ──
        # ── Soft-delete para ingresos (S-6 / auditoria) ──
        # ── Tabla de auditoría (D-16) ──
        """CREATE TABLE IF NOT EXISTS audit_log (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tabla            TEXT    NOT NULL,
            registro_id      INTEGER NOT NULL,
            accion           TEXT    NOT NULL,
            usuario_id       INTEGER,
            datos_anteriores TEXT,
            datos_nuevos     TEXT,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )""",
    ]

    # Migraciones seguras (ALTER TABLE ADD COLUMN)
    _asegurar_columna(conn, "cortes_caja", "fondo_caja", "REAL NOT NULL DEFAULT 0.0")
    _asegurar_columna(conn, "cortes_caja", "desglose_billetes", "TEXT NOT NULL DEFAULT '{}'")
    _asegurar_columna(conn, "venta_detalle", "sincronizado", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "gastos", "origen", "TEXT DEFAULT 'Caja'")
    _asegurar_columna(conn, "productos", "es_precio_abierto", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "productos", "es_bundle", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "productos", "categoria_producto", "TEXT NOT NULL DEFAULT ''")
    _asegurar_columna(conn, "ventas", "cancelada", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "ventas", "cancelada_at", "TEXT DEFAULT NULL")
    _asegurar_columna(conn, "productos", "receta_key", "TEXT NOT NULL DEFAULT ''")
    _asegurar_columna(conn, "inv_ingredientes", "costo_unitario", "REAL NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "gastos", "anulado", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "gastos", "anulado_at", "TEXT DEFAULT NULL")
    _asegurar_columna(conn, "gastos", "anulado_por", "TEXT DEFAULT NULL")
    _asegurar_columna(conn, "ingresos", "anulado", "INTEGER NOT NULL DEFAULT 0")
    _asegurar_columna(conn, "ingresos", "anulado_at", "TEXT DEFAULT NULL")
    _asegurar_columna(conn, "ingresos", "anulado_por", "TEXT DEFAULT NULL")

    for sql in migrations:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception as e:
            logging.error(f"Silenced error: {e}")
    # 1. Inyectar nueva tienda 'Ehretia'
    tienda_ehretia = conn.execute("SELECT id FROM tiendas WHERE nombre='Ehretia'").fetchone()
    if not tienda_ehretia:
        conn.execute("INSERT INTO tiendas (nombre, categoria, precio_abierto, es_barra) VALUES ('Ehretia', 'Deco', 0, 0)")
        conn.commit()
        logging.info("Migración: Tienda 'Ehretia' inyectada exitosamente.")

    # 2. Eliminar duplicado inactivo 'Estación 304' con ID 237
    tienda_237 = conn.execute("SELECT id FROM tiendas WHERE id=237 AND nombre='Estación 304'").fetchone()
    if tienda_237:
        # Chequeo de seguridad: No debe tener ventas ni productos asignados
        ventas_237 = conn.execute("SELECT COUNT(*) as c FROM venta_detalle WHERE tienda_id=237").fetchone()["c"]
        prods_237 = conn.execute("SELECT COUNT(*) as c FROM productos WHERE tienda_id=237").fetchone()["c"]
        if ventas_237 == 0 and prods_237 == 0:
            # Reasignar gastos y pagos_tienda de la tienda 237 a la tienda activa 1
            conn.execute("UPDATE gastos SET tienda_id=1 WHERE tienda_id=237")
            conn.execute("UPDATE pagos_tienda SET tienda_id=1 WHERE tienda_id=237")
            conn.execute("DELETE FROM tiendas WHERE id=237")
            conn.commit()
            logging.info("Migración: Tienda 'Estación 304' (ID 237) combinada con ID 1 y eliminada.")
        else:
            logging.warning("Migración: Tienda 'Estación 304' (ID 237) NO eliminada porque tiene ventas o productos.")

    conn.close()
    # Sembrar ingredientes de las recetas (solo si la tabla está vacía)
    _seed_ingredientes()
    _seed_recetas()

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

def crear_producto(tienda_id, nombre, precio, costo, stock_local, stock_minimo, codigo="", es_precio_abierto=0, es_bundle=0, categoria_producto="", receta_key=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO productos (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto, receta_key) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto, receta_key)
    )
    conn.commit()
    prod_id = cur.lastrowid
    conn.close()
    return prod_id

def actualizar_producto(id, tienda_id, nombre, precio, costo, stock_local, stock_minimo, codigo="", es_precio_abierto=0, es_bundle=0, categoria_producto="", receta_key=""):
    conn = get_connection()
    conn.execute(
        "UPDATE productos SET tienda_id=?, codigo=?, nombre=?, precio=?, costo=?, stock_local=?, stock_minimo=?, es_precio_abierto=?, es_bundle=?, categoria_producto=?, receta_key=?, updated_at=datetime('now','localtime') WHERE id=?",
        (tienda_id, codigo, nombre, precio, costo, stock_local, stock_minimo, es_precio_abierto, es_bundle, categoria_producto, receta_key, id)
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

    items = conn.execute("SELECT * FROM orden_items WHERE orden_id=?", (orden_id,)).fetchall()
    items = [dict(i) for i in items]

    if not items:
        conn.close()
        return None

    total = sum((i["cantidad"] * i["precio_unitario"]) for i in items)
    folio = None
    venta_id = None

    try:  # F-1: bloque atómico con rollback en caso de fallo
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

        # 4. Mover items a venta_detalle y descontar stock
        for item in items:
            pid = item["producto_id"]
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
                # F-3: proteger stock contra negativos
                if not item["es_precio_abierto"] and pid:
                    rows_updated = cur.execute(
                        "UPDATE productos SET stock_local = stock_local - ? WHERE id=? AND stock_local >= ?",
                        (item["cantidad"], pid, item["cantidad"])
                    ).rowcount
                    if rows_updated == 0:
                        raise ValueError(f"Stock insuficiente para producto id={pid}")

        # 5. Cerrar la orden actual
        cur.execute("UPDATE ordenes SET estado='cerrada' WHERE id=?", (orden_id,))

        # 6. ¿Es la última orden abierta en esta mesa?
        abiertas_restantes = cur.execute("SELECT count(*) FROM ordenes WHERE mesa_id=? AND estado='abierta'", (mesa_id,)).fetchone()[0]
        if abiertas_restantes == 0:
            cur.execute("UPDATE mesas SET estado='libre', nombre=CAST(numero AS TEXT) WHERE id=?", (mesa_id,))

        # 7. Comisión tarjeta (4%)
        if metodo_pago == 'Tarjeta':
            comision = round(total * 0.04, 2)
        elif metodo_pago == 'Mixto' and monto_tarjeta > 0:
            comision = round(monto_tarjeta * 0.04, 2)
        else:
            comision = 0.0
        if comision > 0:
            concepto_comision = f"Comisión Tarjeta 4% {folio}"
            cur.execute("""
                INSERT INTO gastos (usuario_id, categoria, tienda_id, concepto, monto, origen)
                VALUES (?, 'General', NULL, ?, ?, 'Banco')
            """, (usuario_id, concepto_comision, comision))

        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        conn.close()
        raise

    conn.close()

    conn2 = get_connection()
    m = conn2.execute("SELECT numero FROM mesas WHERE id=?", (mesa_id,)).fetchone()
    conn2.close()

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
    """Genera un folio único y atómico usando una secuencia en la tabla config (F-5)."""
    hoy = date.today().strftime("%Y%m%d")
    key = f"folio_seq_{hoy}"
    # Asegura que la fila existe; si no, arranca en 0
    conn.execute("INSERT OR IGNORE INTO config (clave, valor) VALUES (?, '0')", (key,))
    # Incremento atómico dentro de la misma transacción
    conn.execute(
        "UPDATE config SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT) WHERE clave = ?",
        (key,)
    )
    row = conn.execute("SELECT valor FROM config WHERE clave=?", (key,)).fetchone()
    num = int(row["valor"])
    return f"VTA-{hoy}-{num:04d}"

# ── GASTOS ──
def registrar_gasto(usuario_id, tienda_id, concepto, monto, origen="Caja"):
    categoria = "General"
    tienda_nombre = None
    if tienda_id:
        conn = get_connection()
        row = conn.execute("SELECT categoria, nombre FROM tiendas WHERE id=?", (tienda_id,)).fetchone()
        conn.close()
        if row:
            categoria = row["categoria"]
            tienda_nombre = row["nombre"]
    conn = get_connection()
    conn.execute("INSERT INTO gastos (usuario_id,categoria,tienda_id,concepto,monto,origen) VALUES (?,?,?,?,?,?)",
                 (usuario_id, categoria, tienda_id, concepto, monto, origen))
    conn.commit(); conn.close()
    # Si el gasto es de Estación 304, también reflejarlo en su balance
    if tienda_nombre and 'Estaci' in tienda_nombre:
        metodo = 'Transferencia' if origen == 'Banco' else 'Efectivo'
        registrar_movimiento_estacion('gasto', concepto, monto, metodo)

def listar_gastos(limit=50, offset=0):
    """Retorna gastos activos con paginación real (S-9). Excluye registros anulados (S-6)."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) as n FROM gastos WHERE anulado IS NULL OR anulado=0"
    ).fetchone()["n"]
    rows = conn.execute("""
        SELECT g.id, g.concepto, g.monto, g.origen, g.categoria, g.created_at,
               COALESCE(u.nombre,'?') as usuario, COALESCE(t.nombre,'General') as tienda
        FROM gastos g
        LEFT JOIN usuarios u ON u.id = g.usuario_id
        LEFT JOIN tiendas  t ON t.id = g.tienda_id
        WHERE g.anulado IS NULL OR g.anulado=0
        ORDER BY g.created_at DESC LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return {"total": total, "items": [dict(r) for r in rows]}

def anular_gasto(gasto_id, anulado_por=None):
    """Soft-delete: marca el gasto como anulado y escribe en audit_log (S-6)."""
    conn = get_connection()
    prev = conn.execute("SELECT * FROM gastos WHERE id=?", (gasto_id,)).fetchone()
    if prev:
        conn.execute(
            "UPDATE gastos SET anulado=1, anulado_at=datetime('now','localtime'), anulado_por=? WHERE id=?",
            (anulado_por, gasto_id)
        )
        _write_audit_log(conn, "gastos", gasto_id, "anulacion", datos_anteriores=dict(prev))
    conn.commit(); conn.close()

# ── INGRESOS ──
def listar_ingresos(limit=50, offset=0):
    """Retorna ingresos activos con paginación real (S-9). Excluye registros anulados (S-6)."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) as n FROM ingresos WHERE anulado IS NULL OR anulado=0"
    ).fetchone()["n"]
    rows = conn.execute("""
        SELECT i.id, i.concepto, i.monto, i.metodo_pago, i.created_at,
               COALESCE(u.nombre,'?') as usuario
        FROM ingresos i
        LEFT JOIN usuarios u ON u.id = i.usuario_id
        WHERE i.anulado IS NULL OR i.anulado=0
        ORDER BY i.created_at DESC LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return {"total": total, "items": [dict(r) for r in rows]}

def anular_ingreso(ingreso_id, anulado_por=None):
    """Soft-delete: marca el ingreso como anulado y escribe en audit_log (S-6)."""
    conn = get_connection()
    prev = conn.execute("SELECT * FROM ingresos WHERE id=?", (ingreso_id,)).fetchone()
    if prev:
        conn.execute(
            "UPDATE ingresos SET anulado=1, anulado_at=datetime('now','localtime'), anulado_por=? WHERE id=?",
            (anulado_por, ingreso_id)
        )
        _write_audit_log(conn, "ingresos", ingreso_id, "anulacion", datos_anteriores=dict(prev))
    conn.commit(); conn.close()

def registrar_ingreso(usuario_id, concepto, monto, metodo_pago="Efectivo"):
    conn = get_connection()
    conn.execute("INSERT INTO ingresos (usuario_id, concepto, monto, metodo_pago) VALUES (?,?,?,?)",
                 (usuario_id, concepto, monto, metodo_pago))
    conn.commit(); conn.close()

# ── BALANCE ACUMULADO HISTÓRICO ──
def obtener_balance_actual():
    """Devuelve el balance real acumulado desde el inicio: ventas + ingresos - gastos - pagos."""
    conn = get_connection()
    fecha = __import__('datetime').date.today().strftime("%Y-%m-%d")
    last_corte = conn.execute("SELECT created_at FROM cortes_caja WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
    desde = last_corte["created_at"] if last_corte else f"{fecha} 00:00:00"
    

    ventas_row = conn.execute("""
        SELECT
            COALESCE(SUM(total), 0) as total,
            COALESCE(SUM(monto_efectivo), 0) as efectivo,
            COALESCE(SUM(monto_tarjeta), 0) as tarjeta
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0) AND created_at > ?
    """, (desde,)).fetchone()

    ingresos_row = conn.execute("""
        SELECT
            COALESCE(SUM(monto), 0) as total,
            COALESCE(SUM(CASE WHEN metodo_pago='Efectivo' THEN monto ELSE 0 END), 0) as efectivo,
            COALESCE(SUM(CASE WHEN metodo_pago!='Efectivo' THEN monto ELSE 0 END), 0) as banco
        FROM ingresos WHERE (anulado IS NULL OR anulado=0) AND created_at > ?
    """, (desde,)).fetchone()

    gastos_row = conn.execute("""
        SELECT
            COALESCE(SUM(monto), 0) as total,
            COALESCE(SUM(CASE WHEN origen='Caja' THEN monto ELSE 0 END), 0) as caja,
            COALESCE(SUM(CASE WHEN origen='Banco' THEN monto ELSE 0 END), 0) as banco
        FROM gastos WHERE (anulado IS NULL OR anulado=0) AND created_at > ?
    """, (desde,)).fetchone()

    # Pagos a tiendas: solo los externos afectan al balance "real" del negocio.
    # Importante: deben descontarse también de caja/banco según el método de pago,
    # o el total no cuadrará con (en_caja + en_banco).
    pagos_row = conn.execute("""
        SELECT
          COALESCE(SUM(monto), 0) as total,
          COALESCE(SUM(CASE WHEN (es_interno=0 OR es_interno IS NULL) THEN monto ELSE 0 END), 0) as externos,
          COALESCE(SUM(CASE WHEN (es_interno=0 OR es_interno IS NULL) AND metodo_pago='Efectivo' THEN monto ELSE 0 END), 0) as externos_efectivo,
          COALESCE(SUM(CASE WHEN (es_interno=0 OR es_interno IS NULL) AND metodo_pago!='Efectivo' THEN monto ELSE 0 END), 0) as externos_banco
        FROM pagos_tienda WHERE created_at > ?
    """, (desde,)).fetchone()

    ajuste_caja_row  = conn.execute("SELECT valor FROM config WHERE clave='ajuste_caja'").fetchone()
    ajuste_banco_row = conn.execute("SELECT valor FROM config WHERE clave='ajuste_banco'").fetchone()
    conn.close()

    total_ventas   = ventas_row['total']
    total_ingresos = ingresos_row['total']
    total_gastos   = gastos_row['total']
    total_pagos    = pagos_row['externos']
    pagos_efectivo = pagos_row['externos_efectivo']
    pagos_banco    = pagos_row['externos_banco']

    ajuste_caja  = float(ajuste_caja_row['valor'])  if ajuste_caja_row  else 0.0
    ajuste_banco = float(ajuste_banco_row['valor']) if ajuste_banco_row else 0.0

    efectivo = (
        ventas_row['efectivo']
        + ingresos_row['efectivo']
        - gastos_row['caja']
        + ajuste_caja
    )
    banco = (
        ventas_row['tarjeta']
        + ingresos_row['banco']
        - gastos_row['banco']
        + ajuste_banco
    )
    neto = total_ventas + total_ingresos - total_gastos + ajuste_caja + ajuste_banco

    return {
        'total':          round(neto, 2),
        'en_caja':        round(efectivo, 2),
        'en_banco':       round(banco, 2),
        'total_ventas':   round(total_ventas, 2),
        'total_ingresos': round(total_ingresos, 2),
        'total_gastos':   round(total_gastos, 2),
        'total_pagos':    round(total_pagos, 2),
        'ajuste_caja':    round(ajuste_caja, 2),
        'ajuste_banco':   round(ajuste_banco, 2),
    }

def ajustar_balance(caja_real: float, banco_real: float):
    """Guarda ajustes para que el balance calculado coincida con los valores reales."""
    conn = get_connection()
    fecha = __import__('datetime').date.today().strftime("%Y-%m-%d")
    last_corte = conn.execute("SELECT created_at FROM cortes_caja WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
    desde = last_corte["created_at"] if last_corte else f"{fecha} 00:00:00"
    
    # Calcular balance actual sin ajustes para determinar la diferencia
    ventas_row = conn.execute("""
        SELECT COALESCE(SUM(monto_efectivo),0) as ef, COALESCE(SUM(monto_tarjeta),0) as tar
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0) AND created_at > ?
    """, (desde,)).fetchone()
    ingresos_row = conn.execute("""
        SELECT COALESCE(SUM(CASE WHEN metodo_pago='Efectivo' THEN monto ELSE 0 END),0) as ef,
               COALESCE(SUM(CASE WHEN metodo_pago!='Efectivo' THEN monto ELSE 0 END),0) as banco
        FROM ingresos WHERE created_at > ?
    """, (desde,)).fetchone()
    gastos_row = conn.execute("""
        SELECT COALESCE(SUM(CASE WHEN origen='Caja' THEN monto ELSE 0 END),0) as caja,
               COALESCE(SUM(CASE WHEN origen='Banco' THEN monto ELSE 0 END),0) as banco
        FROM gastos WHERE created_at > ?
    """, (desde,)).fetchone()
    calculado_caja  = ventas_row['ef']  + ingresos_row['ef']     - gastos_row['caja']
    calculado_banco = ventas_row['tar'] + ingresos_row['banco']  - gastos_row['banco']
    ajuste_caja  = round(caja_real  - calculado_caja,  2)
    ajuste_banco = round(banco_real - calculado_banco, 2)
    conn.execute("INSERT OR REPLACE INTO config (clave,valor) VALUES ('ajuste_caja',?)",  (str(ajuste_caja),))
    conn.execute("INSERT OR REPLACE INTO config (clave,valor) VALUES ('ajuste_banco',?)", (str(ajuste_banco),))
    conn.commit(); conn.close()
    return {'ajuste_caja': ajuste_caja, 'ajuste_banco': ajuste_banco}

def limpiar_ingresos_gastos(fecha_inicio: str, fecha_fin: str):
    """
    Borra ingresos y gastos del rango dado manteniendo el balance intacto.
    """
    bal = obtener_balance_actual()
    caja_real  = bal['en_caja']
    banco_real = bal['en_banco']

    conn = get_connection()
    borrados_ingresos = conn.execute(
        "DELETE FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?",
        (fecha_inicio, fecha_fin)
    ).rowcount
    borrados_gastos = conn.execute(
        "DELETE FROM gastos WHERE DATE(created_at) BETWEEN ? AND ? AND concepto NOT LIKE 'Comisión Tarjeta 4%%'",
        (fecha_inicio, fecha_fin)
    ).rowcount
    conn.commit(); conn.close()

    ajustar_balance(caja_real, banco_real)

    return {
        'borrados_ingresos': borrados_ingresos,
        'borrados_gastos': borrados_gastos,
        'balance_preservado': {'en_caja': caja_real, 'en_banco': banco_real}
    }

# ── NÓMINAS ──
def registrar_nomina(nombre_empleado: str, monto: float, concepto: str, metodo_pago: str, usuario_id: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO nominas (nombre_empleado, monto, concepto, metodo_pago, usuario_id) VALUES (?,?,?,?,?)",
        (nombre_empleado, monto, concepto, metodo_pago, usuario_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM nominas WHERE id=last_insert_rowid()").fetchone()
    conn.close()
    return dict(row)

def listar_nominas(limit: int = 50, offset: int = 0):
    """Retorna nóminas con paginación real (S-9)."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as n FROM nominas").fetchone()["n"]
    rows = conn.execute("""
        SELECT n.*, u.nombre as cajero
        FROM nominas n
        LEFT JOIN usuarios u ON u.id = n.usuario_id
        ORDER BY n.created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    conn.close()
    return {"total": total, "items": [dict(r) for r in rows]}

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
    except Exception as e:
        logging.error(f"Silenced error: {e}")
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
    # Sabrodulce: pago = sum(cantidad * costo), filtrando por tienda_id de la venta
    sabro = conn.execute(
        """SELECT COALESCE(SUM(vd.cantidad),0) as roles,
                  COALESCE(SUM(vd.cantidad * COALESCE(NULLIF(vd.costo_unitario,0), p.costo, 0)), 0) as pago_total
           FROM venta_detalle vd
           JOIN ventas v ON v.id=vd.venta_id
           LEFT JOIN productos p ON p.id=vd.producto_id
           LEFT JOIN tiendas t ON t.id=vd.tienda_id
           WHERE LOWER(COALESCE(t.nombre,'')) LIKE '%sabro%'
             AND DATE(v.created_at)=? AND v.created_at>?
             AND (v.cancelada IS NULL OR v.cancelada=0)""",
        (fecha, desde)
    ).fetchone()
    # Todos los gastos activos (para utilidad) — excluye anulados (S-6)
    rg = conn.execute(
        "SELECT COALESCE(SUM(monto),0) as total_gastos FROM gastos WHERE DATE(created_at)=? AND created_at > ? AND (anulado IS NULL OR anulado=0)",
        (fecha, desde)
    ).fetchone()
    gd = conn.execute(
        "SELECT g.concepto, g.monto, g.categoria, g.origen, COALESCE(t.nombre,'General') as tienda FROM gastos g LEFT JOIN tiendas t ON t.id = g.tienda_id WHERE DATE(g.created_at)=? AND g.created_at > ? AND (g.anulado IS NULL OR g.anulado=0) ORDER BY g.created_at",
        (fecha, desde)
    ).fetchall()
    # Solo gastos que salen de la caja física (excluye comisiones de tarjeta y los que salen del banco)
    gc = conn.execute(
        "SELECT COALESCE(SUM(monto),0) as gastos_caja FROM gastos WHERE DATE(created_at)=? AND created_at > ? AND concepto NOT LIKE 'Comisi%n Tarjeta%' AND origen='Caja' AND (anulado IS NULL OR anulado=0)",
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
    # Solo Tarjeta y Mixto tienen comisión; Transferencia es independiente
    tarjeta_row = conn.execute(
        "SELECT COALESCE(SUM(monto_tarjeta), 0) as monto FROM ventas WHERE metodo_pago IN ('Tarjeta','Mixto') AND DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()
    transferencia_row = conn.execute(
        "SELECT COALESCE(SUM(total), 0) as monto FROM ventas WHERE metodo_pago='Transferencia' AND DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0)",
        (fecha, desde)
    ).fetchone()
    conteo_metodos = conn.execute(
        "SELECT metodo_pago, COUNT(*) as n, COALESCE(SUM(total),0) as monto FROM ventas WHERE DATE(created_at)=? AND created_at > ? AND (cancelada IS NULL OR cancelada=0) GROUP BY metodo_pago",
        (fecha, desde)
    ).fetchall()

    # Ingresos del día activos (excluye anulados, S-6)
    ing_row = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN metodo_pago='Efectivo' THEN monto ELSE 0 END),0) as ef,"
        " COALESCE(SUM(CASE WHEN metodo_pago='Tarjeta' THEN monto ELSE 0 END),0) as tar,"
        " COALESCE(SUM(monto),0) as total"
        " FROM ingresos WHERE DATE(created_at)=? AND created_at > ? AND (anulado IS NULL OR anulado=0)",
        (fecha, desde)
    ).fetchone()
    ing_det = conn.execute(
        "SELECT concepto, monto, metodo_pago FROM ingresos WHERE DATE(created_at)=? AND created_at > ? AND (anulado IS NULL OR anulado=0) ORDER BY created_at",
        (fecha, desde)
    ).fetchall()

    metodos = []
    if efectivo_row["monto"] > 0: metodos.append({"metodo_pago": "Efectivo", "monto": efectivo_row["monto"]})
    if tarjeta_row["monto"] > 0: metodos.append({"metodo_pago": "Tarjeta", "monto": tarjeta_row["monto"]})
    if transferencia_row["monto"] > 0: metodos.append({"metodo_pago": "Transferencia", "monto": transferencia_row["monto"]})

    # Totales con ingresos incluidos
    total_ef           = efectivo_row["monto"] + (ing_row["ef"] if ing_row else 0)
    total_tar          = tarjeta_row["monto"] + (ing_row["tar"] if ing_row else 0)
    total_transfer     = transferencia_row["monto"]
    # Gastos de Caja se restan de efectivo, gastos de Banco (comisiones) se restan de tarjeta
    gastos_caja        = gc["gastos_caja"] if gc else 0
    gastos_banco       = rg["total_gastos"] - gastos_caja
    efectivo_esperado  = total_ef - gastos_caja
    tarjeta_esperado   = total_tar - gastos_banco
    total_esperado     = efectivo_esperado + tarjeta_esperado + total_transfer

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
        "total_transferencia": total_transfer,
        "efectivo_esperado": efectivo_esperado,
        "tarjeta_esperado": tarjeta_esperado,
        "total_esperado": total_esperado,
        "inversion": inv["inversion"],
        "utilidad": rv["total_ventas"] - inv["inversion"] - rg["total_gastos"],
        "metodos_pago": metodos,
        "conteo_metodos": [dict(r) for r in conteo_metodos],
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
        FROM ingresos WHERE DATE(created_at) < ? AND (anulado IS NULL OR anulado=0)
    """, (fecha_inicio,)).fetchone()
    prev_gastos = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total
        FROM gastos WHERE DATE(created_at) < ? AND (anulado IS NULL OR anulado=0)
    """, (fecha_inicio,)).fetchone()
    prev_pagos_ext = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total
        FROM pagos_tienda WHERE DATE(created_at) < ? AND (es_interno=0 OR es_interno IS NULL)
    """, (fecha_inicio,)).fetchone()
    saldo_anterior = (prev_ventas['total'] + prev_ingresos['total']) - prev_gastos['total'] - prev_pagos_ext['total']

    rv = conn.execute("""
        SELECT COALESCE(SUM(total),0) as total_ventas,
               COALESCE(SUM(monto_efectivo),0) as total_efectivo,
               -- Bug #4: separar tarjeta pura de transferencias (no doble-conteo)
               COALESCE(SUM(CASE WHEN metodo_pago IN ('Tarjeta','Mixto') THEN monto_tarjeta ELSE 0 END),0) as total_tarjeta,
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
          AND (anulado IS NULL OR anulado=0)
        GROUP BY DATE(created_at)
    """, (fecha_inicio, fecha_fin)).fetchall()

    gastos = conn.execute("""
        SELECT COALESCE(SUM(monto),0) as total,
               COALESCE(SUM(CASE WHEN origen='Banco' THEN monto ELSE 0 END),0) as banco
        FROM gastos WHERE DATE(created_at) BETWEEN ? AND ?
          AND (anulado IS NULL OR anulado=0)
    """, (fecha_inicio, fecha_fin)).fetchone()

    sabro = conn.execute("""
        SELECT COALESCE(SUM(vd.cantidad),0) as roles,
               COALESCE(SUM(vd.cantidad * COALESCE(NULLIF(vd.costo_unitario,0), p.costo, 0)), 0) as pago_total
        FROM venta_detalle vd
        JOIN ventas v ON v.id=vd.venta_id
        LEFT JOIN productos p ON p.id=vd.producto_id
        LEFT JOIN tiendas t ON t.id=vd.tienda_id
        WHERE LOWER(COALESCE(t.nombre,'')) LIKE '%sabro%'
          AND DATE(v.created_at) BETWEEN ? AND ?
          AND (v.cancelada IS NULL OR v.cancelada=0)
    """, (fecha_inicio, fecha_fin)).fetchone()

    # Detalle de productos vendidos por tienda
    detalle_rows = conn.execute("""
        SELECT COALESCE(t.nombre,'Sin Tienda') as tienda,
               vd.nombre_producto as producto,
               COALESCE(SUM(vd.cantidad),0) as cantidad,
               COALESCE(SUM(vd.subtotal),0) as total,
               COALESCE(SUM(vd.cantidad * COALESCE(NULLIF(vd.costo_unitario,0), p.costo, 0)), 0) as costo_total
        FROM venta_detalle vd
        JOIN ventas v ON v.id=vd.venta_id
        LEFT JOIN productos p ON p.id=vd.producto_id
        LEFT JOIN tiendas t ON t.id=vd.tienda_id
        WHERE DATE(v.created_at) BETWEEN ? AND ? AND (v.cancelada IS NULL OR v.cancelada=0)
        GROUP BY COALESCE(t.nombre,'Sin Tienda'), vd.nombre_producto
        ORDER BY tienda, total DESC
    """, (fecha_inicio, fecha_fin)).fetchall()

    detalle_por_tienda = {}
    for row in detalle_rows:
        tienda = row['tienda']
        if tienda not in detalle_por_tienda:
            detalle_por_tienda[tienda] = []
        detalle_por_tienda[tienda].append({
            'producto': row['producto'],
            'cantidad': int(row['cantidad']),
            'total': round(row['total'], 2),
            'costo_total': round(row['costo_total'], 2)
        })

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
          AND (anulado IS NULL OR anulado=0)
    """, (fecha_inicio, fecha_fin)).fetchone()

    ingresos_diario_rows = conn.execute("""
        SELECT DATE(created_at) as fecha, COALESCE(SUM(monto),0) as ingresos
        FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?
          AND (anulado IS NULL OR anulado=0)
        GROUP BY DATE(created_at)
    """, (fecha_inicio, fecha_fin)).fetchall()

    ingresos_det = conn.execute("""
        SELECT concepto, monto, metodo_pago, DATE(created_at) as fecha
        FROM ingresos WHERE DATE(created_at) BETWEEN ? AND ?
          AND (anulado IS NULL OR anulado=0)
        ORDER BY created_at
    """, (fecha_inicio, fecha_fin)).fetchall()

    ingresos_map = {row["fecha"]: row["ingresos"] for row in ingresos_diario_rows}

    # Bug #2: gastos pagados en efectivo (para restar de total_efectivo, igual que el diario)
    gastos_caja_row = conn.execute("""
        SELECT COALESCE(SUM(monto), 0) as gastos_caja
        FROM gastos
        WHERE DATE(created_at) BETWEEN ? AND ?
          AND concepto NOT LIKE 'Comisi%n Tarjeta%'
          AND origen='Caja'
          AND (anulado IS NULL OR anulado=0)
    """, (fecha_inicio, fecha_fin)).fetchone()
    gastos_caja_semana = gastos_caja_row["gastos_caja"] if gastos_caja_row else 0

    # Bug #3: inversión/costo de mercancía (para restar de utilidad, igual que el diario)
    inv_semana_row = conn.execute("""
        SELECT COALESCE(SUM(vd.cantidad * vd.costo_unitario), 0) as inversion
        FROM venta_detalle vd
        JOIN ventas v ON v.id = vd.venta_id
        WHERE DATE(v.created_at) BETWEEN ? AND ?
          AND (v.cancelada IS NULL OR v.cancelada=0)
    """, (fecha_inicio, fecha_fin)).fetchone()
    inv_semana = inv_semana_row["inversion"] if inv_semana_row else 0

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
    total_pagos_externos = sum(p['monto'] for p in pagos_semana if not p.get('es_interno'))
    acumulado_semana = total_semana + total_ingresos - gastos['total']
    balance_estacion = estacion_ventas + total_pagos_internos
    # Restar pagos a tiendas externas (Sabrodulce, proveedores, etc.) del balance de Estudio Deco
    balance_estudio = acumulado_semana - balance_estacion - total_pagos_externos

    conn.close()
    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'saldo_anterior': saldo_anterior,
        # Legacy fields for loadSemanal view
        'total_semana': total_semana,
        # Bug #2: restar gastos_caja del efectivo (igual que el reporte diario)
        'total_efectivo': rv['total_efectivo'] + (ingresos_total_row['ef'] if ingresos_total_row else 0) - gastos_caja_semana,
        'total_tarjeta': rv['total_tarjeta'] + (ingresos_total_row['tar'] if ingresos_total_row else 0),
        'total_gastos': gastos['total'],
        'total_ingresos': total_ingresos,
        'ingresos_detalle': [dict(r) for r in ingresos_det],
        # Bug #3: incluir inversión/costo de mercancía en la utilidad (igual que el reporte diario)
        'utilidad': total_semana + total_ingresos - gastos['total'] - inv_semana,
        'inversion': round(inv_semana, 2),
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
        'total_pagos_externos': total_pagos_externos,
        'pagos_semana': pagos_semana,
        'detalle_por_tienda': detalle_por_tienda,
    }

def registrar_corte(usuario_id, efectivo_real, fondo_caja=0.0, desglose=None):
    import json
    resumen = obtener_resumen_dia()
    dif = efectivo_real - resumen["efectivo_esperado"]
    desglose_str = json.dumps(desglose or {})
    conn = get_connection()
    fecha = __import__('datetime').date.today().strftime("%Y-%m-%d")
    last_corte = conn.execute("SELECT created_at FROM cortes_caja WHERE fecha=? ORDER BY id DESC LIMIT 1", (fecha,)).fetchone()
    desde = last_corte["created_at"] if last_corte else f"{fecha} 00:00:00"
    
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
    total = sum(i["precio_unitario"] * i["cantidad"] for i in items)

    if metodo_pago == "Efectivo":
        monto_efectivo = total
        monto_tarjeta = 0.0
    elif metodo_pago in ("Tarjeta", "Transferencia", "Transfer"):
        monto_efectivo = 0.0
        monto_tarjeta = total

    try:  # F-1: bloque atómico con rollback en caso de fallo
        folio = _generar_folio(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ventas (folio,usuario_id,metodo_pago,monto_efectivo,monto_tarjeta,subtotal,total) VALUES (?,?,?,?,?,?,?)",
            (folio, usuario_id, metodo_pago, monto_efectivo, monto_tarjeta, total, total)
        )
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
                cur.execute(
                    "INSERT INTO venta_detalle (venta_id,producto_id,tienda_id,nombre_producto,cantidad,precio_unitario,costo_unitario,subtotal,es_precio_abierto) VALUES (?,?,?,?,?,?,?,?,?)",
                    (venta_id, pid, item["tienda_id"], item["nombre"], item["cantidad"], item["precio_unitario"], costo, sub, 1 if item.get("es_precio_abierto") else 0)
                )
                # F-3: proteger stock contra negativos
                if pid and not item.get("es_precio_abierto"):
                    rows_updated = cur.execute(
                        "UPDATE productos SET stock_local=stock_local-?, sincronizado=0 WHERE id=? AND stock_local >= ?",
                        (item["cantidad"], pid, item["cantidad"])
                    ).rowcount
                    if rows_updated == 0:
                        raise ValueError(f"Stock insuficiente para producto id={pid}")

        # Comisión tarjeta (4%)
        if monto_tarjeta > 0 and metodo_pago in ('Tarjeta', 'Mixto'):
            comision = round(monto_tarjeta * 0.04, 2)
            if comision > 0:
                concepto_comision = f"Comisión Tarjeta 4% {folio}"
                cur.execute("""
                    INSERT INTO gastos (usuario_id, categoria, tienda_id, concepto, monto, origen)
                    VALUES (?, 'General', NULL, ?, ?, 'Banco')
                """, (usuario_id, concepto_comision, comision))

        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        conn.close()
        raise

    conn.close()
    cambio = max(0.0, efectivo_recibido - total)
    return {
        "folio": folio, "venta_id": venta_id, "total": total,
        "items": items, "metodo_pago": metodo_pago,
        "monto_efectivo": monto_efectivo, "monto_tarjeta": monto_tarjeta,
        "efectivo_recibido": efectivo_recibido, "cambio": cambio,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def obtener_ventas_dia(fecha=None):
    """Retorna ventas del día con sus items en 2 queries (elimina N+1, F-7)."""
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

    if not ventas:
        conn.close()
        return []

    venta_ids = [v["id"] for v in ventas]
    placeholders = ",".join("?" * len(venta_ids))
    all_items = conn.execute(f"""
        SELECT vd.*, COALESCE(t.nombre,'Sin Tienda') as tienda_nombre
        FROM venta_detalle vd
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE vd.venta_id IN ({placeholders})
    """, venta_ids).fetchall()
    conn.close()

    items_map = {}
    for item in all_items:
        items_map.setdefault(item["venta_id"], []).append(dict(item))

    result = []
    for v in ventas:
        v_dict = dict(v)
        v_dict["items"] = items_map.get(v["id"], [])
        result.append(v_dict)
    return result

def obtener_ventas_turno(fecha=None):
    """Obtiene las ventas del turno actual en 2 queries (elimina N+1, F-7)."""
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

    if not ventas:
        conn.close()
        return []

    venta_ids = [v["id"] for v in ventas]
    placeholders = ",".join("?" * len(venta_ids))
    all_items = conn.execute(f"""
        SELECT vd.*, COALESCE(t.nombre,'Sin Tienda') as tienda_nombre
        FROM venta_detalle vd
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE vd.venta_id IN ({placeholders})
    """, venta_ids).fetchall()
    conn.close()

    items_map = {}
    for item in all_items:
        items_map.setdefault(item["venta_id"], []).append(dict(item))

    result = []
    for v in ventas:
        v_dict = dict(v)
        v_dict["items"] = items_map.get(v["id"], [])
        result.append(v_dict)
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
    """Corrige el método de pago y recalcula la comisión de tarjeta (F-2)."""
    conn = get_connection()
    venta = conn.execute("SELECT folio, metodo_pago, monto_tarjeta, usuario_id FROM ventas WHERE id=?", (venta_id,)).fetchone()
    if not venta:
        conn.close(); return
    try:
        prev_data = dict(venta)
        concepto_com = f"Comisión Tarjeta 4% {venta['folio']}"

        # Anular comisión anterior si existía
        gasto_prev = conn.execute("SELECT id FROM gastos WHERE concepto LIKE ? AND (anulado IS NULL OR anulado=0)", (concepto_com,)).fetchone()
        if gasto_prev:
            conn.execute(
                "UPDATE gastos SET anulado=1, anulado_at=datetime('now','localtime'), anulado_por='correccion_venta' WHERE id=?",
                (gasto_prev["id"],)
            )

        # Actualizar venta
        conn.execute(
            "UPDATE ventas SET metodo_pago=?, monto_efectivo=?, monto_tarjeta=?, sincronizado=0 WHERE id=?",
            (metodo_pago, monto_efectivo, monto_tarjeta, venta_id)
        )

        # Crear nueva comisión si aplica
        if monto_tarjeta > 0 and metodo_pago in ('Tarjeta', 'Mixto'):
            comision = round(monto_tarjeta * 0.04, 2)
            if comision > 0:
                conn.execute(
                    "INSERT INTO gastos (usuario_id, categoria, tienda_id, concepto, monto, origen) VALUES (?, 'General', NULL, ?, ?, 'Banco')",
                    (venta["usuario_id"], concepto_com, comision)
                )

        _write_audit_log(conn, "ventas", venta_id, "correccion",
                         datos_anteriores=prev_data,
                         datos_nuevos={"metodo_pago": metodo_pago, "monto_efectivo": monto_efectivo, "monto_tarjeta": monto_tarjeta})
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        conn.close()
        raise
    conn.close()

def anular_venta(venta_id, anulado_por=None):
    """Cancela la venta, revierte stock y anula (soft-delete) la comisión de tarjeta (S-7)."""
    conn = get_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE id=?", (venta_id,)).fetchone()
    if not venta:
        conn.close(); return
    items = conn.execute("SELECT * FROM venta_detalle WHERE venta_id=?", (venta_id,)).fetchall()
    try:
        for item in items:
            if item["producto_id"] and not item["es_precio_abierto"]:
                conn.execute("UPDATE productos SET stock_local = stock_local + ? WHERE id=?",
                             (item["cantidad"], item["producto_id"]))
        # Soft-delete de la comisión de tarjeta (evita borrar registros ya sincronizados con Sheets)
        comision_concepto = f"Comisión Tarjeta 4% {venta['folio']}"
        gasto_com = conn.execute("SELECT id FROM gastos WHERE concepto LIKE ?", (comision_concepto,)).fetchone()
        if gasto_com:
            conn.execute(
                "UPDATE gastos SET anulado=1, anulado_at=datetime('now','localtime'), anulado_por=? WHERE id=?",
                (anulado_por, gasto_com["id"])
            )
            _write_audit_log(conn, "gastos", gasto_com["id"], "anulacion_por_venta_cancelada",
                             datos_anteriores={"venta_id": venta_id, "folio": venta["folio"]})
        # Marcar venta como cancelada
        conn.execute(
            "UPDATE ventas SET cancelada=1, cancelada_at=datetime('now','localtime'), sincronizado=0 WHERE id=?",
            (venta_id,)
        )
        _write_audit_log(conn, "ventas", venta_id, "anulacion", anulado_por,
                         datos_anteriores=dict(venta))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        conn.close()
        raise
    conn.close()

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
def registrar_movimiento_estacion(tipo, concepto, monto, metodo_pago='Efectivo'):
    conn = get_connection()
    conn.execute(
        "INSERT INTO estacion_movimientos (tipo, concepto, monto, metodo_pago) VALUES (?,?,?,?)",
        (tipo, concepto, monto, metodo_pago)
    )
    conn.commit(); conn.close()

def obtener_balance_estacion():
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE 0 END), 0) as total_ingresos,
            COALESCE(SUM(CASE WHEN tipo='gasto'   THEN monto ELSE 0 END), 0) as total_gastos
        FROM estacion_movimientos
    """).fetchone()
    conn.close()
    ing = row['total_ingresos']; gas = row['total_gastos']
    return {'balance': round(ing - gas, 2), 'total_ingresos': round(ing, 2), 'total_gastos': round(gas, 2)}

def obtener_movimientos_estacion():
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, tipo, concepto, monto, metodo_pago, created_at
        FROM estacion_movimientos ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def registrar_pago_tienda(tienda_id, tienda_nombre, monto, metodo_pago, concepto, es_interno, semana_inicio, semana_fin, usuario_id=None):
    """Registra un pago a una tienda. Si tienda_id=1 (Estación 304), también suma a su balance."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO pagos_tienda (tienda_id, tienda_nombre, monto, metodo_pago, concepto, es_interno, semana_inicio, semana_fin)
        VALUES (?,?,?,?,?,?,?,?)
    """, (tienda_id, tienda_nombre, monto, metodo_pago, concepto, 1 if es_interno else 0, semana_inicio, semana_fin))
    conn.commit()
    conn.close()
    
    # NUEVO: DESCONTAR EL DINERO DE LA CAJA O BANCO
    origen_pago = "Caja" if metodo_pago == "Efectivo" else "Banco"
    uid = usuario_id if usuario_id else 1  # Fallback a Admin si no hay ID
    
    # Reutilizamos la función registrar_gasto para mantener la consistencia contable.
    # Si el pago es a Estación 304 (tienda_id=1), no registramos el gasto con tienda_id=1
    # para evitar que registrar_gasto lo descuente de su propio balance local (como si fuera un gasto interno de la Estación).
    # En su lugar, lo registramos como gasto general y sumamos un ingreso a la Estación.
    if tienda_id == 1 or (tienda_nombre and 'Estaci' in tienda_nombre):
        registrar_gasto(
            usuario_id=uid,
            tienda_id=None,
            concepto=concepto or f"Transferencia interna a {tienda_nombre}",
            monto=monto,
            origen=origen_pago
        )
        registrar_movimiento_estacion('ingreso', concepto or f"Transferencia interna de Estudio Deco", monto, metodo_pago)
    else:
        registrar_gasto(
            usuario_id=uid,
            tienda_id=tienda_id,
            concepto=concepto or f"Pago semanal a {tienda_nombre}",
            monto=monto,
            origen=origen_pago
        )

def obtener_pagos_semana(semana_inicio, semana_fin):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM pagos_tienda
        WHERE semana_inicio = ? AND semana_fin = ?
        ORDER BY created_at
    """, (semana_inicio, semana_fin)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obtener_estadisticas():
    conn = get_connection()

    # Por mes (todos los meses disponibles)
    meses = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as mes,
               COALESCE(SUM(total),0) as ventas,
               COUNT(*) as num_ventas
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0)
        GROUP BY mes ORDER BY mes
    """).fetchall()

    ingresos_mes = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as mes,
               COALESCE(SUM(monto),0) as ingresos
        FROM ingresos GROUP BY mes ORDER BY mes
    """).fetchall()
    ingresos_map = {r['mes']: r['ingresos'] for r in ingresos_mes}

    gastos_mes = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as mes,
               COALESCE(SUM(monto),0) as gastos
        FROM gastos GROUP BY mes ORDER BY mes
    """).fetchall()
    gastos_map = {r['mes']: r['gastos'] for r in gastos_mes}

    # Pagos a tiendas externas por mes
    pagos_mes = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as mes,
               COALESCE(SUM(monto),0) as pagos
        FROM pagos_tienda
        WHERE (es_interno=0 OR es_interno IS NULL)
        GROUP BY mes ORDER BY mes
    """).fetchall()
    pagos_map = {r['mes']: r['pagos'] for r in pagos_mes}

    por_mes = []
    for row in meses:
        m = row['mes']
        por_mes.append({
            'mes': m,
            'ventas': round(row['ventas'], 2),
            'num_ventas': int(row['num_ventas']),
            'ingresos': round(ingresos_map.get(m, 0), 2),
            'gastos': round(gastos_map.get(m, 0), 2),
            'pagos': round(pagos_map.get(m, 0), 2),
        })

    # Por año
    años = conn.execute("""
        SELECT strftime('%Y', created_at) as año,
               COALESCE(SUM(total),0) as ventas,
               COUNT(*) as num_ventas
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0)
        GROUP BY año ORDER BY año
    """).fetchall()

    ingresos_año = conn.execute("""
        SELECT strftime('%Y', created_at) as año,
               COALESCE(SUM(monto),0) as ingresos
        FROM ingresos GROUP BY año
    """).fetchall()
    ingresos_año_map = {r['año']: r['ingresos'] for r in ingresos_año}

    gastos_año = conn.execute("""
        SELECT strftime('%Y', created_at) as año,
               COALESCE(SUM(monto),0) as gastos
        FROM gastos GROUP BY año
    """).fetchall()
    gastos_año_map = {r['año']: r['gastos'] for r in gastos_año}

    # Pagos a tiendas externas por año
    pagos_año = conn.execute("""
        SELECT strftime('%Y', created_at) as año,
               COALESCE(SUM(monto),0) as pagos
        FROM pagos_tienda
        WHERE (es_interno=0 OR es_interno IS NULL)
        GROUP BY año
    """).fetchall()
    pagos_año_map = {r['año']: r['pagos'] for r in pagos_año}

    por_año = []
    for row in años:
        a = row['año']
        por_año.append({
            'año': a,
            'ventas': round(row['ventas'], 2),
            'num_ventas': int(row['num_ventas']),
            'ingresos': round(ingresos_año_map.get(a, 0), 2),
            'gastos': round(gastos_año_map.get(a, 0), 2),
            'pagos': round(pagos_año_map.get(a, 0), 2),
        })

    # Ventas por tienda por mes
    tienda_mes_rows = conn.execute("""
        SELECT strftime('%Y-%m', v.created_at) as mes,
               COALESCE(t.nombre, 'Sin Tienda') as tienda,
               COALESCE(SUM(vd.subtotal), 0) as total
        FROM venta_detalle vd
        JOIN ventas v ON v.id = vd.venta_id
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE (v.cancelada IS NULL OR v.cancelada = 0)
        GROUP BY mes, tienda ORDER BY mes, total DESC
    """).fetchall()

    # Ventas por tienda por año
    tienda_año_rows = conn.execute("""
        SELECT strftime('%Y', v.created_at) as año,
               COALESCE(t.nombre, 'Sin Tienda') as tienda,
               COALESCE(SUM(vd.subtotal), 0) as total
        FROM venta_detalle vd
        JOIN ventas v ON v.id = vd.venta_id
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE (v.cancelada IS NULL OR v.cancelada = 0)
        GROUP BY año, tienda ORDER BY año, total DESC
    """).fetchall()

    # Build {mes: {tienda: total}} maps
    tienda_mes_map = {}
    tiendas_set = set()
    for r in tienda_mes_rows:
        tienda_mes_map.setdefault(r['mes'], {})[r['tienda']] = round(r['total'], 2)
        tiendas_set.add(r['tienda'])

    tienda_año_map = {}
    for r in tienda_año_rows:
        tienda_año_map.setdefault(r['año'], {})[r['tienda']] = round(r['total'], 2)
        tiendas_set.add(r['tienda'])

    tiendas = sorted(tiendas_set)

    # Enrich por_mes and por_año with per-store data
    # Efectivo y tarjeta por período
    ef_tar_mes = conn.execute("""
        SELECT strftime('%Y-%m', created_at) as mes,
               COALESCE(SUM(monto_efectivo), 0) as efectivo,
               COALESCE(SUM(monto_tarjeta), 0) as tarjeta
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0)
        GROUP BY mes
    """).fetchall()
    ef_tar_mes_map = {r['mes']: (round(r['efectivo'],2), round(r['tarjeta'],2)) for r in ef_tar_mes}

    ef_tar_año = conn.execute("""
        SELECT strftime('%Y', created_at) as año,
               COALESCE(SUM(monto_efectivo), 0) as efectivo,
               COALESCE(SUM(monto_tarjeta), 0) as tarjeta
        FROM ventas WHERE (cancelada IS NULL OR cancelada=0)
        GROUP BY año
    """).fetchall()
    ef_tar_año_map = {r['año']: (round(r['efectivo'],2), round(r['tarjeta'],2)) for r in ef_tar_año}

    for row in por_mes:
        ef, tar = ef_tar_mes_map.get(row['mes'], (0, 0))
        row['efectivo'] = ef
        row['tarjeta'] = tar
        row['por_tienda'] = {t: tienda_mes_map.get(row['mes'], {}).get(t, 0) for t in tiendas}
    for row in por_año:
        ef, tar = ef_tar_año_map.get(row['año'], (0, 0))
        row['efectivo'] = ef
        row['tarjeta'] = tar
        row['por_tienda'] = {t: tienda_año_map.get(row['año'], {}).get(t, 0) for t in tiendas}

    # Datos diarios del año en curso
    año_actual = str(datetime.now().year)
    ventas_dia = conn.execute("""
        SELECT strftime('%Y-%m-%d', created_at) as dia,
               COALESCE(SUM(total), 0) as ventas,
               COALESCE(SUM(monto_efectivo), 0) as efectivo,
               COALESCE(SUM(monto_tarjeta), 0) as tarjeta
        FROM ventas
        WHERE (cancelada IS NULL OR cancelada=0)
          AND strftime('%Y', created_at) = ?
        GROUP BY dia ORDER BY dia
    """, (año_actual,)).fetchall()

    gastos_dia = conn.execute("""
        SELECT strftime('%Y-%m-%d', created_at) as dia,
               COALESCE(SUM(monto), 0) as gastos
        FROM gastos
        WHERE strftime('%Y', created_at) = ?
        GROUP BY dia ORDER BY dia
    """, (año_actual,)).fetchall()
    gastos_dia_map = {r['dia']: round(r['gastos'], 2) for r in gastos_dia}

    # Pagos a tiendas externas por día (año en curso)
    pagos_dia = conn.execute("""
        SELECT strftime('%Y-%m-%d', created_at) as dia,
               COALESCE(SUM(monto), 0) as pagos
        FROM pagos_tienda
        WHERE (es_interno=0 OR es_interno IS NULL)
          AND strftime('%Y', created_at) = ?
        GROUP BY dia ORDER BY dia
    """, (año_actual,)).fetchall()
    pagos_dia_map = {r['dia']: round(r['pagos'], 2) for r in pagos_dia}

    por_dia = []
    for row in ventas_dia:
        d = row['dia']
        por_dia.append({
            'dia': d,
            'label': d[5:],   # MM-DD
            'ventas': round(row['ventas'], 2),
            'efectivo': round(row['efectivo'], 2),
            'tarjeta': round(row['tarjeta'], 2),
            'gastos': round(gastos_dia_map.get(d, 0), 2),
            'pagos': round(pagos_dia_map.get(d, 0), 2),
        })

    conn.close()
    return {'por_mes': por_mes, 'por_año': por_año, 'tiendas': tiendas, 'por_dia': por_dia}


# Cláusula SQL centralizada: "Estudio Deco" en sentido de negocio = todo
# excepto la cafetería Estación 304 (misma convención que obtener_resumen_semana).
_SCOPE_ESTUDIO_SQL = "LOWER(COALESCE(t.nombre,'')) NOT LIKE '%estaci%'"

_DOW_ES = {
    '0': 'Domingo', '1': 'Lunes', '2': 'Martes', '3': 'Miércoles',
    '4': 'Jueves', '5': 'Viernes', '6': 'Sábado',
}
_DOW_ORDEN = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def obtener_estadisticas_estudio(desde=None, hasta=None):
    """Estadísticas enfocadas SOLO en Estudio Deco (excluye Estación 304).

    Responde a: cuánto se vende, qué taller vende más, qué días se vende más.
    Los totales se calculan sobre venta_detalle.subtotal (no sobre ventas.total),
    porque una venta puede mezclar artículos de varias tiendas.
    """
    conn = get_connection()

    # Rango de fechas opcional. Sin rango => histórico completo.
    fecha_clause = ""
    params = []
    if desde and hasta:
        fecha_clause = " AND DATE(v.created_at) BETWEEN ? AND ? "
        params = [desde, hasta]

    base_from = f"""
        FROM venta_detalle vd
        JOIN ventas v ON v.id = vd.venta_id
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE (v.cancelada IS NULL OR v.cancelada = 0)
          AND {_SCOPE_ESTUDIO_SQL}
          {fecha_clause}
    """

    # ── Resumen general del alcance ──
    resumen_row = conn.execute(f"""
        SELECT COALESCE(SUM(vd.subtotal), 0) as total,
               COUNT(DISTINCT v.id)          as num_ventas,
               COALESCE(SUM(vd.cantidad), 0) as unidades
        {base_from}
    """, params).fetchone()
    total_ventas = round(resumen_row['total'], 2)
    num_ventas = int(resumen_row['num_ventas'])
    unidades = int(resumen_row['unidades'])
    ticket_promedio = round(total_ventas / num_ventas, 2) if num_ventas else 0.0

    # ── Ranking de talleres (categoria_producto = 'talleres') ──
    talleres_rows = conn.execute(f"""
        SELECT vd.nombre_producto          as producto,
               COALESCE(SUM(vd.cantidad),0) as cantidad,
               COALESCE(SUM(vd.subtotal),0) as total
        FROM venta_detalle vd
        JOIN ventas v ON v.id = vd.venta_id
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        LEFT JOIN productos p ON p.id = vd.producto_id
        WHERE (v.cancelada IS NULL OR v.cancelada = 0)
          AND {_SCOPE_ESTUDIO_SQL}
          AND LOWER(COALESCE(p.categoria_producto,'')) = 'talleres'
          {fecha_clause}
        GROUP BY vd.nombre_producto
        ORDER BY total DESC
    """, params).fetchall()
    ranking_talleres = [
        {'producto': r['producto'], 'cantidad': int(r['cantidad']), 'total': round(r['total'], 2)}
        for r in talleres_rows
    ]

    # ── Ranking de tiendas (dentro del alcance) ──
    tiendas_rows = conn.execute(f"""
        SELECT COALESCE(t.nombre,'Sin Tienda') as tienda,
               COALESCE(SUM(vd.cantidad),0)    as cantidad,
               COALESCE(SUM(vd.subtotal),0)    as total
        {base_from}
        GROUP BY COALESCE(t.nombre,'Sin Tienda')
        ORDER BY total DESC
    """, params).fetchall()
    ranking_tiendas = [
        {'tienda': r['tienda'], 'cantidad': int(r['cantidad']), 'total': round(r['total'], 2)}
        for r in tiendas_rows
    ]

    # ── Top productos (cualquier categoría, dentro del alcance) ──
    productos_rows = conn.execute(f"""
        SELECT vd.nombre_producto          as producto,
               COALESCE(SUM(vd.cantidad),0) as cantidad,
               COALESCE(SUM(vd.subtotal),0) as total
        {base_from}
        GROUP BY vd.nombre_producto
        ORDER BY total DESC
        LIMIT 15
    """, params).fetchall()
    ranking_productos = [
        {'producto': r['producto'], 'cantidad': int(r['cantidad']), 'total': round(r['total'], 2)}
        for r in productos_rows
    ]

    # ── Ventas por día de la semana ──
    dow_rows = conn.execute(f"""
        SELECT strftime('%w', v.created_at) as dow,
               COALESCE(SUM(vd.subtotal),0) as total,
               COUNT(DISTINCT v.id)         as num_ventas
        {base_from}
        GROUP BY dow
    """, params).fetchall()
    dow_map = {r['dow']: r for r in dow_rows}
    ranking_dias_semana = []
    for nombre in _DOW_ORDEN:
        dow_key = next((k for k, v in _DOW_ES.items() if v == nombre), None)
        row = dow_map.get(dow_key)
        ranking_dias_semana.append({
            'dia': nombre,
            'total': round(row['total'], 2) if row else 0.0,
            'num_ventas': int(row['num_ventas']) if row else 0,
        })

    # ── Top días concretos (fechas con más venta) ──
    top_dias_rows = conn.execute(f"""
        SELECT DATE(v.created_at)            as fecha,
               COALESCE(SUM(vd.subtotal),0)  as total,
               COUNT(DISTINCT v.id)          as num_ventas
        {base_from}
        GROUP BY DATE(v.created_at)
        ORDER BY total DESC
        LIMIT 10
    """, params).fetchall()
    top_dias = [
        {'fecha': r['fecha'], 'total': round(r['total'], 2), 'num_ventas': int(r['num_ventas'])}
        for r in top_dias_rows
    ]

    # ── Serie mensual ──
    mes_rows = conn.execute(f"""
        SELECT strftime('%Y-%m', v.created_at) as mes,
               COALESCE(SUM(vd.subtotal),0)    as total,
               COUNT(DISTINCT v.id)            as num_ventas
        {base_from}
        GROUP BY mes
        ORDER BY mes
    """, params).fetchall()
    por_mes = [
        {'mes': r['mes'], 'total': round(r['total'], 2), 'num_ventas': int(r['num_ventas'])}
        for r in mes_rows
    ]

    conn.close()
    return {
        'scope': 'estudio_deco',
        'desde': desde,
        'hasta': hasta,
        'resumen': {
            'total': total_ventas,
            'num_ventas': num_ventas,
            'unidades': unidades,
            'ticket_promedio': ticket_promedio,
        },
        'ranking_talleres': ranking_talleres,
        'ranking_tiendas': ranking_tiendas,
        'ranking_productos': ranking_productos,
        'ranking_dias_semana': ranking_dias_semana,
        'top_dias': top_dias,
        'por_mes': por_mes,
    }


# ══════════════════════════════════════════════════════════════════
# INVENTARIO ESTACIÓN 304
# ══════════════════════════════════════════════════════════════════

# Recetario canónico: nombre_bebida → {nombre_ingrediente: cantidad_en_g_o_unidades}
# Nombres de ingredientes ya normalizados para coincidir exactamente con la BD.
RECETAS_BEBIDAS: dict[str, dict[str, float]] = {
    "AMERICANO":         {"Shot de cafe": 20, "Agua": 250,  "Hielo": 230, "Vaso": 1},
    "LATTE":             {"Shot de cafe": 15, "Leche": 250,  "Hielo": 230, "Vaso": 1},
    "CAPPUCHINO":        {"Shot de cafe": 20, "Leche": 220,  "Hielo": 230, "Vaso": 1},
    "MOCHA":             {"Shot de cafe": 20, "Leche": 200,  "Lechera": 10, "Carlos V polvo": 10, "Hielo": 220, "Vaso": 1},
    "LATTE VAINILLA":    {"Shot de cafe": 15, "Leche": 250,  "Vainilla syrup": 30, "Hielo": 230, "Vaso": 1},
    "CARAMEL MACCHIATO": {"Shot de cafe": 20, "Leche": 220,  "Caramelo": 35, "Vainilla syrup": 15, "Hielo": 230, "Vaso": 1},
    "AMANECER NARANJA":  {"Shot de cafe": 15, "Mineral": 100, "Jugo de naranja": 150, "Hielo": 230, "Vaso": 1},
    "PANCAKE LATTE":     {"Shot de cafe": 20, "Vainilla": 5,  "Azucar": 4, "Leche": 215, "Crema para batir": 30, "Maple": 10, "Hielo": 230, "Vaso": 1},
    "CHOCOLATE":         {"Carlos V polvo": 30, "Leche": 250, "Hielo": 230, "Vaso": 1},
    "TIRAMISU LATTE":    {"Shot de cafe": 20, "Leche": 215,  "Mascarpone": 30, "Crema para batir": 30, "Tiramisu syrup": 5, "Hielo": 230, "Vaso": 1},
    "NUBE DE FRESA":     {"Shot de cafe": 20, "Leche de fresa": 150, "Crema para batir": 30, "Yomi": 20, "Lechera": 10, "Hielo": 230, "Vaso": 1},
    "HORCHATA ESPRESSO": {"Shot de cafe": 20, "Horchata": 30, "Leche": 250, "Vaso": 1},
    "CHAI":              {"Chai": 30,  "Leche": 250, "Hielo": 230, "Vaso": 1},
    "TARO":              {"Taro": 30,  "Leche": 250, "Hielo": 230, "Vaso": 1},
    "LIMONADA ROSA":     {"Jarabe limonada": 50, "Mineral": 296, "Hielo": 230, "Vaso": 1},
    "CHOCOMENTA":        {"Shot de cafe": 15, "Leche": 250, "Menta": 6, "Crema para batir": 35, "Chocolate davinc": 20, "Lechera": 5, "Hielo": 230, "Vaso": 1},
}

# Ingredientes que se cuentan por unidad (no gramos/ml)
_UNIDAD_UNIDADES = {"Vaso", "Yomi"}


def _seed_ingredientes():
    """Inserta en inv_ingredientes todos los insumos únicos del recetario (solo si no existen)."""
    ingredientes: dict[str, str] = {}
    for receta in RECETAS_BEBIDAS.values():
        for nombre in receta:
            if nombre not in ingredientes:
                unidad = "unidad" if nombre in _UNIDAD_UNIDADES else "g"
                ingredientes[nombre] = unidad

    conn = get_connection()
    for nombre, unidad in ingredientes.items():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO inv_ingredientes (nombre, unidad) VALUES (?,?)",
                (nombre, unidad)
            )
        except Exception as e:
            logging.error(f"Silenced error: {e}")
    conn.commit()
    conn.close()


def _seed_recetas():
    """Inserta en inv_recetas e inv_receta_ingredientes las recetas del recetario canónico."""
    conn = get_connection()
    for nombre_bebida, ingredientes in RECETAS_BEBIDAS.items():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO inv_recetas (nombre) VALUES (?)",
                (nombre_bebida,)
            )
            conn.commit()
        except Exception as e:
            logging.error(f"Silenced error: {e}")
        receta_row = conn.execute(
            "SELECT id FROM inv_recetas WHERE nombre=?", (nombre_bebida,)
        ).fetchone()
        if not receta_row:
            continue
        receta_id = receta_row["id"]
        for nombre_ing, cantidad in ingredientes.items():
            ing_row = conn.execute(
                "SELECT id FROM inv_ingredientes WHERE nombre=?", (nombre_ing,)
            ).fetchone()
            if not ing_row:
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO inv_receta_ingredientes (receta_id, ingrediente_id, cantidad) VALUES (?,?,?)",
                    (receta_id, ing_row["id"], cantidad)
                )
                conn.commit()
            except Exception as e:
                logging.error(f"Silenced error: {e}")
    conn.close()


def listar_ingredientes() -> list[dict]:
    """Devuelve todos los ingredientes con stock actual, mínimo, costo unitario y unidad."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, nombre, unidad, stock_actual, stock_minimo, costo_unitario, updated_at
        FROM inv_ingredientes
        ORDER BY nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def crear_ingrediente(nombre: str, unidad: str = "g", stock_inicial: float = 0, stock_minimo: float = 0) -> dict:
    """Crea un nuevo ingrediente personalizado en el inventario."""
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if unidad not in ("g", "unidad"):
        raise ValueError("Unidad debe ser 'g' o 'unidad'.")
    if stock_inicial < 0 or stock_minimo < 0:
        raise ValueError("Los valores de stock no pueden ser negativos.")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO inv_ingredientes (nombre, unidad, stock_actual, stock_minimo) VALUES (?,?,?,?)",
            (nombre, unidad, stock_inicial, stock_minimo)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM inv_ingredientes WHERE id=last_insert_rowid()").fetchone()
        return dict(row)
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        if "UNIQUE" in str(e):
            raise ValueError(f"Ya existe un ingrediente llamado '{nombre}'.")
        raise
    finally:
        conn.close()


def calcular_porciones_disponibles() -> dict[str, dict]:
    """
    Calcula cuántas porciones de cada bebida se pueden preparar
    con el stock actual de la BD.

    Retorna:
        {
          nombre_bebida: {
            porciones: int,          # 0 si hay escasez
            cuello_de_botella: str,  # ingrediente que limita (None si porciones>0)
            faltantes: [str],        # ingredientes con stock = 0
          }
        }
    """
    conn = get_connection()
    stock_rows = conn.execute("SELECT nombre, stock_actual FROM inv_ingredientes").fetchall()
    stock: dict[str, float] = {r["nombre"]: r["stock_actual"] for r in stock_rows}

    recetas_rows = conn.execute("""
        SELECT r.nombre as bebida, i.nombre as ingrediente, ri.cantidad
        FROM inv_recetas r
        JOIN inv_receta_ingredientes ri ON ri.receta_id = r.id
        JOIN inv_ingredientes i ON i.id = ri.ingrediente_id
        WHERE r.activo = 1
    """).fetchall()
    conn.close()

    recetas: dict[str, dict[str, float]] = {}
    for row in recetas_rows:
        recetas.setdefault(row["bebida"], {})[row["ingrediente"]] = row["cantidad"]

    resultado: dict[str, dict] = {}
    for bebida, receta in recetas.items():
        min_porciones: float = float("inf")
        cuello: str | None = None
        faltantes: list[str] = []

        for ingrediente, cantidad in receta.items():
            disponible = stock.get(ingrediente, 0.0)
            if disponible <= 0:
                faltantes.append(ingrediente)
                min_porciones = 0
                continue
            if cantidad <= 0:
                continue
            posibles = disponible / cantidad
            if posibles < min_porciones:
                min_porciones = posibles
                cuello = ingrediente

        if min_porciones == float("inf"):
            min_porciones = 0

        porciones = max(0, int(min_porciones))
        resultado[bebida] = {
            "porciones": porciones,
            "cuello_de_botella": None if porciones > 0 else cuello,
            "faltantes": faltantes,
        }

    return resultado


def descontar_ingredientes_bebida(nombre_bebida: str) -> None:
    """
    Descuenta los insumos exactos de la BD al registrar la venta de una bebida.

    Raises:
        ValueError: si la bebida no existe en el recetario, o si el stock
                    de algún ingrediente es insuficiente.
    """
    key = nombre_bebida.strip().upper()
    conn = get_connection()
    try:
        receta_row = conn.execute(
            "SELECT id FROM inv_recetas WHERE nombre=? AND activo=1", (key,)
        ).fetchone()
        if not receta_row:
            raise ValueError(f"Bebida '{nombre_bebida}' no encontrada en el recetario.")

        ing_rows = conn.execute("""
            SELECT i.nombre, i.stock_actual, ri.cantidad
            FROM inv_receta_ingredientes ri
            JOIN inv_ingredientes i ON i.id = ri.ingrediente_id
            WHERE ri.receta_id = ?
        """, (receta_row["id"],)).fetchall()

        receta = {r["nombre"]: r["cantidad"] for r in ing_rows}

        # ── 1. Verificar stock suficiente antes de tocar nada ──
        for row in ing_rows:
            if row["stock_actual"] < row["cantidad"]:
                raise ValueError(
                    f"Stock insuficiente de '{row['nombre']}': "
                    f"disponible {row['stock_actual']:.1f}, necesario {row['cantidad']}."
                )

        # ── 2. Descontar ──
        for ingrediente, cantidad in receta.items():
            conn.execute(
                """UPDATE inv_ingredientes
                   SET stock_actual = stock_actual - ?,
                       updated_at   = datetime('now','localtime')
                   WHERE nombre = ?""",
                (cantidad, ingrediente)
            )

        # ── 3. Registrar en log ──
        conn.execute(
            "INSERT INTO inv_consumo_log (nombre_bebida) VALUES (?)", (key,)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def restock_ingrediente(ingrediente_id: int, cantidad: float) -> None:
    """Suma `cantidad` al stock actual de un ingrediente."""
    if cantidad <= 0:
        raise ValueError("La cantidad a reponer debe ser mayor a 0.")
    conn = get_connection()
    affected = conn.execute(
        """UPDATE inv_ingredientes
           SET stock_actual = stock_actual + ?,
               updated_at   = datetime('now','localtime')
           WHERE id = ?""",
        (cantidad, ingrediente_id)
    ).rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        raise ValueError(f"Ingrediente id={ingrediente_id} no encontrado.")


def ajustar_stock_ingrediente(ingrediente_id: int, nuevo_stock: float) -> None:
    """Establece el stock exacto de un ingrediente (útil para inventarios físicos)."""
    if nuevo_stock < 0:
        raise ValueError("El stock no puede ser negativo.")
    conn = get_connection()
    affected = conn.execute(
        """UPDATE inv_ingredientes
           SET stock_actual = ?,
               updated_at   = datetime('now','localtime')
           WHERE id = ?""",
        (nuevo_stock, ingrediente_id)
    ).rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        raise ValueError(f"Ingrediente id={ingrediente_id} no encontrado.")


def ajustar_stock_minimo(ingrediente_id: int, stock_minimo: float) -> None:
    """Actualiza el stock mínimo de alerta de un ingrediente."""
    if stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo.")
    conn = get_connection()
    conn.execute(
        "UPDATE inv_ingredientes SET stock_minimo=? WHERE id=?",
        (stock_minimo, ingrediente_id)
    )
    conn.commit()
    conn.close()


def obtener_log_consumo(limit: int = 100) -> list[dict]:
    """Devuelve el historial de bebidas vendidas con descuento de inventario."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, nombre_bebida, concepto, created_at
        FROM inv_consumo_log
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def registrar_compra_insumo(
    ingrediente_id: int,
    cantidad: float,
    costo_total: float,
    nota: str = "",
) -> dict:
    """
    Registra la compra de un insumo en una sola transacción atómica:
      1. Inserta en inv_entradas.
      2. Suma cantidad al stock_actual del ingrediente.
      3. Recalcula el costo_unitario promedio ponderado (CPP):
            CPP_nuevo = (stock_anterior * CPP_anterior + costo_total)
                        / (stock_anterior + cantidad)

    Returns el registro insertado en inv_entradas.
    Raises ValueError si los parámetros son inválidos o el ingrediente no existe.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0.")
    if costo_total < 0:
        raise ValueError("El costo total no puede ser negativo.")

    costo_unitario_entrada = round(costo_total / cantidad, 6) if cantidad else 0

    conn = get_connection()
    try:
        # Leer estado actual del ingrediente
        ing = conn.execute(
            "SELECT id, stock_actual, costo_unitario FROM inv_ingredientes WHERE id = ?",
            (ingrediente_id,)
        ).fetchone()
        if ing is None:
            raise ValueError(f"Ingrediente id={ingrediente_id} no encontrado.")

        stock_ant  = ing["stock_actual"]
        costo_ant  = ing["costo_unitario"]

        # Costo Promedio Ponderado
        stock_nuevo = stock_ant + cantidad
        if stock_nuevo > 0:
            cpp = (stock_ant * costo_ant + costo_total) / stock_nuevo
        else:
            cpp = costo_unitario_entrada

        # Insertar entrada
        conn.execute(
            """INSERT INTO inv_entradas
               (ingrediente_id, cantidad, costo_total, costo_unitario, nota)
               VALUES (?,?,?,?,?)""",
            (ingrediente_id, cantidad, costo_total, costo_unitario_entrada, nota)
        )
        entrada_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Actualizar ingrediente
        conn.execute(
            """UPDATE inv_ingredientes
               SET stock_actual   = stock_actual + ?,
                   costo_unitario = ?,
                   updated_at     = datetime('now','localtime')
               WHERE id = ?""",
            (cantidad, round(cpp, 6), ingrediente_id)
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM inv_entradas WHERE id = ?", (entrada_id,)
        ).fetchone()
        return dict(row)
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_entradas_ingrediente(ingrediente_id: int, limit: int = 50) -> list[dict]:
    """Devuelve el historial de compras de un ingrediente específico."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.id, e.cantidad, e.costo_total, e.costo_unitario, e.nota, e.created_at,
                  i.nombre as ingrediente, i.unidad
           FROM inv_entradas e
           JOIN inv_ingredientes i ON i.id = e.ingrediente_id
           WHERE e.ingrediente_id = ?
           ORDER BY e.created_at DESC
           LIMIT ?""",
        (ingrediente_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_todas_entradas(limit: int = 100) -> list[dict]:
    """Historial completo de compras de todos los insumos."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT e.id, e.ingrediente_id, i.nombre as ingrediente, i.unidad,
                  e.cantidad, e.costo_total, e.costo_unitario, e.nota, e.created_at
           FROM inv_entradas e
           JOIN inv_ingredientes i ON i.id = e.ingrediente_id
           ORDER BY e.created_at DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── CRUD RECETAS ──

def listar_recetas() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.id, r.nombre, r.activo,
               COUNT(ri.id) as num_ingredientes
        FROM inv_recetas r
        LEFT JOIN inv_receta_ingredientes ri ON ri.receta_id = r.id
        GROUP BY r.id
        ORDER BY r.nombre
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_receta_detalle(receta_id: int) -> dict | None:
    conn = get_connection()
    receta = conn.execute(
        "SELECT id, nombre FROM inv_recetas WHERE id=?", (receta_id,)
    ).fetchone()
    if not receta:
        conn.close()
        return None
    ings = conn.execute("""
        SELECT ri.ingrediente_id, i.nombre as ingrediente_nombre, i.unidad, ri.cantidad
        FROM inv_receta_ingredientes ri
        JOIN inv_ingredientes i ON i.id = ri.ingrediente_id
        WHERE ri.receta_id = ?
        ORDER BY i.nombre
    """, (receta_id,)).fetchall()
    conn.close()
    return {
        "id": receta["id"],
        "nombre": receta["nombre"],
        "ingredientes": [dict(r) for r in ings],
    }


def crear_receta(nombre: str) -> dict:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    conn = get_connection()
    try:
        conn.execute("INSERT INTO inv_recetas (nombre) VALUES (?)", (nombre,))
        conn.commit()
        row = conn.execute("SELECT * FROM inv_recetas WHERE id=last_insert_rowid()").fetchone()
        return dict(row)
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        if "UNIQUE" in str(e):
            raise ValueError(f"Ya existe una receta llamada '{nombre}'.")
        raise
    finally:
        conn.close()


def actualizar_nombre_receta(receta_id: int, nombre: str) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    conn = get_connection()
    try:
        conn.execute("UPDATE inv_recetas SET nombre=? WHERE id=?", (nombre, receta_id))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        if "UNIQUE" in str(e):
            raise ValueError(f"Ya existe una receta llamada '{nombre}'.")
        raise
    finally:
        conn.close()


def eliminar_receta(receta_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM inv_receta_ingredientes WHERE receta_id=?", (receta_id,))
        conn.execute("DELETE FROM inv_recetas WHERE id=?", (receta_id,))
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def agregar_ingrediente_receta(receta_id: int, ingrediente_id: int, cantidad: float) -> None:
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0.")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO inv_receta_ingredientes (receta_id, ingrediente_id, cantidad) VALUES (?,?,?)",
            (receta_id, ingrediente_id, cantidad)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"DB Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def quitar_ingrediente_receta(receta_id: int, ingrediente_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "DELETE FROM inv_receta_ingredientes WHERE receta_id=? AND ingrediente_id=?",
        (receta_id, ingrediente_id)
    )
    conn.commit()
    conn.close()
