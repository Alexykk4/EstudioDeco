"""Pruebas de la lógica de dinero: cobro, anulación, balance, corte y pagos.
Ejecutar con: python -m unittest discover -s tests
Usan una BD en memoria creada con init_db(); nunca tocan pos_estudio_deco.db."""
import sqlite3
import json
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

with patch('logging.basicConfig'):
    from modules import database as db


class MemoryConnection(sqlite3.Connection):
    def close(self):
        # Todas las funciones de negocio comparten esta BD aislada durante la prueba.
        pass


class DineroBase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:', factory=MemoryConnection)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.addCleanup(sqlite3.Connection.close, self.conn)
        p = patch.object(db, 'get_connection', return_value=self.conn)
        p.start()
        self.addCleanup(p.stop)
        db.init_db()
        c = self.conn
        self.uid = c.execute("INSERT INTO usuarios(nombre,perfil,nip) VALUES ('Prueba','Administrador','x')").lastrowid
        self.tienda = c.execute("SELECT id FROM tiendas WHERE nombre NOT LIKE '%Estaci%' ORDER BY id LIMIT 1").fetchone()["id"]
        self.prod = c.execute(
            "INSERT INTO productos(tienda_id,nombre,precio,costo,stock_local,stock_minimo) VALUES (?,?,?,?,?,0)",
            (self.tienda, 'Taza', 100.0, 40.0, 10)).lastrowid
        c.commit()

    def item(self, pid=None, cantidad=1, precio=100.0, nombre='Taza'):
        return {"producto_id": pid or self.prod, "tienda_id": self.tienda, "nombre": nombre,
                "cantidad": cantidad, "precio_unitario": precio, "es_precio_abierto": False}

    def stock(self, pid):
        return self.conn.execute("SELECT stock_local FROM productos WHERE id=?", (pid,)).fetchone()["stock_local"]


