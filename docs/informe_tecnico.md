# FreshTrack AI — Informe Técnico Completo

**Versión:** 1.0  
**Fecha:** 2026-06-03  
**Proyecto:** Bot de gestión de inventario de perecederos con IA  
**Plataforma:** Telegram Bot + Supabase + Groq AI  

---

## 1. RESUMEN EJECUTIVO

FreshTrack AI es un sistema de gestión de inventario de perecederos implementado como un bot de Telegram. Está diseñado para operadores de bodega en distribuidoras de alimentos que necesitan registrar, controlar y despachar productos con fecha de vencimiento aplicando la metodología **FEFO** (First Expired, First Out).

El sistema combina:
- **Procesamiento de lenguaje natural (NLP)** via Groq API (Llama 3.3 70B) para entradas en texto libre
- **Base de datos relacional en la nube** via Supabase (PostgreSQL)
- **Interfaz conversacional** via Telegram Bot API
- **Alertas automáticas diarias** via APScheduler

---

## 2. STACK TECNOLÓGICO

| Capa | Tecnología | Versión | Rol |
|------|-----------|---------|-----|
| Lenguaje | Python | 3.10+ | Runtime principal |
| Interfaz | python-telegram-bot | 21.6 | Wrapper Telegram Bot API |
| LLM / NLP | Groq API + Llama 3.3 70B | Latest | Parsing de lenguaje natural |
| Base de datos | Supabase (PostgreSQL) | Cloud | Persistencia de datos |
| Scheduling | APScheduler | 3.10.4 | Alertas automáticas diarias |
| Configuración | python-dotenv | 1.0.1 | Variables de entorno |
| Timezone | tzdata | 2024.1 | Manejo de America/Bogota |

### 2.1 Dependencias (`requirements.txt`)

```
python-telegram-bot==21.6
groq==0.11.0
python-dotenv==1.0.1
apscheduler==3.10.4
supabase==2.9.1
tzdata==2024.1
```

---

## 3. ARQUITECTURA DEL SISTEMA

### 3.1 Visión General

El sistema sigue una arquitectura de **capas desacopladas**:

```
Usuario (Telegram) 
    ↕ HTTPS / WebSocket
Telegram Bot API (servidores de Telegram)
    ↕ Polling
bot.py — Orquestador principal
    ├── ai_parser.py       → Groq API (LLM)
    ├── database.py        → Supabase (PostgreSQL)
    ├── conversations.py   → Flujos de conversación
    ├── keyboards.py       → UI de Telegram
    └── scheduler.py       → Daemon de alertas diarias
```

### 3.2 Módulos del Sistema

| Módulo | Líneas | Responsabilidad |
|--------|--------|----------------|
| `bot.py` | 668 | Dispatcher de comandos y mensajes |
| `database.py` | 509 | Operaciones Supabase + lógica FEFO |
| `conversations.py` | 607 | Flujos multi-paso (wizards) |
| `ai_parser.py` | 205 | Integración Groq LLM + parseo |
| `keyboards.py` | 143 | Definición de UI Telegram |
| `scheduler.py` | 100 | Daemon de alertas diarias 8 AM |

**Total código:** ~2,232 líneas de Python

---

## 4. MÓDULOS TÉCNICOS — DESCRIPCIÓN DETALLADA

### 4.1 `bot.py` — Orquestador Principal (668 líneas)

El módulo central que registra handlers y gestiona el flujo de mensajes Telegram.

#### Comandos registrados (13 comandos)

| Comando | Función | Descripción |
|---------|---------|-------------|
| `/start` | `start()` | Bienvenida + muestra chat ID |
| `/stock` | `stock()` | Inventario ordenado FEFO con emojis |
| `/alertas` | `alertas()` | Productos vencen en ≤3 días |
| `/vencidos` | `vencidos()` | Dar de baja lotes vencidos |
| `/estadisticas` | `estadisticas()` | Estadísticas globales |
| `/reporte_diario` | `reporte_diario()` | Resumen movimientos del día |
| `/buscar` | `buscar()` | Búsqueda parcial por nombre |
| `/consumir` | `consumir()` | Consumo interno con FEFO |
| `/despachar` | `despachar()` | Despacho a cliente con FEFO |
| `/clientes` | `clientes()` | Listar clientes activos |
| `/addcliente` | `addcliente()` | Registrar nuevo cliente |
| `/ayuda` | `ayuda()` | Documentación completa |
| Free-text | `procesar_mensaje()` | Entrada libre vía IA |

