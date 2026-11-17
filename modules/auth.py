"""Sesiones, bloqueos y verificación de dispositivos para el login."""
import hashlib
import hmac
import math
import secrets
import time
from threading import RLock

from modules import database

MAX_INTENTOS = 5
BLOQUEO_SEG = 300
SESION_SEG = 12 * 3600
CODIGO_SEG = 600

_fallos = {}
_bloqueos = {}
_sesiones = {}
_retos = {}
# Los endpoints síncronos pueden atenderse en distintos hilos.
_lock = RLock()


def bloqueado(username) -> int:
    with _lock:
        restante = _bloqueos.get(username, 0) - time.time()
        if restante <= 0:
            _bloqueos.pop(username, None)
            return 0
        return math.ceil(restante)


def registrar_fallo(username):
    with _lock:
        if bloqueado(username):
            return
        intentos = _fallos.get(username, 0) + 1
        if intentos >= MAX_INTENTOS:
            _bloqueos[username] = time.time() + BLOQUEO_SEG
            _fallos.pop(username, None)
        else:
            _fallos[username] = intentos


def limpiar_fallos(username):
    with _lock:
        _fallos.pop(username, None)
        _bloqueos.pop(username, None)


def crear_sesion(username, role) -> str:
    with _lock:
        token = secrets.token_urlsafe(32)
        _sesiones[token] = {"username": username, "role": role, "expira": time.time() + SESION_SEG}
        return token


def sesion_valida(token) -> bool:
    with _lock:
        sesion = _sesiones.get(token)
        if not sesion:
            return False
        if sesion["expira"] <= time.time():
            _sesiones.pop(token, None)
            return False
        sesion["expira"] = time.time() + SESION_SEG  # caduca por inactividad: cada uso la renueva
        return True


def cerrar_sesion(token):
    with _lock:
        _sesiones.pop(token, None)


def crear_reto(username, role) -> tuple[str, str]:
    with _lock:
        for reto_id, reto in list(_retos.items()):
            if reto["username"] == username:
                del _retos[reto_id]
        reto_id = secrets.token_urlsafe(32)
        codigo = f"{secrets.randbelow(10000):04d}"
        _retos[reto_id] = {"username": username, "role": role,
                          "codigo_hash": hashlib.sha256(codigo.encode()).hexdigest(),
                          "expira": time.time() + CODIGO_SEG, "intentos": 0}
        return reto_id, codigo


def bloqueo_reto(reto_id) -> int:
    """Consulta el bloqueo del usuario asociado al reto sin aceptar otro usuario."""
    with _lock:
        reto = _retos.get(reto_id)
        return bloqueado(reto["username"]) if reto else 0


def verificar_reto(reto_id, codigo) -> tuple[str, str] | None:
    with _lock:
        reto = _retos.get(reto_id)
        if not reto:
            return None
        if reto["expira"] <= time.time():
            del _retos[reto_id]
            return None
        username = reto["username"]
        if bloqueado(username):
            return None
        codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
        if not hmac.compare_digest(reto["codigo_hash"], codigo_hash):
            reto["intentos"] += 1
            registrar_fallo(username)
            if reto["intentos"] >= MAX_INTENTOS:
                del _retos[reto_id]
            return None
        del _retos[reto_id]
        limpiar_fallos(username)
        return username, reto["role"]


def nuevo_dispositivo(username) -> str:
    token = secrets.token_urlsafe(32)
    database.registrar_dispositivo(username, hashlib.sha256(token.encode()).hexdigest())
    return token


def dispositivo_confiable(username, device_token) -> bool:
    if not device_token:
        return False
    return database.existe_dispositivo(username, hashlib.sha256(device_token.encode()).hexdigest())