class CobroYAnulacion(DineroBase):
    def test_tarjeta_crea_comision_y_anular_la_anula(self):
        v = db.registrar_venta(self.uid, 'Tarjeta', [self.item()])
        com = self.conn.execute("SELECT monto, anulado FROM gastos WHERE concepto LIKE ?", (f"%{v['folio']}",)).fetchone()
        self.assertEqual(com["monto"], 4.0)
        db.anular_venta(v["venta_id"])
        com = self.conn.execute("SELECT anulado FROM gastos WHERE concepto LIKE ?", (f"%{v['folio']}",)).fetchone()
        self.assertEqual(com["anulado"], 1)

    def test_anular_dos_veces_devuelve_stock_una_sola_vez(self):
        v = db.registrar_venta(self.uid, 'Efectivo', [self.item(cantidad=2)])
        self.assertEqual(self.stock(self.prod), 8)
        db.anular_venta(v["venta_id"])
        db.anular_venta(v["venta_id"])
        self.assertEqual(self.stock(self.prod), 10)

    def test_combo_sin_stock_de_componente_se_bloquea_igual_que_suelto(self):
        c = self.conn
        comp = c.execute("INSERT INTO productos(tienda_id,nombre,precio,costo,stock_local,stock_minimo) VALUES (?,?,?,?,0,0)",
                         (self.tienda, 'Pincel', 20.0, 5.0)).lastrowid
        combo = c.execute("INSERT INTO productos(tienda_id,nombre,precio,costo,stock_local,stock_minimo,es_bundle) VALUES (?,?,?,?,99,0,1)",
                          (self.tienda, 'Kit', 50.0, 0.0)).lastrowid
        c.execute("INSERT INTO bundle_components(bundle_producto_id,componente_producto_id,cantidad,precio_asignado) VALUES (?,?,1,50)", (combo, comp))
        c.commit()
        with self.assertRaises(ValueError):
            db.registrar_venta(self.uid, 'Efectivo', [self.item(pid=comp, precio=20.0, nombre='Pincel')])
        with self.assertRaises(ValueError):
            db.registrar_venta(self.uid, 'Efectivo', [self.item(pid=combo, precio=50.0, nombre='Kit')])
        self.assertEqual(self.stock(comp), 0)
        self.assertEqual(c.execute("SELECT COUNT(*) n FROM ventas").fetchone()["n"], 0)

    def test_mixto_que_no_cuadra_se_rechaza(self):
        with self.assertRaises(ValueError):
            db.registrar_venta(self.uid, 'Mixto', [self.item()], monto_efectivo=100, monto_tarjeta=100)
        self.assertEqual(self.stock(self.prod), 10)

    def test_mixto_que_cuadra_con_propina_pasa(self):
        propina = {"producto_id": None, "tienda_id": self.tienda, "nombre": "Propina (10%)",
                   "cantidad": 1, "precio_unitario": 10.0, "es_precio_abierto": True}
        v = db.registrar_venta(self.uid, 'Mixto', [self.item(), propina], monto_efectivo=60, monto_tarjeta=50)
        self.assertEqual(v["total"], 110.0)

    def test_mesa_mixto_que_no_cuadra_se_rechaza_y_la_orden_sigue_abierta(self):
        mesa = self.conn.execute("SELECT id FROM mesas ORDER BY id LIMIT 1").fetchone()["id"]
        oid = db.abrir_mesa(mesa, self.uid)
        db.agregar_item_orden(oid, self.prod, self.tienda, 'Taza', 1, 100.0)
        with self.assertRaises(ValueError):
            db.cerrar_mesa(oid, self.uid, 'Mixto', monto_efectivo=10, monto_tarjeta=10)
        estado = self.conn.execute("SELECT estado FROM ordenes WHERE id=?", (oid,)).fetchone()["estado"]
        self.assertEqual(estado, 'abierta')

    def test_corregir_a_mixto_que_no_cuadra_se_rechaza(self):
        v = db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        with self.assertRaises(ValueError):
            db.corregir_venta(v["venta_id"], 'Mixto', 100, 100)

    def test_anular_devuelve_insumos_de_bebida(self):
        c = self.conn
        ing = c.execute("INSERT INTO inv_ingredientes(nombre,unidad,stock_actual) VALUES ('Leche prueba','ml',1000)").lastrowid
        rec = c.execute("INSERT INTO inv_recetas(nombre) VALUES ('BEBIDA PRUEBA')").lastrowid
        c.execute("INSERT INTO inv_receta_ingredientes(receta_id,ingrediente_id,cantidad) VALUES (?,?,200)", (rec, ing))
        bebida = c.execute("INSERT INTO productos(tienda_id,nombre,precio,costo,stock_local,stock_minimo,receta_key,es_precio_abierto) VALUES (?,?,?,?,0,0,'BEBIDA PRUEBA',1)",
                           (self.tienda, 'Bebida prueba', 60.0, 0.0)).lastrowid
        c.commit()
        it = self.item(pid=bebida, precio=60.0, nombre='Bebida prueba (Frío)')
        it["es_precio_abierto"] = True
        v = db.registrar_venta(self.uid, 'Efectivo', [it])
        db.descontar_ingredientes_bebida('BEBIDA PRUEBA')  # lo hace server.py tras cobrar
        self.assertEqual(c.execute("SELECT stock_actual FROM inv_ingredientes WHERE id=?", (ing,)).fetchone()[0], 800)
        db.anular_venta(v["venta_id"])
        self.assertEqual(c.execute("SELECT stock_actual FROM inv_ingredientes WHERE id=?", (ing,)).fetchone()[0], 1000)


class BalanceYCorte(DineroBase):
    def test_ajuste_con_gasto_anulado_deja_el_balance_igual_a_lo_contado(self):
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        db.registrar_gasto(self.uid, None, 'Error', 200, 'Caja')
        gid = self.conn.execute("SELECT id FROM gastos WHERE concepto='Error'").fetchone()["id"]
        db.anular_gasto(gid)
        db.ajustar_balance(5000, 0)
        self.assertEqual(db.obtener_balance_actual()["en_caja"], 5000)

    def test_balance_es_acumulado_y_no_se_reinicia_con_el_corte(self):
        with patch.object(db, "datetime") as dt:  # el ajuste ocurrió antes que lo que sigue
            dt.now.return_value = datetime.now() - timedelta(minutes=1)
            db.ajustar_balance(5000, 300)
        db.registrar_corte(self.uid, 0)  # nuevo turno
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        bal = db.obtener_balance_actual()
        self.assertEqual(bal["en_caja"], 5100)
        self.assertEqual(bal["en_banco"], 300)
        self.assertEqual(bal["total"], 5400)

    def test_ajuste_viejo_numerico_se_suma_al_turno(self):
        self.conn.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES ('ajuste_caja','1000')")
        self.conn.commit()
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        self.assertEqual(db.obtener_balance_actual()["en_caja"], 1100)

    def test_ajuste_json_previo_sigue_valiendo_tras_el_corte(self):
        # Formato guardado por la versión anterior: monto = diferencia, desde = inicio de turno.
        self.conn.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES ('ajuste_caja',?)",
                          (json.dumps({"monto": 800, "desde": "2000-01-01 00:00:00"}),))
        self.conn.commit()
        db.registrar_corte(self.uid, 0)
        self.assertEqual(db.obtener_balance_actual()["en_caja"], 800)

    def test_corte_despues_de_medianoche_incluye_el_turno_completo(self):
        c = self.conn
        ayer = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO cortes_caja(usuario_id,fecha,total_ventas,total_gastos,efectivo_esperado,efectivo_real,diferencia,created_at) "
                  "VALUES (?,?,0,0,0,0,0,?)", (self.uid, ayer, f"{ayer} 09:00:00"))
        c.execute("INSERT INTO ventas(folio,usuario_id,metodo_pago,monto_efectivo,subtotal,total,created_at) "
                  "VALUES ('T-1',?,'Efectivo',300,300,300,?)", (self.uid, f"{ayer} 23:30:00"))
        c.commit()
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        r = db.obtener_resumen_dia()
        self.assertEqual(r["total_ventas"], 400)
        self.assertEqual(r["efectivo_esperado"], 400)

    def test_resumen_con_fecha_explicita_no_cambia(self):
        c = self.conn
        ayer = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO ventas(folio,usuario_id,metodo_pago,monto_efectivo,subtotal,total,created_at) "
                  "VALUES ('T-2',?,'Efectivo',300,300,300,?)", (self.uid, f"{ayer} 12:00:00"))
        c.commit()
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        self.assertEqual(db.obtener_resumen_dia(ayer)["total_ventas"], 300)


