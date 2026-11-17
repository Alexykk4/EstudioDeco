"""Pruebas de login sin servidor, correo real ni acceso a la BD del negocio."""
import ast
import asyncio
import hashlib
import hmac
import tempfile
import unittest
from email import message_from_string
from email.header import decode_header, make_header
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

with patch('logging.basicConfig'):
    from modules import auth, database as db, email_sender

ROOT = Path(__file__).resolve().parents[1]
# Cargar los endpoints reales sin iniciar la BD del negocio ni Sheets.
tree = ast.parse((ROOT / 'server.py').read_text(encoding='utf-8'))
nombres = {'LoginReq', 'VerificarReq', '_hash_pw', 'login', 'verificar_login', 'logout', 'no_cache_static'}
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name in nombres]
rutas = dict(app=FastAPI(), BaseModel=BaseModel, Header=Header, HTTPException=HTTPException,
             JSONResponse=JSONResponse, hashlib=hashlib, hmac=hmac, autenticacion=auth,
             enviar_codigo_login=Mock(return_value=True),
             SYSTEM_USERS={'prueba': {'password_hash': hashlib.sha256(b'clave').hexdigest(), 'role': 'deco'}})
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'server.py', 'exec'), rutas)


class EstadoAuth(unittest.TestCase):
    def setUp(self):
        for nombre in ('_fallos', '_bloqueos', '_sesiones', '_retos'):
            parche = patch.object(auth, nombre, {})
            parche.start()
            self.addCleanup(parche.stop)
        parche = patch('modules.auth.time.time', return_value=1700000000.0)
        self.reloj = parche.start()
        self.addCleanup(parche.stop)


class AuthTests(EstadoAuth):
    def test_cinco_fallos_bloquean_y_el_contador_se_reinicia(self):
        for _ in range(auth.MAX_INTENTOS):
            auth.registrar_fallo('prueba')
        self.assertEqual(auth.bloqueado('prueba'), auth.BLOQUEO_SEG)
        self.assertEqual(auth.bloqueado('otro'), 0)
        self.reloj.return_value += 299.5
        self.assertEqual(auth.bloqueado('prueba'), 1)
        self.reloj.return_value += 1.5
        self.assertEqual(auth.bloqueado('prueba'), 0)
        for _ in range(auth.MAX_INTENTOS - 1):
            auth.registrar_fallo('prueba')
        self.assertEqual(auth.bloqueado('prueba'), 0)
        auth.registrar_fallo('prueba')
        self.assertGreater(auth.bloqueado('prueba'), 0)

    def test_limpiar_fallos_reinicia_intentos_y_bloqueo(self):
        for _ in range(auth.MAX_INTENTOS):
            auth.registrar_fallo('prueba')
        auth.limpiar_fallos('prueba')
        self.assertEqual(auth.bloqueado('prueba'), 0)
        for _ in range(auth.MAX_INTENTOS - 1):
            auth.registrar_fallo('prueba')
        auth.limpiar_fallos('prueba')
        auth.registrar_fallo('prueba')
        self.assertEqual(auth.bloqueado('prueba'), 0)

    def test_sesion_expira_y_se_borra(self):
        token = auth.crear_sesion('prueba', 'deco')
        self.assertTrue(auth.sesion_valida(token))
        self.assertFalse(auth.sesion_valida(None))
        self.assertFalse(auth.sesion_valida('falso'))
        self.reloj.return_value += auth.SESION_SEG - 1
        self.assertTrue(auth.sesion_valida(token))
        self.reloj.return_value += 1
        self.assertFalse(auth.sesion_valida(token))
        self.assertNotIn(token, auth._sesiones)

    def test_cerrar_sesion_la_invalida(self):
        token = auth.crear_sesion('prueba', 'deco')
        auth.cerrar_sesion(token)
        auth.cerrar_sesion(None)
        self.assertFalse(auth.sesion_valida(token))

    def test_reto_correcto_es_de_un_solo_uso_y_limpia_fallos(self):
        for _ in range(auth.MAX_INTENTOS - 1):
            auth.registrar_fallo('prueba')
        with patch('modules.auth.secrets.randbelow', return_value=7):
            reto, codigo = auth.crear_reto('prueba', 'deco')
        self.assertEqual(codigo, '0007')
        self.assertEqual(auth._retos[reto]['codigo_hash'], hashlib.sha256(codigo.encode()).hexdigest())
        self.assertNotIn(codigo, auth._retos[reto].values())
        self.assertEqual(auth.verificar_reto(reto, codigo), ('prueba', 'deco'))
        self.assertIsNone(auth.verificar_reto(reto, codigo))
        auth.registrar_fallo('prueba')
        self.assertEqual(auth.bloqueado('prueba'), 0)

    def test_cinco_codigos_incorrectos_borran_reto_y_bloquean(self):
        reto, codigo = auth.crear_reto('prueba', 'deco')
        for _ in range(auth.MAX_INTENTOS):
            self.assertIsNone(auth.verificar_reto(reto, 'incorrecto'))
        self.assertNotIn(reto, auth._retos)
        self.assertGreater(auth.bloqueado('prueba'), 0)
        self.reloj.return_value += auth.BLOQUEO_SEG + 1
        self.assertIsNone(auth.verificar_reto(reto, codigo))

    def test_reto_expirado_se_borra(self):
        reto, codigo = auth.crear_reto('prueba', 'deco')
        self.reloj.return_value += auth.CODIGO_SEG
        self.assertIsNone(auth.verificar_reto(reto, codigo))
        self.assertNotIn(reto, auth._retos)
        self.assertIsNone(auth.verificar_reto('inexistente', codigo))

    def test_nuevo_reto_reemplaza_solo_el_del_mismo_usuario(self):
        anterior, codigo_anterior = auth.crear_reto('prueba', 'deco')
        otro, codigo_otro = auth.crear_reto('otro', 'estacion')
        nuevo, codigo = auth.crear_reto('prueba', 'deco')
        self.assertIsNone(auth.verificar_reto(anterior, codigo_anterior))
        self.assertEqual(auth.verificar_reto(nuevo, codigo), ('prueba', 'deco'))
        self.assertEqual(auth.verificar_reto(otro, codigo_otro), ('otro', 'estacion'))

    def test_fallos_de_password_y_codigo_comparten_bloqueo(self):
        for _ in range(auth.MAX_INTENTOS - 1):
            auth.registrar_fallo('prueba')
        reto, codigo = auth.crear_reto('prueba', 'deco')
        self.assertIsNone(auth.verificar_reto(reto, 'incorrecto'))
        self.assertGreater(auth.bloqueo_reto(reto), 0)
        self.assertIsNone(auth.verificar_reto(reto, codigo))
        self.reloj.return_value += auth.BLOQUEO_SEG + 1
        self.assertEqual(auth.verificar_reto(reto, codigo), ('prueba', 'deco'))


