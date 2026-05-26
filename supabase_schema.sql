-- =====================================================
-- FreshTrack AI - Esquema Completo v2
-- Operador de bodega - Distribuidora de Perecederos
-- =====================================================
-- INSTRUCCIONES:
-- 1. Crea un nuevo proyecto en https://supabase.com
-- 2. Ve a SQL Editor → New query
-- 3. Pega TODO este contenido y haz click en "Run"
-- 4. Debes ver "Success. No rows returned"
-- =====================================================

-- TABLA: inventario (principal)
CREATE TABLE inventario (
    id BIGSERIAL PRIMARY KEY,
    producto TEXT NOT NULL,
    categoria TEXT DEFAULT 'general',
    cantidad NUMERIC NOT NULL CHECK (cantidad >= 0),
    unidad TEXT DEFAULT 'unidades',
    fecha_vencimiento DATE NOT NULL,
    fecha_registro TIMESTAMPTZ DEFAULT NOW(),
    lote TEXT,
    estado TEXT DEFAULT 'activo' CHECK (estado IN ('activo', 'baja', 'agotado')),
    precio_unitario NUMERIC DEFAULT 0,
    usuario_id BIGINT,
    usuario_nombre TEXT
);

-- TABLA: clientes (destinatarios de despachos)
CREATE TABLE clientes (
    id BIGSERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    contacto TEXT,
    telefono TEXT,
    direccion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- TABLA: despachos (cabecera de cada entrega a cliente)
CREATE TABLE despachos (
    id BIGSERIAL PRIMARY KEY,
    cliente_id BIGINT REFERENCES clientes(id),
    cliente_nombre TEXT NOT NULL,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    observaciones TEXT,
    estado TEXT DEFAULT 'completado',
    usuario_id BIGINT,
    usuario_nombre TEXT
);

-- TABLA: despacho_items (detalle de productos por despacho)
CREATE TABLE despacho_items (
    id BIGSERIAL PRIMARY KEY,
    despacho_id BIGINT REFERENCES despachos(id) ON DELETE CASCADE,
    inventario_id BIGINT REFERENCES inventario(id),
    producto TEXT NOT NULL,
    cantidad NUMERIC NOT NULL CHECK (cantidad > 0),
    unidad TEXT DEFAULT 'unidades'
);

-- TABLA: movimientos (auditoria completa de todas las operaciones)
CREATE TABLE movimientos (
    id BIGSERIAL PRIMARY KEY,
    inventario_id BIGINT REFERENCES inventario(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'BAJA', 'CONSUMO', 'DESPACHO')),
    cantidad NUMERIC,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    motivo TEXT,
    despacho_id BIGINT REFERENCES despachos(id),
    usuario_id BIGINT
);

-- INDICES para performance en consultas FEFO y búsquedas frecuentes
CREATE INDEX idx_inv_fecha_venc   ON inventario(fecha_vencimiento);
CREATE INDEX idx_inv_estado       ON inventario(estado);
CREATE INDEX idx_inv_categoria    ON inventario(categoria);
CREATE INDEX idx_inv_producto     ON inventario(producto);
CREATE INDEX idx_mov_inventario   ON movimientos(inventario_id);
CREATE INDEX idx_mov_tipo         ON movimientos(tipo);
CREATE INDEX idx_mov_fecha        ON movimientos(fecha);
CREATE INDEX idx_desp_fecha       ON despachos(fecha);
CREATE INDEX idx_desp_cliente     ON despachos(cliente_id);
CREATE INDEX idx_items_despacho   ON despacho_items(despacho_id);

-- =====================================================
-- FIN DEL SCRIPT
-- =====================================================
-- Despues de ejecutar:
-- 1. Ve a Settings -> API
-- 2. Copia "Project URL" y "anon public key"
-- 3. Pegalos en el archivo .env del proyecto Python
-- =====================================================