#### Funciones utilitarias clave

```python
def _emoji_dias(dias: int) -> str:
    # 🔴 vencido (<0), 🟠 mañana (≤1), 🟡 próximo (≤3), 🟢 ok (>3)

def _texto_dias(dias: int) -> str:
    # Texto legible: "VENCIDO", "Vence hoy", "Vence en X días"

def _truncar(texto: str, limite: int = 4000) -> str:
    # Respeta límite de 4096 chars de Telegram
```

#### Prioridad de handlers

```
1. ConversationHandlers (flujos multi-paso)
2. MessageHandler para botones del menú
3. CommandHandlers (comandos /xxx)
4. CallbackQueryHandler (botones inline)
5. MessageHandler texto libre → procesar_mensaje()
```

---

### 4.2 `ai_parser.py` — Capa NLP con Groq (205 líneas)

Integra Groq API con modelo Llama 3.3 70B para extraer datos estructurados de texto libre.

#### Configuración del LLM

```python
GROQ_MODEL = "llama-3.3-70b-versatile"
temperature = 0.1      # Determinístico
max_tokens = 1024
response_format = {"type": "json_object"}
```

#### Los 3 prompts especializados

**Prompt 1 — Entrada de inventario** (`_PROMPT_ENTRADA`)
- **Input:** `"Lechuga 5 kg vence 10/12, Tomate 8 cajas 09/12"`
- **Output JSON:**
  ```json
  {
    "productos": [
      {"producto": "Lechuga", "cantidad": 5, "unidad": "kg",
       "fecha_vencimiento": "2026-12-10", "categoria": "verduras"},
      {"producto": "Tomate", "cantidad": 8, "unidad": "cajas",
       "fecha_vencimiento": "2026-12-09", "categoria": "verduras"}
    ]
  }
  ```

**Prompt 2 — Consumo interno** (`_PROMPT_CONSUMO`)
- **Input:** `"consumí 3 kg de lechuga para almuerzo del personal"`
- **Output JSON:**
  ```json
  {
    "items": [{"producto": "Lechuga", "cantidad": 3, "motivo": "almuerzo del personal"}]
  }
  ```

**Prompt 3 — Despacho a cliente** (`_PROMPT_DESPACHO`)
- **Input:** `"despachar a Éxito: 10 kg tomate, 5 cajas lechuga"`
- **Output JSON:**
  ```json
  {
    "cliente": "Éxito",
    "items": [
      {"producto": "Tomate", "cantidad": 10},
      {"producto": "Lechuga", "cantidad": 5}
    ],
    "observaciones": ""
  }
  ```

#### Normalización automática

- **Fechas:** `DD/MM` → `YYYY-MM-DD` con corrección de año (fechas pasadas avanzan al siguiente año)
- **Unidades:** estandarización a `kg`, `litros`, `unidades`, `cajas`, `bolsas`, `canastas`
- **Categorías:** auto-clasificación en 7 categorías (`lacteos`, `carnes`, `verduras`, `frutas`, `congelados`, `procesados`, `general`)

---

### 4.3 `database.py` — Capa de Datos con Supabase (509 líneas)

Abstracción completa sobre el cliente Supabase con toda la lógica de negocio de inventario.

#### Configuración de conexión

```python
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TZ = ZoneInfo("America/Bogota")   # UTC-5
```

#### Funciones principales

**Gestión de inventario:**
```python
registrar_producto(producto, cantidad, unidad, fecha_vencimiento, 
                   categoria, usuario_id, usuario_nombre) → dict

consultar_stock(orden_fefo=True) → list[dict]        # Ordenado por vencimiento
consultar_proximos_vencer(dias=3) → list[dict]        # Alerta temprana
buscar_producto(nombre: str) → list[dict]             # Búsqueda parcial ilike
```

**Consumo con FEFO:**
```python
consumir_producto(nombre, cantidad, motivo, usuario_id) → {
    "exito": bool,
    "lotes_afectados": list,
    "total_consumido": float,
    "error": str
}
# Aplica FEFO: descuenta primero del lote más próximo a vencer
```

