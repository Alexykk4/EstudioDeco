"""
server.py — Estudio Deco POS v2
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uvicorn

from modules.database import (
    init_db, listar_tiendas, obtener_productos, validar_nip,
    registrar_venta, registrar_gasto, obtener_resumen_dia,
    registrar_corte, obtener_stock, listar_usuarios, crear_usuario,
    listar_mesas, abrir_mesa, agregar_item_orden,
    quitar_item_orden, cerrar_mesa, obtener_items_comanda, get_connection,
    obtener_ordenes_mesa, renombrar_orden, cancelar_orden_mesa,
    obtener_todos_los_productos, crear_producto, actualizar_producto, eliminar_producto,
    actualizar_item_orden, registrar_ingreso, set_fondo_apertura, get_fondo_apertura,
    obtener_ventas_dia, corregir_venta, anular_venta,
    obtener_bundle_components, agregar_bundle_component, eliminar_bundle_component,
)
from modules.printer import imprimir_ticket, imprimir_comanda, imprimir_corte_caja
from modules.pdf_report import generar_corte_pdf
from modules.sync_sheets import sync_worker

init_db(); sync_worker.start()
app = FastAPI(title="Estudio Deco POS", version="2.0")

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
    cantidad: int = 1
    precio_unitario: float
    es_precio_abierto: bool = False
class EditItemReq(BaseModel):
    nombre: str
    precio_unitario: float
class CerrarMesaReq(BaseModel):
    usuario_id: int
    metodo_pago: str
    monto_efectivo: float = 0.0
    monto_tarjeta: float = 0.0
    efectivo_recibido: float = 0.0

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
    monto: float
    origen: str = "Caja"
class CorteReq(BaseModel):
    usuario_id: int
    efectivo_real: float
    fondo_caja: float = 0.0
    desglose: dict = {}

class IngresoReq(BaseModel):
    usuario_id: int
    concepto: str = "Ingreso"
    monto: float
    metodo_pago: str = "Efectivo"

class FondoReq(BaseModel):
    monto: float

class ImprimirCorteReq(BaseModel):
    usuario_id: int

class CorregirVentaReq(BaseModel):
    metodo_pago: str
    monto_efectivo: float = 0.0
    monto_tarjeta: float = 0.0

class BundleComponentReq(BaseModel):
    componente_id: int
    cantidad: int = 1
    precio_asignado: float

class ProductReq(BaseModel):
    tienda_id: int
    nombre: str
    precio: float
    costo: float = 0.0
    stock_local: int
    stock_minimo: int
    codigo: str = ""
    es_precio_abierto: bool = False
    es_bundle: int = 0
    categoria_producto: str = ""

# ── Pages ──
@app.get("/")
async def root(): return FileResponse(str(STATIC / "index.html"))

# ── Auth ──
@app.post("/api/auth")
async def auth(r: NipReq):
    u = validar_nip(r.nip)
    if not u: raise HTTPException(401, "NIP incorrecto")
    return u

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
    pid = crear_producto(r.tienda_id, r.nombre, r.precio, r.costo, r.stock_local, r.stock_minimo, r.codigo, 1 if r.es_precio_abierto else 0, r.es_bundle, r.categoria_producto)
    return {"id": pid}

@app.put("/api/catalog/{pid}")
async def api_put_catalog(pid: int, r: ProductReq):
    actualizar_producto(pid, r.tienda_id, r.nombre, r.precio, r.costo, r.stock_local, r.stock_minimo, r.codigo, 1 if r.es_precio_abierto else 0, r.es_bundle, r.categoria_producto)
    return {"ok": True}

@app.delete("/api/catalog/{pid}")
async def api_del_catalog(pid: int):
    eliminar_producto(pid)
    return {"ok": True}

# ── MESAS / ORDENES ──
@app.get("/api/mesas")
async def api_mesas():
    # listar_mesas needs to show how many orders are open per mesa
    conn = get_connection()
    mesas_raw = conn.execute("SELECT * FROM mesas").fetchall()
    
    mesas = []
    for m in mesas_raw:
        m_dict = dict(m)
        ordenes = conn.execute("SELECT id, nombre_cliente FROM ordenes WHERE mesa_id=? AND estado='abierta'", (m["id"],)).fetchall()
        m_dict["ordenes"] = [dict(o) for o in ordenes]
        m_dict["num_items"] = 0 # To conform to older API if needed, or recalculate
        
        # Calculate totals if needed
        total_orden = 0
        num_items = 0
        for o in ordenes:
            items = conn.execute("SELECT cantidad, precio_unitario FROM orden_items WHERE orden_id=?", (o["id"],)).fetchall()
            for it in items:
                num_items += it["cantidad"]
                total_orden += it["cantidad"] * it["precio_unitario"]
        
        m_dict["total_orden"] = total_orden
        m_dict["num_items"] = num_items
        mesas.append(m_dict)
        
    conn.close()
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

@app.post("/api/ordenes/{oid}/cerrar")
async def api_cerrar(oid: int, r: CerrarMesaReq):
    # Obtener items de comanda ANTES de cerrar (items de barra no impresos)
    items_comanda = obtener_items_comanda(oid)

    venta = cerrar_mesa(oid, r.usuario_id, r.metodo_pago, r.monto_efectivo, r.monto_tarjeta, r.efectivo_recibido)
    if not venta: raise HTTPException(400, "No se pudo cerrar")

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
    impreso = imprimir_ticket(venta, cajero)
    # Imprimir comanda automática para items de barra (tienda_id=1)
    items_barra = [i for i in r["items"] if i.get("tienda_id") == 1]
    if items_barra:
        imprimir_comanda("VENTA DIRECTA", [{"nombre_producto": i["nombre"], "cantidad": i["cantidad"]} for i in items_barra])
    return {"venta": venta, "impreso": impreso, "cajero": cajero}

# ── Gastos ──
@app.post("/api/gastos")
async def api_gasto(r: GastoReq):
    registrar_gasto(r.usuario_id, r.tienda_id, r.concepto, r.monto, r.origen)
    return {"ok": True}

# ── Ingresos ──
@app.post("/api/ingresos")
async def api_ingreso(r: IngresoReq):
    registrar_ingreso(r.usuario_id, r.concepto, r.monto, r.metodo_pago)
    return {"ok": True}

# ── Fondo de Apertura ──
@app.get("/api/fondo")
async def api_get_fondo():
    return {"fondo": get_fondo_apertura()}

@app.post("/api/fondo")
async def api_set_fondo(r: FondoReq):
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
async def api_resumen_semanal():
    from datetime import date, timedelta
    conn = get_connection()
    dias = []
    total_semana = 0.0
    total_efectivo = 0.0
    total_tarjeta = 0.0
    total_gastos_semana = 0.0

    for i in range(6, -1, -1):
        fecha = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        rv = conn.execute(
            "SELECT COALESCE(SUM(total),0) as tv, COALESCE(SUM(monto_efectivo),0) as te, COALESCE(SUM(monto_tarjeta),0) as tt, COUNT(*) as nv FROM ventas WHERE DATE(created_at)=?",
            (fecha,)
        ).fetchone()
        rg = conn.execute(
            "SELECT COALESCE(SUM(monto),0) as tg FROM gastos WHERE DATE(created_at)=?",
            (fecha,)
        ).fetchone()
        por_tienda = conn.execute(
            "SELECT t.nombre, COALESCE(SUM(vd.subtotal),0) as subtotal FROM venta_detalle vd JOIN ventas v ON v.id=vd.venta_id JOIN tiendas t ON t.id=vd.tienda_id WHERE DATE(v.created_at)=? GROUP BY t.nombre",
            (fecha,)
        ).fetchall()
        total_semana += rv["tv"]
        total_efectivo += rv["te"]
        total_tarjeta += rv["tt"]
        total_gastos_semana += rg["tg"]
        dias.append({
            "fecha": fecha,
            "total_ventas": rv["tv"],
            "num_ventas": rv["nv"],
            "efectivo": rv["te"],
            "tarjeta": rv["tt"],
            "gastos": rg["tg"],
            "por_tienda": [{"tienda": r["nombre"], "total": r["subtotal"]} for r in por_tienda],
        })

    conn.close()
    return {
        "dias": dias,
        "total_semana": total_semana,
        "total_efectivo": total_semana and total_efectivo,
        "total_tarjeta": total_semana and total_tarjeta,
        "total_gastos": total_gastos_semana,
        "utilidad": total_semana - total_gastos_semana,
    }

@app.post("/api/corte")
async def api_corte(r: CorteReq):
    conn = get_connection()
    row = conn.execute("SELECT nombre FROM usuarios WHERE id=?", (r.usuario_id,)).fetchone()
    conn.close()
    cajero = row["nombre"] if row else "?"
    resumen = registrar_corte(r.usuario_id, r.efectivo_real, fondo_caja=r.fondo_caja, desglose=r.desglose)
    generar_corte_pdf(resumen, cajero)
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

if __name__ == "__main__":
    print("\n  * Estudio Deco POS *")
    print("  http://localhost:8001\n")
    uvicorn.run(app, host="0.0.0.0", port=8001)