class DispositivosYLoginTests(EstadoAuth):
    def setUp(self):
        super().setUp()
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        parche = patch.object(db, 'DB_PATH', Path(temporal.name) / 'auth.db')
        parche.start()
        self.addCleanup(parche.stop)
        db.init_db()
        self.correo = rutas['enviar_codigo_login']
        self.correo.reset_mock(return_value=True, side_effect=True)
        self.correo.return_value = True

    def login(self, **cambios):
        datos = dict(username='prueba', password='clave')
        datos.update(cambios)
        return rutas['login'](rutas['LoginReq'](**datos))

    def verificar(self, reto, codigo):
        return rutas['verificar_login'](rutas['VerificarReq'](reto=reto, codigo=codigo))

    def test_dispositivo_persistido_solo_como_hash_y_ligado_al_usuario(self):
        token = auth.nuevo_dispositivo('prueba')
        self.assertTrue(auth.dispositivo_confiable('prueba', token))
        self.assertFalse(auth.dispositivo_confiable('otro', token))
        self.assertFalse(auth.dispositivo_confiable('prueba', 'falso'))
        self.assertFalse(auth.dispositivo_confiable('prueba', None))
        self.assertFalse(auth.dispositivo_confiable('prueba', ''))
        conn = db.get_connection()
        try:
            fila = conn.execute('SELECT * FROM dispositivos_confiables').fetchone()
            self.assertEqual(fila['token_hash'], hashlib.sha256(token.encode()).hexdigest())
            self.assertNotIn(token, tuple(fila))
        finally:
            conn.close()
        db.init_db()
        self.assertTrue(auth.dispositivo_confiable('prueba', token))

    def test_login_verificacion_logout_y_reingreso_con_dispositivo(self):
        respuesta = self.login()
        self.assertTrue(respuesta['verificar'])
        self.assertNotIn('token', respuesta)
        codigo, username = self.correo.call_args.args
        self.assertEqual(username, 'prueba')
        sesion = self.verificar(respuesta['reto'], codigo)
        self.assertTrue(auth.sesion_valida(sesion['token']))
        self.assertEqual((sesion['username'], sesion['role']), ('prueba', 'deco'))
        self.assertTrue(auth.dispositivo_confiable('prueba', sesion['device']))
        asyncio.run(rutas['logout'](sesion['token']))
        self.assertFalse(auth.sesion_valida(sesion['token']))
        self.correo.reset_mock()
        regreso = self.login(device=sesion['device'])
        self.assertTrue(auth.sesion_valida(regreso['token']))
        self.assertNotIn('verificar', regreso)
        self.correo.assert_not_called()

    def test_login_bloqueado_devuelve_429_incluso_con_password_correcto(self):
        for _ in range(auth.MAX_INTENTOS):
            with self.assertRaises(HTTPException) as error:
                self.login(password='incorrecta')
            self.assertEqual(error.exception.status_code, 401)
        with self.assertRaises(HTTPException) as error:
            self.login()
        self.assertEqual(error.exception.status_code, 429)
        self.assertEqual(error.exception.detail, 'Demasiados intentos. Espera 5 min.')
        self.correo.assert_not_called()

    def test_usuario_inexistente_y_password_malo_con_dispositivo_fallan(self):
        token = auth.nuevo_dispositivo('prueba')
        for cambios in ({'username': 'inexistente'}, {'password': 'incorrecta', 'device': token}):
            with self.assertRaises(HTTPException) as error:
                self.login(**cambios)
            self.assertEqual(error.exception.status_code, 401)
            self.assertEqual(error.exception.detail, 'Usuario o contraseña incorrectos')
        self.correo.assert_not_called()

    def test_error_de_correo_devuelve_503_sin_sesion(self):
        self.correo.return_value = False
        with self.assertRaises(HTTPException) as error:
            self.login()
        self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(error.exception.detail, 'No se pudo enviar el código por correo. Revisa la configuración de email.')
        self.assertFalse(auth._sesiones)

    def test_verificacion_no_limpia_fallos_hasta_acertar_y_respeta_429(self):
        for _ in range(auth.MAX_INTENTOS - 1):
            auth.registrar_fallo('prueba')
        respuesta = self.login()
        with self.assertRaises(HTTPException) as error:
            self.verificar(respuesta['reto'], 'incorrecto')
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(error.exception.detail, 'Código incorrecto o vencido')
        codigo = self.correo.call_args.args[0]
        with self.assertRaises(HTTPException) as error:
            self.verificar(respuesta['reto'], codigo)
        self.assertEqual(error.exception.status_code, 429)
        self.assertFalse(auth._sesiones)

    def test_middleware_exenta_login_y_rechaza_sesion_vencida(self):
        siguiente = AsyncMock(return_value=JSONResponse({'ok': True}))
        for ruta in ('/api/login', '/api/login/verificar'):
            request = SimpleNamespace(url=SimpleNamespace(path=ruta), headers={})
            self.assertEqual(asyncio.run(rutas['no_cache_static'](request, siguiente)).status_code, 200)
        token = auth.crear_sesion('prueba', 'deco')
        request = SimpleNamespace(url=SimpleNamespace(path='/api/tiendas'), headers={'X-Auth-Token': token})
        self.assertEqual(asyncio.run(rutas['no_cache_static'](request, siguiente)).status_code, 200)
        self.reloj.return_value += auth.SESION_SEG
        siguiente.reset_mock()
        self.assertEqual(asyncio.run(rutas['no_cache_static'](request, siguiente)).status_code, 401)
        siguiente.assert_not_called()