**Despacho con FEFO:**
```python
registrar_despacho(cliente_nombre, items, observaciones, 
                   usuario_id, usuario_nombre) → {
    "despacho_id": str,
    "cliente": str,
    "productos": list,
    "errores": list
}
# Crea cabecera + líneas de despacho + movimientos de auditoría
```

**Auditoría:**
```python
dar_de_baja(inventario_id, motivo, usuario_id)        # Baja individual
dar_de_baja_vencidos(usuario_id) → list               # Baja masiva vencidos
```

**Reportes:**
```python
reporte_diario() → {
    "entradas": int, "consumos": int, 
    "bajas": int, "despachos": int,
    "total_lotes": int, "total_unidades": float
}

estadisticas_generales() → {
    "total_lotes": int, "total_unidades": float,
    "productos_unicos": int, "bajas": int, "total_despachos": int
}
```

---

### 4.4 `conversations.py` — Flujos Multi-paso (607 líneas)

Implementa tres `ConversationHandler` de python-telegram-bot para guiar al usuario paso a paso.

#### Flujo 1: Entrada Manual (`CONV_ENTRADA`)

```
Estado PROD → Estado CANT → Estado UNID → Estado FECH → Estado CONF
   ↓               ↓            ↓              ↓             ↓
¿Producto?    ¿Cantidad?    ¿Unidad?     ¿Vencimiento?  ✅/❌
                                         (validación)   Guardar/Agregar/Cancelar
```

#### Flujo 2: Consumo Interno (`CONV_CONSUMO`)

```
Estado C_PROD → Estado C_CANT → Estado C_MOT → Ejecutar
    ↓                ↓               ↓
¿Producto?      ¿Cantidad?       ¿Motivo?    consumir_producto()
(botones o        (validar         (botones     FEFO automático
  manual)          stock)          o libre)
```

#### Flujo 3: Despacho a Cliente (`CONV_DESPACHO`)

```
Estado D_CLI → Estado D_PRODS → Estado D_CANT → Estado D_CONF
    ↓               ↓                ↓                ↓
¿Cliente?      ¿Productos?      ¿Cantidades?    Confirmar
(lista o         (multi-          (por cada       registrar_despacho()
  nuevo)          select)          producto)       FEFO automático
```

#### Timeout y configuración

```python
conversation_timeout = 300   # 5 minutos de inactividad
allow_reentry = True         # Permite reiniciar flujo
fallback = /cancelar         # Salida de emergencia
```

---

### 4.5 `keyboards.py` — Interfaz de Usuario Telegram (143 líneas)

Define todos los teclados inline y reply keyboards usados en la interfaz.

#### Teclados estáticos

```python
MENU_PRINCIPAL = ReplyKeyboardMarkup([
    ["📦 Registrar entrada", "🔍 Ver stock"],
    ["🔥 Alertas de vencimiento", "🚚 Despachar"],
    ["⚠️ Dar de baja vencidos", "📊 Estadísticas"]
])

KB_UNIDADES = InlineKeyboardMarkup([
    [("kg", "unidad_kg"), ("litros", "unidad_litros"), ("unidades", "unidad_unidades")],
    [("cajas", "unidad_cajas"), ("bolsas", "unidad_bolsas"), ("canastas", "unidad_canastas")]
])
```

#### Teclados dinámicos

```python
kb_confirmar_entrada(productos: list) → InlineKeyboardMarkup
# ✅ Guardar / ❌ Cancelar — confirma datos parseados por IA

kb_productos_stock(productos: list, prefix: str) → InlineKeyboardMarkup
# Lista hasta 8 productos con botones + opción "✍️ Escribir manualmente"

kb_clientes(clientes: list) → InlineKeyboardMarkup
# Lista hasta 6 clientes + opción "✍️ Nuevo cliente"

kb_productos_despacho(productos: list, seleccionados: list) → InlineKeyboardMarkup
# Multi-select con checkmarks ✓ + botón "✅ Confirmar selección"
```

---

### 4.6 `scheduler.py` — Daemon de Alertas (100 líneas)

Proceso independiente que ejecuta alertas diarias a las 8:00 AM.

