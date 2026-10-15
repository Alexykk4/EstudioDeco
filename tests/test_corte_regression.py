"""Regresión del corte: ejecutar con python -m unittest discover -s tests -p test_corte_regression.py."""
import ast
import asyncio
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI
from pydantic import BaseModel, Field, ValidationError

with patch('logging.basicConfig'):
    from modules import database as db
from modules import pdf_report

ROOT = Path(__file__).resolve().parents[1]
# Cargar el modelo y endpoint reales sin ejecutar init_db ni arrancar Sheets.
tree = ast.parse((ROOT / 'server.py').read_text(encoding='utf-8'))
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.AsyncFunctionDef))
         and n.name in ('CorteReq', 'api_corte')]
namespace = dict(app=FastAPI(), BaseModel=BaseModel, Field=Field,
                 get_connection=lambda: db.get_connection(),
                 registrar_corte=db.registrar_corte,
                 obtener_ventas_turno=db.obtener_ventas_turno,
                 generar_corte_pdf=pdf_report.generar_corte_pdf,
                 enviar_corte_email=Mock())
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'server.py', 'exec'), namespace)
CorteReq = namespace['CorteReq']


class MemoryConnection(sqlite3.Connection):
    def close(self):
        # Las funciones de negocio comparten esta DB aislada durante cada prueba.
        pass


class CorteRegressionTests(unittest.TestCase):
    def test_negative_net_is_valid(self):
        corte = CorteReq(usuario_id=1, efectivo_real=-50, fondo_caja=1000)
        self.assertEqual(corte.efectivo_real, -50)

    def test_negative_fund_is_rejected(self):
        with self.assertRaises(ValidationError):
            CorteReq(usuario_id=1, efectivo_real=-50, fondo_caja=-1000)

    def test_nonfinite_amounts_are_rejected(self):
        for field in ('efectivo_real', 'fondo_caja'):
            for value in (float('nan'), float('inf'), -float('inf')):
                with self.subTest(field=field, value=value):
                    data = dict(usuario_id=1, efectivo_real=0, fondo_caja=1000)
                    data[field] = value
                    with self.assertRaises(ValidationError):
                        CorteReq(**data)

    def test_cash_expense_cut_is_saved_with_zero_difference_and_pdf(self):
        conn = sqlite3.connect(':memory:', factory=MemoryConnection)
        conn.row_factory = sqlite3.Row
        self.addCleanup(sqlite3.Connection.close, conn)
        conn.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        for table, column in [('ventas', 'cancelada'), ('gastos', 'anulado'), ('ingresos', 'anulado')]:
            db._asegurar_columna(conn, table, column, 'INTEGER DEFAULT 0')
        uid = conn.execute("INSERT INTO usuarios(nombre,perfil,nip) VALUES ('Prueba','Administrador','prueba')").lastrowid
        conn.execute("INSERT INTO gastos(usuario_id,categoria,concepto,monto,origen) VALUES (?,'General','Basura',50,'Caja')", (uid,))
        conn.commit()
        request = CorteReq(usuario_id=uid, efectivo_real=-50, fondo_caja=1000,
                           desglose={'B500': 1, 'B200': 2, 'B50': 1})
        pdfs = []
        original_output = pdf_report.CortePDF.output
        def output_in_memory(pdf, *args, **kwargs):
            pdfs.append(bytes(original_output(pdf)))
        mail = namespace['enviar_corte_email']
        mail.reset_mock()
        with patch.object(db, 'get_connection', return_value=conn), \
                patch('pathlib.Path.mkdir'), \
                patch.object(pdf_report.CortePDF, 'output', output_in_memory), \
                patch('os.startfile', create=True):
            response = asyncio.run(namespace['api_corte'](request))
        summary = response['resumen']
        self.assertEqual(summary['efectivo_esperado'], -50)
        self.assertEqual(summary['efectivo_real'], -50)
        self.assertEqual(summary['diferencia'], 0)
        rows = conn.execute('SELECT * FROM cortes_caja').fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['fondo_caja'], 1000)
        self.assertEqual(rows[0]['efectivo_real'], -50)
        self.assertEqual(rows[0]['diferencia'], 0)
        self.assertEqual(len(pdfs), 1)
        self.assertTrue(pdfs[0].startswith(b'%PDF-'))
        mail.assert_called_once()


if __name__ == '__main__':
    unittest.main()