class PagosTienda(DineroBase):
    def semana(self):
        hoy = date.today()
        ini = hoy - timedelta(days=hoy.weekday())
        return ini.strftime("%Y-%m-%d"), (ini + timedelta(days=6)).strftime("%Y-%m-%d")

    def test_pago_externo_nuevo_se_resta_una_vez(self):
        ini, fin = self.semana()
        db.registrar_pago_tienda(self.tienda, 'Externa', 300, 'Efectivo', 'Pago', False, ini, fin, self.uid)
        r = db.obtener_resumen_semana(ini, fin)
        self.assertEqual(r["balance_estudio_deco"], -300)

    def test_pago_externo_viejo_sin_gasto_se_resta_una_vez(self):
        ini, fin = self.semana()
        self.conn.execute("INSERT INTO pagos_tienda(tienda_id,tienda_nombre,monto,metodo_pago,concepto,es_interno,semana_inicio,semana_fin) "
                          "VALUES (?,?,200,'Efectivo','viejo',0,?,?)", (self.tienda, 'Externa', ini, fin))
        self.conn.commit()
        r = db.obtener_resumen_semana(ini, fin)
        self.assertEqual(r["balance_estudio_deco"], -200)

    def test_transferencia_interna_mueve_dinero_sin_perderlo(self):
        ini, fin = self.semana()
        est = self.conn.execute("SELECT id, nombre FROM tiendas WHERE nombre LIKE '%Estaci%' ORDER BY id LIMIT 1").fetchone()
        db.registrar_pago_tienda(est["id"], est["nombre"], 500, 'Efectivo', 'Fondo', True, ini, fin, self.uid)
        r = db.obtener_resumen_semana(ini, fin)
        self.assertEqual(r["balance_estacion_304"], 500)
        self.assertEqual(r["balance_estudio_deco"], -500)

    def test_pago_semanal_en_efectivo_no_descuadra_el_corte(self):
        ini, fin = self.semana()
        db.registrar_venta(self.uid, 'Efectivo', [self.item()])
        db.registrar_pago_tienda(self.tienda, 'Externa', 3048, 'Efectivo', f'Pago semanal {ini} a {fin}', False, ini, fin, self.uid)
        db.registrar_gasto(self.uid, None, 'domos', 30)  # gasto normal de caja: sí se resta
        r = db.obtener_resumen_dia()
        self.assertEqual(r["efectivo_esperado"], 70)
        self.assertEqual(r["tarjeta_esperado"], 0)
        self.assertEqual(db.obtener_balance_actual()["en_caja"], 100 - 3048 - 30)

    def test_pago_a_tienda_es_atomico(self):
        ini, fin = self.semana()
        # Usuario inexistente: el gasto falla por llave foránea; el pago no debe quedar guardado.
        with self.assertRaises(sqlite3.IntegrityError):
            db.registrar_pago_tienda(self.tienda, 'Externa', 300, 'Efectivo', 'Pago', False, ini, fin, 999999)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) n FROM pagos_tienda").fetchone()["n"], 0)


if __name__ == '__main__':
    unittest.main()