```python
scheduler = AsyncIOScheduler(timezone="America/Bogota")
scheduler.add_job(
    enviar_alerta_diaria,
    CronTrigger(hour=8, minute=0)
)

async def enviar_alerta_diaria():
    proximos = await consultar_proximos_vencer(dias=3)
    if not proximos:
        # 📦 Sin alertas — resumen de stock
    else:
        # ⚠️ Lista de productos por vencer con emojis de severidad
        # 🔴 VENCIDO | 🟠 MAÑANA | 🟡 En N días
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=mensaje)
```

---

## 5. BASE DE DATOS

### 5.1 Esquema de tablas

#### Tabla `inventario` — Lotes de productos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID (PK) | Identificador único del lote |
| `producto` | TEXT | Nombre del producto |
| `categoria` | TEXT | verduras/frutas/lacteos/carnes/congelados/procesados/general |
| `cantidad` | NUMERIC | Cantidad disponible en el lote |
| `unidad` | TEXT | kg/litros/unidades/cajas/bolsas/canastas |
| `fecha_vencimiento` | DATE | Fecha de vencimiento del lote |
| `fecha_registro` | TIMESTAMPTZ | Cuándo se registró |
| `lote` | TEXT | Código de lote (opcional) |
| `estado` | TEXT | activo / agotado / baja |
| `precio_unitario` | NUMERIC | Precio por unidad (opcional) |
| `usuario_id` | TEXT | ID del operador que registró |
| `usuario_nombre` | TEXT | Nombre del operador |

#### Tabla `clientes` — Registro de clientes

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID (PK) | Identificador único |
| `nombre` | TEXT | Nombre del cliente |
| `contacto` | TEXT | Persona de contacto |
| `telefono` | TEXT | Teléfono |
| `direccion` | TEXT | Dirección de entrega |
| `activo` | BOOLEAN | Estado activo/inactivo |
| `created_at` | TIMESTAMPTZ | Fecha de registro |

#### Tabla `despachos` — Cabeceras de despacho

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID (PK) | Identificador del despacho |
| `cliente_id` | UUID (FK) | Referencia a clientes |
| `cliente_nombre` | TEXT | Nombre del cliente (desnormalizado) |
| `fecha` | TIMESTAMPTZ | Fecha y hora del despacho |
| `observaciones` | TEXT | Notas adicionales |
| `estado` | TEXT | pendiente / completado / cancelado |
| `usuario_id` | TEXT | ID del operador |
| `usuario_nombre` | TEXT | Nombre del operador |

#### Tabla `despacho_items` — Líneas de despacho

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID (PK) | Identificador de la línea |
| `despacho_id` | UUID (FK) | Referencia a despachos |
| `inventario_id` | UUID (FK) | Lote descontado |
| `producto` | TEXT | Nombre del producto |
| `cantidad` | NUMERIC | Cantidad despachada |
| `unidad` | TEXT | Unidad de medida |

#### Tabla `movimientos` — Auditoría completa

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | UUID (PK) | Identificador único |
| `inventario_id` | UUID (FK) | Lote afectado |
| `tipo` | TEXT | ENTRADA / CONSUMO / DESPACHO / BAJA |
| `cantidad` | NUMERIC | Cantidad del movimiento |
| `fecha` | TIMESTAMPTZ | Timestamp del evento |
| `motivo` | TEXT | Descripción del motivo |
| `despacho_id` | UUID (FK) | Referencia a despachos (nullable) |
| `usuario_id` | TEXT | ID del operador |

### 5.2 Índices de optimización

```sql
-- Índices en inventario
CREATE INDEX ON inventario(fecha_vencimiento);   -- Queries FEFO
CREATE INDEX ON inventario(estado);              -- Filtro activo/baja
CREATE INDEX ON inventario(categoria);           -- Filtros por categoría
CREATE INDEX ON inventario(producto);            -- Búsquedas por nombre

-- Índices en movimientos
CREATE INDEX ON movimientos(inventario_id);      -- Auditoría por lote
CREATE INDEX ON movimientos(tipo);               -- Filtros por tipo
CREATE INDEX ON movimientos(fecha);              -- Reportes por fecha
```

---

## 6. METODOLOGÍA FEFO

**First Expired, First Out** — Los lotes con fecha de vencimiento más próxima se consumen primero.

### 6.1 Implementación en consultas

```python
# Ordenamiento FEFO en toda consulta de stock activo
supabase.table("inventario")
    .select("*")
    .eq("estado", "activo")
    .order("fecha_vencimiento", desc=False)   # ASC = primero vence primero
    .execute()
```

