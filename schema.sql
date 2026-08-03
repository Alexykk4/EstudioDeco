-- ============================================================
-- Estudio Deco POS v2 — Sistema de Mesas
-- ============================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    perfil     TEXT NOT NULL CHECK (perfil IN ('Administrador','Cajero','Invitado')),
    nip        TEXT NOT NULL,
    activo     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS tiendas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL UNIQUE,
    categoria      TEXT NOT NULL CHECK (categoria IN ('Barra','Deco')),
    precio_abierto INTEGER NOT NULL DEFAULT 0,
    es_barra       INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO tiendas (nombre, categoria, precio_abierto, es_barra) VALUES
    ('Estación 304',  'Barra', 0, 1),
    ('Kokoro',       'Deco',  0, 0),
    ('Mack&M',       'Deco',  0, 0),
    ('Acuario',      'Deco',  0, 0),
    ('Estudio Deco', 'Deco',  0, 0),
    ('Sabro Dulce',   'Deco',  0, 0),
    ('Promociones',  'Deco',  0, 0);

CREATE TABLE IF NOT EXISTS productos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tienda_id     INTEGER NOT NULL,
    codigo        TEXT DEFAULT '',
    nombre        TEXT NOT NULL,
    precio        REAL NOT NULL,
    costo         REAL NOT NULL DEFAULT 0.0,
    stock_local   INTEGER NOT NULL DEFAULT 0,
    stock_minimo  INTEGER NOT NULL DEFAULT 0,
    sincronizado  INTEGER NOT NULL DEFAULT 0,
    activo        INTEGER NOT NULL DEFAULT 1,
    es_precio_abierto INTEGER NOT NULL DEFAULT 0,
    es_bundle     INTEGER NOT NULL DEFAULT 0,
    categoria_producto TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY(tienda_id) REFERENCES tiendas(id)
);

CREATE TABLE IF NOT EXISTS bundle_components (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_producto_id     INTEGER NOT NULL,
    componente_producto_id INTEGER NOT NULL,
    cantidad               INTEGER NOT NULL DEFAULT 1,
    precio_asignado        REAL    NOT NULL DEFAULT 0.0,
    FOREIGN KEY (bundle_producto_id)     REFERENCES productos(id),
    FOREIGN KEY (componente_producto_id) REFERENCES productos(id)
);
CREATE INDEX IF NOT EXISTS idx_productos_tienda ON productos(tienda_id);

CREATE TABLE IF NOT EXISTS mesas (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL UNIQUE,
    nombre TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'libre' CHECK (estado IN ('libre','ocupada','cuenta'))
);

INSERT OR IGNORE INTO mesas (numero, nombre) VALUES
    (1,'1'),(2,'2'),(3,'3'),(4,'4');

