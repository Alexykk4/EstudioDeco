import logging
logging.basicConfig(filename="errores.log", level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
"""
server.py — Estudio Deco POS v2
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import uvicorn, hashlib, secrets

from modules.database import (
    init_db, listar_tiendas, obtener_productos, validar_nip,
    registrar_venta, registrar_gasto, obtener_resumen_dia,
    registrar_corte, obtener_stock, listar_usuarios, crear_usuario,
    listar_mesas, abrir_mesa, agregar_item_orden,
    quitar_item_orden, cerrar_mesa, obtener_items_comanda, get_connection,
    obtener_ordenes_mesa, renombrar_orden, cancelar_orden_mesa,
    obtener_todos_los_productos, crear_producto, actualizar_producto, eliminar_producto,
    actualizar_item_orden, registrar_ingreso, set_fondo_apertura, get_fondo_apertura,
    obtener_ventas_dia, obtener_ventas_turno, corregir_venta, anular_venta,
    obtener_bundle_components, agregar_bundle_component, eliminar_bundle_component,
    obtener_resumen_semana, registrar_pago_tienda, obtener_pagos_semana,
    obtener_estadisticas, obtener_estadisticas_estudio,
    obtener_balance_actual, ajustar_balance, limpiar_ingresos_gastos,
    registrar_nomina, listar_nominas,
    registrar_movimiento_estacion, obtener_balance_estacion, obtener_movimientos_estacion,
    listar_gastos, anular_gasto, listar_ingresos, anular_ingreso,
    listar_ingredientes, calcular_porciones_disponibles, descontar_ingredientes_bebida,
    restock_ingrediente, ajustar_stock_ingrediente, ajustar_stock_minimo, obtener_log_consumo,
    registrar_compra_insumo, listar_entradas_ingrediente, listar_todas_entradas, crear_ingrediente,
    listar_recetas, obtener_receta_detalle, crear_receta, actualizar_nombre_receta,
    eliminar_receta, agregar_ingrediente_receta, quitar_ingrediente_receta,
)
from modules.printer import imprimir_ticket, imprimir_comanda, imprimir_corte_caja
from modules.pdf_report import generar_corte_pdf, generar_nomina_pdf
from modules.email_sender import enviar_corte_email, enviar_notificacion_email, enviar_nomina_email
from modules.sync_sheets import sync_worker

init_db(); sync_worker.start()
app = FastAPI(title="Estudio Deco POS", version="2.0")

# ── System users (login) ──
# S-1: contraseñas almacenadas como hash SHA-256 (nunca en texto plano)
def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

SYSTEM_USERS = {
    "estudiodeco": {"password_hash": _hash_pw("19jul"),    "role": "deco"},
    "estacion304": {"password_hash": _hash_pw("telefono"), "role": "estacion"},
}

# S-2: tokens de sesión en memoria (se invalidan al reiniciar el servidor)
_active_tokens: dict[str, dict] = {}

STATIC = Path(__file__).parent / "static"
ASSETS = Path(__file__).parent / "assets"
ASSETS.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS)), name="assets")

# ── Models ──
class NipReq(BaseModel): nip: str
class AddItemReq(BaseModel):
    producto_id: int | None = None
    tienda_id: int
    nombre: str
    cantidad: int = Field(default=1, ge=1)
    precio_unitario: float = Field(ge=0.0)
    es_precio_abierto: bool = False
class EditItemReq(BaseModel):
    nombre: str
    precio_unitario: float = Field(ge=0.0)
class CerrarMesaReq(BaseModel):
    usuario_id: int
    metodo_pago: str
    monto_efectivo: float = Field(default=0.0, ge=0.0)
    monto_tarjeta: float = Field(default=0.0, ge=0.0)
    efectivo_recibido: float = Field(default=0.0, ge=0.0)

class MesaNombreReq(BaseModel):
    nombre: str

class AbrirMesaReq(BaseModel):
    usuario_id: int
    nombre_cliente: str = ""

class GastoReq(BaseModel):
    usuario_id: int
    categoria: str | None = None
    tienda_id: int | None = None
    concepto: str
    monto: float = Field(ge=0.0)
    origen: str = "Caja"
class CorteReq(BaseModel):
    usuario_id: int
    efectivo_real: float = Field(ge=0.0)
    fondo_caja: float = Field(default=0.0, ge=0.0)
    desglose: dict = {}

class IngresoReq(BaseModel):
    usuario_id: int
    concepto: str = "Ingreso"
    monto: float = Field(ge=0.0)
    metodo_pago: str = "Efectivo"

class FondoReq(BaseModel):
    monto: float = Field(ge=0.0)

class ImprimirCorteReq(BaseModel):
    usuario_id: int

class CorregirVentaReq(BaseModel):
    metodo_pago: str
    monto_efectivo: float = Field(default=0.0, ge=0.0)
    monto_tarjeta: float = Field(default=0.0, ge=0.0)

class BundleComponentReq(BaseModel):
    componente_id: int
    cantidad: int = Field(default=1, ge=1)
    precio_asignado: float = Field(ge=0.0)

class LoginReq(BaseModel):
    username: str
    password: str

class EstacionGastoReq(BaseModel):
    concepto: str
    monto: float = Field(ge=0.0)
    metodo_pago: str = "Efectivo"

class RestockReq(BaseModel):
    cantidad: float = Field(ge=0.0)

class AjustarStockReq(BaseModel):
    nuevo_stock: float = Field(ge=0.0)

class AjustarMinimoReq(BaseModel):
    stock_minimo: float = Field(ge=0.0)

class BebidaVendidaReq(BaseModel):
    nombre_bebida: str

class NuevoIngredienteReq(BaseModel):
    nombre: str
    unidad: str = "g"
    stock_inicial: float = Field(default=0.0, ge=0.0)
    stock_minimo: float = Field(default=0.0, ge=0.0)

class CompraInsumoReq(BaseModel):
    ingrediente_id: int
    cantidad: float = Field(ge=0.0)
    costo_total: float = Field(ge=0.0)
    nota: str = ""

class RecetaNombreReq(BaseModel):
    nombre: str

class RecetaIngredienteReq(BaseModel):
    ingrediente_id: int
    cantidad: float = Field(ge=0.0)

class PagoTiendaReq(BaseModel):
    usuario_id: int | None = None
    tienda_id: int
    tienda_nombre: str
    monto: float = Field(ge=0.0)
    metodo_pago: str = "Efectivo"
    concepto: str = ""
    es_interno: bool = False
    semana_inicio: str
    semana_fin: str

class ProductReq(BaseModel):
    tienda_id: int
    nombre: str
    precio: float = Field(ge=0.0)
    costo: float = Field(default=0.0, ge=0.0)
    stock_local: int = Field(ge=0)
    stock_minimo: int = Field(ge=0)
    codigo: str = ""
    es_precio_abierto: bool = False
    es_bundle: int = 0
    categoria_producto: str = ""
    receta_key: str = ""

class NotaReq(BaseModel):
    texto: str
    pos_x: float = 100
    pos_y: float = 100
    color: str = "#fef3c7"

# ── Pages ──
@app.get("/")
async def root():
    r = FileResponse(str(STATIC / "index.html"))
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r

# ── Auth ──
@app.post("/api/auth")
async def auth(r: NipReq):
    u = validar_nip(r.nip)
    if not u: raise HTTPException(401, "NIP incorrecto")
    return u

@app.post("/api/login")
async def login(r: LoginReq):
    user = SYSTEM_USERS.get(r.username)
    if not user or user["password_hash"] != _hash_pw(r.password):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = secrets.token_urlsafe(32)
    _active_tokens[token] = {"username": r.username, "role": user["role"]}
    return {"ok": True, "role": user["role"], "username": r.username, "token": token}

@app.post("/api/logout")
async def logout(x_auth_token: str | None = Header(default=None)):
    if x_auth_token and x_auth_token in _active_tokens:
        del _active_tokens[x_auth_token]
    return {"ok": True}

# ── Estación 304 admin ──
@app.get("/api/estacion/balance")
async def api_estacion_balance(): return obtener_balance_estacion()

@app.get("/api/estacion/movimientos")
async def api_estacion_movimientos(): return obtener_movimientos_estacion()

@app.post("/api/estacion/gasto")
async def api_estacion_gasto(r: EstacionGastoReq):
    registrar_movimiento_estacion('gasto', r.concepto, r.monto, r.metodo_pago)
    return {"ok": True}

@app.post("/api/estacion/ingreso")
async def api_estacion_ingreso(r: EstacionGastoReq):
    registrar_movimiento_estacion('ingreso', r.concepto, r.monto, r.metodo_pago)
    return {"ok": True}

# ── Inventario Estación 304 ──
@app.get("/api/estacion/inventario")
async def api_inventario():
    return listar_ingredientes()

@app.post("/api/estacion/inventario")
async def api_crear_ingrediente(r: NuevoIngredienteReq):
    try:
        return crear_ingrediente(r.nombre, r.unidad, r.stock_inicial, r.stock_minimo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/estacion/porciones")
async def api_porciones():
    return calcular_porciones_disponibles()

@app.post("/api/estacion/inventario/{iid}/restock")
async def api_restock(iid: int, r: RestockReq):
    try:
        restock_ingrediente(iid, r.cantidad)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/estacion/inventario/{iid}")
async def api_ajustar_stock(iid: int, r: AjustarStockReq):
    try:
        ajustar_stock_ingrediente(iid, r.nuevo_stock)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/estacion/inventario/{iid}/minimo")
async def api_ajustar_minimo(iid: int, r: AjustarMinimoReq):
    try:
        ajustar_stock_minimo(iid, r.stock_minimo)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/estacion/bebida-vendida")
async def api_bebida_vendida(r: BebidaVendidaReq):
    """Descuenta los ingredientes de una bebida. Si el stock es insuficiente, avisa pero no bloquea."""
    try:
        descontar_ingredientes_bebida(r.nombre_bebida)
        return {"ok": True}
    except ValueError as e:
        return {"ok": False, "warning": str(e)}

@app.get("/api/estacion/consumo-log")
async def api_consumo_log():
    return obtener_log_consumo()

@app.post("/api/estacion/compras")
async def api_registrar_compra(r: CompraInsumoReq):
    try:
        entrada = registrar_compra_insumo(r.ingrediente_id, r.cantidad, r.costo_total, r.nota)
        return entrada
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/estacion/compras")
async def api_todas_entradas():
    return listar_todas_entradas()

@app.get("/api/estacion/compras/{iid}")
async def api_entradas_ingrediente(iid: int):
    return listar_entradas_ingrediente(iid)

# ── Data ──
@app.get("/api/tiendas")
async def api_tiendas(): return listar_tiendas()

@app.get("/api/productos/{tid}")
async def api_productos(tid: int): return obtener_productos(tid)

# ── Catálogo ──
@app.get("/api/catalog")
async def api_get_catalog(): return obtener_todos_los_productos()

@app.post("/api/catalog")
async def api_post_catalog(r: ProductReq):
    pid = crear_producto(r.tienda_id, r.nombre, r.precio, r.costo, r.stock_local, r.stock_minimo, r.codigo, 1 if r.es_precio_abierto else 0, r.es_bundle, r.categoria_producto, r.receta_key)
    return {"id": pid}

@app.put("/api/catalog/{pid}")
async def api_put_catalog(pid: int, r: ProductReq):
    actualizar_producto(pid, r.tienda_id, r.nombre, r.precio, r.costo, r.stock_local, r.stock_minimo, r.codigo, 1 if r.es_precio_abierto else 0, r.es_bundle, r.categoria_producto, r.receta_key)
    return {"ok": True}

@app.get("/api/estacion/recetas")
async def api_recetas():
    return listar_recetas()

@app.get("/api/estacion/recetas/{rid}")
async def api_receta_detalle(rid: int):
    r = obtener_receta_detalle(rid)
    if r is None:
        raise HTTPException(404, "Receta no encontrada")
    return r

@app.post("/api/estacion/recetas")
async def api_crear_receta(r: RecetaNombreReq):
    try:
        return crear_receta(r.nombre)
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.put("/api/estacion/recetas/{rid}")
async def api_actualizar_receta(rid: int, r: RecetaNombreReq):
    try:
        actualizar_nombre_receta(rid, r.nombre)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/estacion/recetas/{rid}")
async def api_eliminar_receta(rid: int):
    eliminar_receta(rid)
    return {"ok": True}

@app.post("/api/estacion/recetas/{rid}/ingredientes")
async def api_agregar_ing_receta(rid: int, r: RecetaIngredienteReq):
    try:
        agregar_ingrediente_receta(rid, r.ingrediente_id, r.cantidad)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/estacion/recetas/{rid}/ingredientes/{iid}")
async def api_quitar_ing_receta(rid: int, iid: int):
    quitar_ingrediente_receta(rid, iid)
    return {"ok": True}

@app.delete("/api/catalog/{pid}")
async def api_del_catalog(pid: int):
    eliminar_producto(pid)
    return {"ok": True}

# ── MESAS / ORDENES ──
@app.get("/api/mesas")
async def api_mesas():
    """Lista todas las mesas con sus órdenes e items usando 3 queries en total (S-8)."""
    conn = get_connection()
    mesas_raw = conn.execute("SELECT * FROM mesas").fetchall()

    # Query única para todas las órdenes abiertas
    ordenes_raw = conn.execute(
        "SELECT id, mesa_id, nombre_cliente FROM ordenes WHERE estado='abierta'"
    ).fetchall()

    # Query única para todos los items de esas órdenes
    items_raw = []
    if ordenes_raw:
        orden_ids = [o["id"] for o in ordenes_raw]
        ph = ",".join("?" * len(orden_ids))
        items_raw = conn.execute(
            f"SELECT orden_id, cantidad, precio_unitario FROM orden_items WHERE orden_id IN ({ph})",
            orden_ids
        ).fetchall()

    conn.close()

    # Construir mapas de lookup
    items_by_orden = {}
    for it in items_raw:
        items_by_orden.setdefault(it["orden_id"], []).append(it)

    ordenes_by_mesa = {}
    for o in ordenes_raw:
        ordenes_by_mesa.setdefault(o["mesa_id"], []).append(o)

    mesas = []
    for m in mesas_raw:
        m_dict = dict(m)
        ordenes = ordenes_by_mesa.get(m["id"], [])
        total_orden = 0
        num_items = 0
        for o in ordenes:
            for it in items_by_orden.get(o["id"], []):
                num_items += it["cantidad"]
                total_orden += it["cantidad"] * it["precio_unitario"]
        m_dict["ordenes"] = [{"id": o["id"], "nombre_cliente": o["nombre_cliente"]} for o in ordenes]
        m_dict["total_orden"] = total_orden
        m_dict["num_items"] = num_items
        mesas.append(m_dict)

    return mesas

@app.post("/api/mesas/{mid}/abrir")
async def api_abrir(mid: int, r: AbrirMesaReq):
    return {"orden_id": abrir_mesa(mid, r.usuario_id, r.nombre_cliente)}

@app.put("/api/ordenes/{oid}/nombre")
async def api_renombrar_orden(oid: int, r: MesaNombreReq):
    renombrar_orden(oid, r.nombre)
    return {"ok": True}

@app.get("/api/mesas/{mid}/ordenes")
async def api_orden(mid: int):
    return obtener_ordenes_mesa(mid)

@app.post("/api/ordenes/{oid}/items")
async def api_items_orden(oid: int, r: AddItemReq):
    item_id = agregar_item_orden(oid, r.producto_id, r.tienda_id, r.nombre, r.cantidad, r.precio_unitario, r.es_precio_abierto)
    # No imprimimos automáticamente; la comanda se envía con botón manual
    return {"item_id": item_id, "comanda": False}


@app.post("/api/ordenes/{oid}/comanda")
async def api_comanda(oid: int):
    items = obtener_items_comanda(oid)
    if not items: return {"printed": 0}
    
    # Get table info for the name
    conn = get_connection()
    o = conn.execute("""
        SELECT o.nombre_cliente, m.numero 
        FROM ordenes o
        JOIN mesas m ON m.id = o.mesa_id
        WHERE o.id=?
    """, (oid,)).fetchone()
    conn.close()
    
    label = f"MESA {o['numero']}" if o else f"ORDEN {oid}"
    if o and o["nombre_cliente"]:
        label += f" - {o['nombre_cliente']}"
        
    ok = imprimir_comanda(label, items)
    return {"printed": len(items) if ok else 0}

@app.put("/api/orden-items/{item_id}")
async def api_put_item(item_id: int, r: EditItemReq):
    actualizar_item_orden(item_id, r.nombre, r.precio_unitario)
    return {"ok": True}

@app.delete("/api/orden-items/{item_id}")
async def api_del_item(item_id: int):
    quitar_item_orden(item_id); return {"ok": True}

@app.delete("/api/ordenes/{oid}")
async def api_cancelar_orden(oid: int):
    ok = cancelar_orden_mesa(oid)
    if not ok: raise HTTPException(404, "Orden no encontrada")
    return {"ok": True}

def _descontar_bebidas_venta(items: list):
    """Descuenta ingredientes usando receta_key del producto. Opera silenciosamente."""
    conn = get_connection()
    for it in items:
        prod_id   = it.get("producto_id")
        receta_key = ""
        if prod_id:
            try:
                row = conn.execute("SELECT receta_key FROM productos WHERE id=?", (prod_id,)).fetchone()
                if row:
                    receta_key = (row["receta_key"] or "").strip()
            except Exception as e:
                logging.error(f"Silenced error in server: {e}")
        # Fallback: comparar nombre en mayúsculas (compatibilidad con productos sin receta asignada)
        if not receta_key:
            receta_key = (it.get("nombre_producto") or it.get("nombre") or "").strip().upper()
        if not receta_key:
            continue
        cantidad = int(it.get("cantidad", 1))
        for _ in range(cantidad):
            try:
                descontar_ingredientes_bebida(receta_key)
            except Exception as e:
                logging.error(f"Silenced error in server: {e}")
    conn.close()


@app.post("/api/ordenes/{oid}/cerrar")
async def api_cerrar(oid: int, r: CerrarMesaReq):
    # Obtener items de comanda ANTES de cerrar (items de barra no impresos)
    items_comanda = obtener_items_comanda(oid)

    venta = cerrar_mesa(oid, r.usuario_id, r.metodo_pago, r.monto_efectivo, r.monto_tarjeta, r.efectivo_recibido)
    if not venta: raise HTTPException(400, "No se pudo cerrar")

    # Descontar ingredientes del inventario para bebidas de Estación 304
    _descontar_bebidas_venta(venta.get("items", []))

    conn = get_connection()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    conn.close()

    cajero = row["nombre"] if row else "?"
    impreso = imprimir_ticket(venta, cajero)

    # Imprimir comanda automáticamente si hay items de barra
    if items_comanda:
        conn = get_connection()
        o = conn.execute("""
            SELECT o.nombre_cliente, m.numero
            FROM ordenes o JOIN mesas m ON m.id = o.mesa_id WHERE o.id=?
        """, (oid,)).fetchone()
        conn.close()
        label = f"MESA {o['numero']}" if o else f"ORDEN {oid}"
        if o and o["nombre_cliente"]:
            label += f" - {o['nombre_cliente']}"
        imprimir_comanda(label, items_comanda)

    return {"venta": venta, "impreso": impreso, "cajero": cajero}

# ── Ventas directas (sin mesa) ──
@app.post("/api/ventas")
async def api_venta_directa(r: dict):
    venta = registrar_venta(r["usuario_id"], r["metodo_pago"], r["items"], r.get("monto_efectivo", 0.0), r.get("monto_tarjeta", 0.0), r.get("efectivo_recibido", 0.0))
    conn = get_connection()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r["usuario_id"],)).fetchone()
    conn.close()
    cajero = row["nombre"] if row else "?"
    # Descontar ingredientes del inventario para bebidas de Estación 304
    _descontar_bebidas_venta(venta.get("items", []))
    impreso = imprimir_ticket(venta, cajero)
    # Imprimir comanda automática para items de barra (tienda_id=1)
    # Consultamos venta_detalle (ya expandida con componentes de bundles)
    venta_id = venta["venta_id"]
    conn2 = get_connection()
    items_barra = conn2.execute(
        "SELECT nombre_producto, cantidad FROM venta_detalle WHERE venta_id=? AND tienda_id=1",
        (venta_id,)
    ).fetchall()
    conn2.close()
    if items_barra:
        imprimir_comanda("VENTA DIRECTA", [dict(i) for i in items_barra])
    return {"venta": venta, "impreso": impreso, "cajero": cajero}

# ── Gastos ──
@app.get("/api/gastos")
async def api_listar_gastos(limit: int = 50, offset: int = 0):
    return listar_gastos(limit=limit, offset=offset)

@app.delete("/api/gastos/{gid}")
async def api_anular_gasto(gid: int):
    anular_gasto(gid); return {"ok": True}

@app.post("/api/gastos")
async def api_gasto(r: GastoReq):
    registrar_gasto(r.usuario_id, r.tienda_id, r.concepto, r.monto, r.origen)
    # Obtener nombre del usuario
    conn = get_connection()
    u = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    t = conn.execute("SELECT nombre FROM tiendas WHERE id=?", (r.tienda_id,)).fetchone() if r.tienda_id else None
    conn.close()
    cajero = u["nombre"] if u else "?"
    tienda_name = t["nombre"] if t else "General"
    from datetime import datetime
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    enviar_notificacion_email(
        f"💸 Gasto Registrado – ${r.monto:.2f}",
        f"GASTO REGISTRADO\n"
        f"Fecha: {ahora}\n"
        f"Cajero: {cajero}\n"
        f"Tienda: {tienda_name}\n"
        f"Concepto: {r.concepto}\n"
        f"Monto: ${r.monto:,.2f}\n"
        f"Origen: {r.origen}\n"
    )
    return {"ok": True}

# ── Ingresos ──
@app.get("/api/ingresos")
async def api_listar_ingresos(limit: int = 50, offset: int = 0):
    return listar_ingresos(limit=limit, offset=offset)

@app.delete("/api/ingresos/{iid}")
async def api_anular_ingreso(iid: int):
    anular_ingreso(iid); return {"ok": True}

@app.post("/api/ingresos")
async def api_ingreso(r: IngresoReq):
    registrar_ingreso(r.usuario_id, r.concepto, r.monto, r.metodo_pago)
    conn = get_connection()
    u = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    conn.close()
    cajero = u["nombre"] if u else "?"
    from datetime import datetime
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    enviar_notificacion_email(
        f"💰 Ingreso Registrado – ${r.monto:.2f}",
        f"INGRESO REGISTRADO\n"
        f"Fecha: {ahora}\n"
        f"Cajero: {cajero}\n"
        f"Concepto: {r.concepto}\n"
        f"Monto: ${r.monto:,.2f}\n"
        f"Método: {r.metodo_pago}\n"
    )
    return {"ok": True}

# ── Fondo de Apertura ──
@app.get("/api/fondo")
async def api_get_fondo():
    return {"fondo": get_fondo_apertura()}

@app.post("/api/fondo")
async def api_set_fondo(r: FondoReq):
    # Solo se puede abrir caja una vez al día
    if get_fondo_apertura() > 0:
        raise HTTPException(409, "La caja ya fue abierta hoy. Solo se puede abrir una vez al día.")
    set_fondo_apertura(r.monto)
    return {"ok": True}

# ── Corte ──
@app.post("/api/cortes")
async def api_cierre(r: CorteReq):
    registrar_corte(r.usuario_id, r.efectivo_real, fondo_caja=r.fondo_caja, desglose=r.desglose)
    return {"ok": True}

@app.post("/api/cortes/imprimir")
async def api_imprimir_corte(r: ImprimirCorteReq):
    resumen = obtener_resumen_dia()
    conn = get_connection()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    conn.close()
    cajero = row["nombre"] if row else "Admin"
    ok = imprimir_corte_caja(resumen, cajero)
    return {"impreso": ok}

@app.get("/api/report/corte")
async def api_resumen(): return obtener_resumen_dia()

@app.get("/api/report/semanal")
async def api_resumen_semanal(desde: str = None, hasta: str = None):
    return obtener_resumen_semana(desde, hasta)

@app.get("/api/estadisticas")
async def api_estadisticas(): return obtener_estadisticas()

@app.get("/api/estadisticas/estudio")
async def api_estadisticas_estudio(desde: str = None, hasta: str = None):
    return obtener_estadisticas_estudio(desde, hasta)

@app.get("/api/balance")
async def api_balance(): return obtener_balance_actual()

@app.post("/api/balance/ajustar")
async def api_ajustar_balance(r: dict):
    return ajustar_balance(float(r.get('caja', 0)), float(r.get('banco', 0)))

@app.post("/api/limpiar_semana")
async def api_limpiar_semana(r: dict):
    return limpiar_ingresos_gastos(r['fecha_inicio'], r['fecha_fin'])

@app.get("/api/nominas")
async def api_listar_nominas(limit: int = 50, offset: int = 0):
    return listar_nominas(limit=limit, offset=offset)

@app.post("/api/nominas")
async def api_registrar_nomina(r: dict):
    nomina = registrar_nomina(
        r['nombre_empleado'], float(r['monto']), r.get('concepto','Nómina'),
        r.get('metodo_pago','Efectivo'), r.get('usuario_id')
    )
    conn = __import__('modules.database', fromlist=['get_connection']).get_connection()
    u = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.get('usuario_id'),)).fetchone()
    conn.close()
    cajero = u['nombre'] if u else 'Sistema'
    pdf_path = generar_nomina_pdf(nomina, cajero)
    enviar_nomina_email(pdf_path, nomina, cajero)
    return {'ok': True, 'nomina': nomina}

@app.post("/api/pagos-tienda")
async def api_pago_tienda(r: PagoTiendaReq):
    registrar_pago_tienda(
        r.tienda_id, r.tienda_nombre, r.monto, r.metodo_pago,
        r.concepto, r.es_interno, r.semana_inicio, r.semana_fin,
        usuario_id=r.usuario_id
    )
    return {"ok": True}

@app.post("/api/corte")
async def api_corte(r: CorteReq):
    conn = get_connection()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    conn.close()
    cajero = row["nombre"] if row else "?"
    ventas_turno = obtener_ventas_turno()
    resumen = registrar_corte(r.usuario_id, r.efectivo_real, fondo_caja=r.fondo_caja, desglose=r.desglose)
    pdf_path = generar_corte_pdf(resumen, cajero, ventas_turno=ventas_turno)
    
    # Enviar el corte por correo automáticamente
    enviar_corte_email(
        pdf_path=pdf_path,
        resumen=resumen,
        cajero=cajero,
        callback_ok=lambda msg: print(f"Email enviado: {msg}"),
        callback_error=lambda err: print(f"Error al enviar email: {err}")
    )
    
    return {"resumen": resumen}

# ── Bundle / Promociones ──
@app.get("/api/bundle-components/{bid}")
async def api_get_bundle(bid: int): return obtener_bundle_components(bid)

@app.post("/api/bundle-components/{bid}")
async def api_add_bundle(bid: int, r: BundleComponentReq):
    agregar_bundle_component(bid, r.componente_id, r.cantidad, r.precio_asignado)
    return {"ok": True}

@app.delete("/api/bundle-components/{cid}")
async def api_del_bundle(cid: int):
    eliminar_bundle_component(cid)
    return {"ok": True}

# ── Ventas del día ──
@app.get("/api/ventas/hoy")
async def api_ventas_hoy(): return obtener_ventas_dia()

@app.put("/api/ventas/{vid}")
async def api_corregir_venta(vid: int, r: CorregirVentaReq):
    corregir_venta(vid, r.metodo_pago, r.monto_efectivo, r.monto_tarjeta)
    return {"ok": True}

@app.delete("/api/ventas/{vid}")
async def api_anular_venta(vid: int):
    anular_venta(vid)
    return {"ok": True}

@app.post("/api/ventas/{vid}/reimprimir")
async def api_reimprimir_ticket(vid: int):
    conn = get_connection()
    v = conn.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
    if not v:
        conn.close()
        raise HTTPException(404, "Venta no encontrada")
    items = conn.execute("""
        SELECT vd.*, COALESCE(t.nombre,'Sin Tienda') as tienda_nombre
        FROM venta_detalle vd
        LEFT JOIN tiendas t ON t.id = vd.tienda_id
        WHERE vd.venta_id = ?
    """, (vid,)).fetchall()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (v["usuario_id"],)).fetchone()
    mesa_row = conn.execute("SELECT numero FROM mesas WHERE id=?", (v["mesa_id"],)).fetchone() if v["mesa_id"] else None
    conn.close()
    cajero = row["nombre"] if row else "?"
    venta_data = {
        "folio": v["folio"],
        "total": v["total"],
        "metodo_pago": v["metodo_pago"],
        "monto_efectivo": v["monto_efectivo"],
        "monto_tarjeta": v["monto_tarjeta"],
        "efectivo_recibido": 0,
        "cambio": 0,
        "fecha": v["created_at"],
        "items": [dict(i) for i in items],
        "mesa": f"Mesa {mesa_row['numero']}" if mesa_row else None,
    }
    ok = imprimir_ticket(venta_data, cajero)
    return {"impreso": ok}

@app.post("/api/ventas/{vid}/reimprimir_comanda")
async def api_reimprimir_comanda(vid: int):
    conn = get_connection()
    v = conn.execute("SELECT * FROM ventas WHERE id=?", (vid,)).fetchone()
    if not v:
        conn.close()
        raise HTTPException(404, "Venta no encontrada")
    items = conn.execute("""
        SELECT vd.nombre_producto, vd.cantidad, vd.tienda_id
        FROM venta_detalle vd
        WHERE vd.venta_id = ? AND vd.tienda_id = 1
    """, (vid,)).fetchall()
    mesa_row = conn.execute("SELECT numero FROM mesas WHERE id=?", (v["mesa_id"],)).fetchone() if v["mesa_id"] else None
    conn.close()
    if not items:
        return {"impreso": False, "msg": "Sin items de barra"}
    label = f"Mesa {mesa_row['numero']}" if mesa_row else "VENTA DIRECTA"
    label += f" · {v['folio']}"
    ok = imprimir_comanda(label, [dict(i) for i in items])
    return {"impreso": ok}

# ── Notas Flotantes ──
import emoji

def remove_emojis(text: str) -> str:
    return emoji.replace_emoji(text, replace='')

@app.get("/api/notas")
async def api_get_notas():
    conn = get_connection()
    notas = conn.execute("SELECT * FROM notas").fetchall()
    conn.close()
    return [dict(n) for n in notas]

@app.post("/api/notas")
async def api_post_nota(r: NotaReq):
    conn = get_connection()
    cur = conn.cursor()
    texto_limpio = remove_emojis(r.texto)
    cur.execute("INSERT INTO notas (texto, pos_x, pos_y, color) VALUES (?,?,?,?)", (texto_limpio, r.pos_x, r.pos_y, r.color))
    conn.commit()
    nid = cur.lastrowid
    conn.close()
    return {"id": nid}

@app.put("/api/notas/{nid}")
async def api_put_nota(nid: int, r: NotaReq):
    conn = get_connection()
    texto_limpio = remove_emojis(r.texto)
    conn.execute("UPDATE notas SET texto=?, pos_x=?, pos_y=?, color=? WHERE id=?", (texto_limpio, r.pos_x, r.pos_y, r.color, nid))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/notas/{nid}")
async def api_delete_nota(nid: int):
    conn = get_connection()
    conn.execute("DELETE FROM notas WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return {"ok": True}

if __name__ == "__main__":
    print("\n  * Estudio Deco POS *")
    print("  http://localhost:8001\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)