### 6.2 Algoritmo de consumo multi-lote

```python
def consumir_producto(nombre, cantidad_total, motivo, usuario_id):
    # 1. Obtener todos los lotes activos del producto, ordenados FEFO
    lotes = get_lotes_fefo(nombre)
    
    # 2. Descontar de cada lote hasta cubrir la cantidad total
    restante = cantidad_total
    for lote in lotes:
        if restante <= 0:
            break
        descontar = min(lote["cantidad"], restante)
        actualizar_lote(lote["id"], lote["cantidad"] - descontar)
        registrar_movimiento(lote["id"], "CONSUMO", descontar, motivo)
        restante -= descontar
    
    # 3. Si lote queda en 0, marcarlo como "agotado"
    if lote["cantidad"] == 0:
        actualizar_estado(lote["id"], "agotado")
    
    return {"exito": restante == 0, "lotes_afectados": [...]}
```

---

## 7. FLUJO DE DATOS — ENTRADA DE INVENTARIO

### Ruta 1: Texto libre via IA

```
Usuario escribe: "llegaron 10 kg de lechuga, vence el 15/12"
    ↓
bot.py: procesar_mensaje()
    ↓
ai_parser.py: parsear_mensaje(texto)
    ↓
Groq API (Llama 3.3 70B) → respuesta JSON
    ↓
{producto: "Lechuga", cantidad: 10, unidad: "kg", 
 fecha_vencimiento: "2026-12-15", categoria: "verduras"}
    ↓
bot.py: mostrar_confirmacion() — botones ✅/❌
    ↓ (usuario confirma)
database.py: registrar_producto()
    ↓
Supabase: INSERT INTO inventario + INSERT INTO movimientos (ENTRADA)
    ↓
Bot responde: "✅ Lechuga registrada: 10 kg, vence 15/12/2026"
```

### Ruta 2: Wizard manual (/registrar o botón)

```
Usuario presiona "📦 Registrar entrada"
    ↓
conversations.py: CONV_ENTRADA inicia
    ↓ Estado PROD: "¿Nombre del producto?"
    ↓ Estado CANT: "¿Cantidad?"
    ↓ Estado UNID: botones kg/litros/unidades/...
    ↓ Estado FECH: "¿Fecha vencimiento? (DD/MM)"
    ↓ Estado CONF: "✅ Guardar / ➕ Agregar otro / ❌ Cancelar"
    ↓
database.py: registrar_producto()
    ↓
Supabase: INSERT
```

---

## 8. CONFIGURACIÓN Y DESPLIEGUE

### 8.1 Variables de entorno (`.env`)

```env
TELEGRAM_BOT_TOKEN=7891234567:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.[...]
ADMIN_CHAT_ID=123456789   # Opcional: para alertas diarias
```

### 8.2 Comandos de ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Iniciar el bot (proceso principal)
python bot.py

# Iniciar daemon de alertas (proceso separado, opcional)
python scheduler.py
```

### 8.3 Verificación inicial

```bash
# Probar conexión a base de datos
python database.py

# El bot debe responder a:
# /start   → Mensaje de bienvenida con chat ID
# /stock   → Inventario vacío o con datos
# Texto libre → Parsing por IA
```

### 8.4 Diagrama de despliegue

```
[Operador] ←→ [App Telegram] ←→ [Telegram Servers] 
                                        ↕ HTTPS Polling
                              [Python Bot Server (Local/VPS)]
                                ├── bot.py        (proceso 1)
                                └── scheduler.py  (proceso 2)
                                        ↕
                              [Groq API] ←→ [Supabase Cloud]
                              (LLM: Llama)   (PostgreSQL)
```

---

## 9. SEGURIDAD Y CONSIDERACIONES

- **Sin autenticación por usuario:** Cualquier usuario de Telegram puede interactuar con el bot
- **ADMIN_CHAT_ID:** Solo este chat recibe alertas automáticas diarias
- **Credenciales:** Almacenadas en `.env`, nunca en código fuente
- **SUPABASE_KEY:** Usa la clave `anon` (pública), no la `service_role`
- **Rate limiting:** No implementado; Telegram tiene límites nativos
- **Validación de entrada:** Realizada por el LLM y por validaciones en `conversations.py`

---


*Documento generado automáticamente — FreshTrack AI v1.0*