CREATE TABLE IF NOT EXISTS ordenes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mesa_id        INTEGER NOT NULL,
    usuario_id     INTEGER NOT NULL,
    nombre_cliente TEXT NOT NULL DEFAULT '',
    estado         TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta','cerrada')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (mesa_id)    REFERENCES mesas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS orden_items (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id          INTEGER NOT NULL,
    producto_id       INTEGER,
    tienda_id         INTEGER NOT NULL,
    nombre_producto   TEXT NOT NULL,
    cantidad          INTEGER NOT NULL DEFAULT 1,
    precio_unitario   REAL NOT NULL,
    es_precio_abierto INTEGER NOT NULL DEFAULT 0,
    comanda_impresa   INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (orden_id) REFERENCES ordenes(id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    folio        TEXT NOT NULL UNIQUE,
    mesa_id      INTEGER,
    usuario_id   INTEGER NOT NULL,
    metodo_pago  TEXT NOT NULL DEFAULT 'Efectivo',
    monto_efectivo REAL NOT NULL DEFAULT 0.0,
    monto_tarjeta  REAL NOT NULL DEFAULT 0.0,
    subtotal     REAL NOT NULL DEFAULT 0.0,
    total        REAL NOT NULL DEFAULT 0.0,
    sincronizado INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS venta_detalle (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id          INTEGER NOT NULL,
    producto_id       INTEGER,
    tienda_id         INTEGER,
    nombre_producto   TEXT NOT NULL,
    cantidad          INTEGER NOT NULL,
    precio_unitario   REAL NOT NULL,
    costo_unitario    REAL NOT NULL DEFAULT 0.0,
    subtotal          REAL NOT NULL,
    es_precio_abierto INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (venta_id) REFERENCES ventas(id)
);

CREATE TABLE IF NOT EXISTS gastos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL,
    categoria    TEXT NOT NULL CHECK (categoria IN ('Barra','Deco','General')),
    tienda_id    INTEGER,
    concepto     TEXT NOT NULL,
    monto        REAL NOT NULL,
    origen       TEXT NOT NULL DEFAULT 'Caja',
    sincronizado INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS cortes_caja (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id        INTEGER NOT NULL,
    fecha             TEXT NOT NULL,
    total_ventas      REAL NOT NULL DEFAULT 0.0,
    total_gastos      REAL NOT NULL DEFAULT 0.0,
    efectivo_esperado REAL NOT NULL DEFAULT 0.0,
    efectivo_real     REAL NOT NULL DEFAULT 0.0,
    diferencia        REAL NOT NULL DEFAULT 0.0,
    fondo_caja        REAL NOT NULL DEFAULT 0.0,
    desglose_billetes TEXT NOT NULL DEFAULT '{}',
    ruta_pdf          TEXT,
    sincronizado      INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS ingresos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL,
    concepto     TEXT NOT NULL DEFAULT 'Ingreso',
    monto        REAL NOT NULL,
    metodo_pago  TEXT NOT NULL DEFAULT 'Efectivo',
    sincronizado INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
INSERT OR IGNORE INTO config (clave, valor) VALUES
    ('nombre_negocio','Estudio Deco'),
    ('sheets_id',''),
    ('sync_intervalo_seg','60'),
    ('fondo_turno','{"monto":0,"fecha":""}'),
    ('email_from',''),
    ('email_password',''),
    ('email_destino','estudiodecomx@gmail.com');

INSERT OR IGNORE INTO usuarios (id, nombre, perfil, nip) VALUES
    (1,'Admin','Administrador','03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4');

-- ── PRODUCTOS DE PRUEBA ──
-- Estudio 304 (tienda_id = 1)
INSERT OR IGNORE INTO productos (id, tienda_id, nombre, precio, stock_local, stock_minimo) VALUES
    (1,  1, 'Americano',        45.00, 50, 5),
    (2,  1, 'Latte',            55.00, 50, 5),
    (3,  1, 'Cappuccino',       60.00, 30, 5),
    (4,  1, 'Té Matcha',        65.00, 20, 3),
    (5,  1, 'Smoothie Frutas',  70.00, 15, 3),
    (6,  1, 'Croissant',        40.00, 12, 2),
    (7,  1, 'Panini Jamón',     85.00, 10, 2),
    (8,  1, 'Chai Latte',       58.00, 25, 5),
    (9,  1, 'Frappé Mokka',     72.00, 20, 3),
    (10, 1, 'Jugo Verde',       55.00, 18, 3);

-- Kokoro (tienda_id = 2)
INSERT OR IGNORE INTO productos (id, tienda_id, nombre, precio, stock_local, stock_minimo) VALUES
    (11, 2, 'Vela Aromática',   180.00, 15, 3),
    (12, 2, 'Incienso Pack',     85.00, 20, 5),
    (13, 2, 'Taza Cerámica',   150.00,  8, 2),
    (14, 2, 'Difusor Bambú',   250.00,  5, 2),
    (15, 2, 'Jabón Artesanal',  65.00, 25, 5),
    (16, 2, 'Aceite Esencial', 120.00, 12, 3);

-- Mack (tienda_id = 3) → no necesita productos, es precio abierto

-- Acuario (tienda_id = 4)
INSERT OR IGNORE INTO productos (id, tienda_id, nombre, precio, stock_local, stock_minimo) VALUES
    (17, 4, 'Pez Betta',       120.00, 10, 2),
    (18, 4, 'Pecera Mini',     350.00,  5, 1),
    (19, 4, 'Alimento Peces',   45.00, 30, 5),
    (20, 4, 'Planta Acuática',  80.00, 12, 3),
    (21, 4, 'Grava Decorativa', 55.00, 20, 5),
    (22, 4, 'Filtro Pecera',   180.00,  8, 2);
    
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texto TEXT NOT NULL,
    pos_x REAL NOT NULL DEFAULT 100,
    pos_y REAL NOT NULL DEFAULT 100,
    color TEXT DEFAULT '#fef3c7',
    width REAL NOT NULL DEFAULT 260,
    height REAL NOT NULL DEFAULT 180,
    minimizada INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);