class EmailLoginTests(unittest.TestCase):
    def test_sin_credenciales_devuelve_false_sin_enviar(self):
        for config in ({}, {'email_from': 'prueba@example.com'}, {'email_password': 'clave'}):
            with self.subTest(config=config), patch.object(db, 'get_email_config', return_value=config), \
                    patch.object(email_sender.smtplib, 'SMTP_SSL') as smtp, patch('builtins.print') as imprimir:
                self.assertFalse(email_sender.enviar_codigo_login('0007', 'prueba'))
                smtp.assert_not_called()
                self.assertNotIn('0007', str(imprimir.call_args_list))

    def test_envio_sincrono_y_destino_configurado_o_fallback(self):
        for destino in ('negocio@example.com', ''):
            config = dict(email_from='prueba@example.com', email_password='clave', email_destino=destino)
            with patch.object(db, 'get_email_config', return_value=config), \
                    patch.object(email_sender.smtplib, 'SMTP_SSL') as smtp, patch('builtins.print') as imprimir:
                self.assertTrue(email_sender.enviar_codigo_login('0007', 'prueba'))
                smtp.assert_called_once_with('smtp.gmail.com', 465)
                servidor = smtp.return_value.__enter__.return_value
                servidor.login.assert_called_once_with('prueba@example.com', 'clave')
                remitente, receptor, mensaje = servidor.sendmail.call_args.args
                self.assertEqual(remitente, 'prueba@example.com')
                self.assertEqual(receptor, destino or 'estudiodecomx@gmail.com')
                mensaje = message_from_string(mensaje)
                self.assertEqual(str(make_header(decode_header(mensaje['Subject']))), 'Código de acceso Estudio Deco: 0007')
                cuerpo = mensaje.get_payload(0).get_payload(decode=True).decode('utf-8')
                for texto in ('0007', 'prueba', 'Fecha y hora:', '10 minutos', 'Si no fuiste tú, cambia la contraseña'):
                    self.assertIn(texto, cuerpo)
                imprimir.assert_not_called()

    def test_excepcion_devuelve_false_sin_imprimir_codigo(self):
        with patch.object(db, 'get_email_config', side_effect=RuntimeError('error con 0007')), \
                patch('builtins.print') as imprimir:
            self.assertFalse(email_sender.enviar_codigo_login('0007', 'prueba'))
            imprimir.assert_called_once()
            self.assertNotIn('0007', str(imprimir.call_args))


if __name__ == '__main__':
    unittest.main()
