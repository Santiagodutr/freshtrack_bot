# FreshTrack AI — Bot de Telegram para Bodegas de Perecederos

Sistema de control de inventario para operadores de bodega en distribuidoras de alimentos perecederos. Aplica metodología **FEFO** (First Expired, First Out), procesamiento por IA y base de datos en la nube.

## Equipo

- **Sofía García** — Backend & Bot Telegram
- **David Arango** — IA & Parser de mensajes
- **Santiago Duarte** — Base de Datos & Reportes (Supabase)

## Arquitectura

```
Operador → Telegram → bot.py → ai_parser.py (Groq/Llama 3.3) → database.py → Supabase
                          ↓
                   scheduler.py (alertas 8 AM)
```

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Bot | python-telegram-bot 21.6 |
| IA | Groq API + Llama 3.3 70B (gratis) |
| Base de datos | Supabase (PostgreSQL cloud) |
| Tareas programadas | APScheduler |
| Lenguaje | Python 3.10+ |

---

## Credenciales necesarias

| Variable | Estado | Cómo obtenerla |
|---|---|---|
| `SUPABASE_URL` | ✅ Lista | Ya configurada en `.env.example` |
| `SUPABASE_KEY` | ✅ Lista | Ya configurada en `.env.example` |
| `TELEGRAM_BOT_TOKEN` | ⚠️ Falta | @BotFather → `/newbot` |
| `GROQ_API_KEY` | ⚠️ Falta | https://console.groq.com/keys |
| `ADMIN_CHAT_ID` | Opcional | Tu `/start` en el bot te lo da |

---

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Crear .env (Supabase ya viene listo)
cp .env.example .env
# Abre .env y pega tu TELEGRAM_BOT_TOKEN y GROQ_API_KEY

# 4. Verificar conexión a Supabase
python database.py

# 5. Arrancar el bot
python bot.py
```

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `/start` | Bienvenida y tu chat ID |
| `/stock` | Inventario completo ordenado FEFO |
| `/alertas` | Productos que vencen en ≤ 3 días |
| `/vencidos` | Da de baja automática productos vencidos |
| `/buscar [nombre]` | Busca un producto en el stock |
| `/consumir [descripción]` | Registra consumo interno (aplica FEFO) |
| `/despachar [cliente]: [productos]` | Registra salida a cliente (aplica FEFO) |
| `/clientes` | Lista de clientes registrados |
| `/addcliente [nombre]` | Agrega un nuevo cliente |
| `/reporte` | Resumen de movimientos del día |
| `/stats` | Estadísticas globales del inventario |
| `/ayuda` | Ayuda completa |

### Ejemplos de uso

**Registrar entrada** (texto libre, sin comando):
```
Lechuga 5 kg 10/12
Tomate 8 kg 09/12, Yogur 10 litros 15/12
Llegaron 12 cajas de queso que vencen el 20 de junio
```

**Consumo interno:**
```
/consumir 5 kg de lechuga para almuerzo
/consumir 3 litros de leche — dañada
/consumir 2 kg tomate y 1 kg zanahoria
```

**Despacho a cliente:**
```
/despachar Éxito: 10 kg tomate, 5 unidades lechuga
/despachar cliente Carulla 3 kg queso y 2 litros leche
/despachar Olimpica 8 kg salmon
```

**Agregar cliente:**
```
/addcliente Almacenes Éxito
/addcliente Carulla Palermo
```

---

## Esquema de base de datos

```
inventario          → Lotes de productos (con categoría, estado, FEFO)
clientes            → Clientes de la distribuidora
despachos           → Cabecera de cada entrega a cliente
despacho_items      → Detalle de productos por despacho
movimientos         → Auditoría completa (ENTRADA | CONSUMO | DESPACHO | BAJA)
```

**Estados de un lote:**
- `activo` — con stock disponible
- `agotado` — cantidad llegó a 0 por consumo/despacho
- `baja` — dado de baja manualmente o por vencimiento

**Tipos de movimiento:**
- `ENTRADA` — llegada de producto a bodega
- `CONSUMO` — consumo interno
- `DESPACHO` — salida hacia un cliente
- `BAJA` — descarte por vencimiento

---

## Alertas automáticas (opcional)

```bash
# En terminal separada, después de arrancar bot.py
python scheduler.py
```

Envía un reporte matutino cada día a las 8 AM con productos próximos a vencer. Requiere `ADMIN_CHAT_ID` en `.env`.

---

## Guion del demo (video)

### Escena 1 — Sofía (Bot funcionando)
1. Corre `python bot.py`
2. En Telegram envía `/start`
3. Envía: `Lechuga 5 kg 10/12, Tomate 8 kg 09/12, Yogur 10 litros 15/12, Queso 2 kg 12/12, Salmón 1.5 kg 08/12`
4. Muestra confirmación de 5 productos registrados

### Escena 2 — David (IA por dentro)
1. Muestra `ai_parser.py` — tres prompts distintos (entrada, consumo, despacho)
2. Corre `python ai_parser.py` y muestra los tres JSON resultantes
3. Explica modelo Llama 3.3 70B vía Groq (gratuito, sin tarjeta)

### Escena 3 — Santiago (Supabase en vivo)
1. Dashboard Supabase → Table Editor → `inventario` (5 productos de Sofía)
2. Vuelve a Telegram: `/stock` → FEFO
3. `/alertas` → próximos a vencer
4. `/despachar Carulla: 3 kg tomate, 2 litros yogur`
5. Supabase → `despachos` + `movimientos` → auditoría completa
6. `/reporte` → resumen del día
7. `/vencidos` → baja automática
8. `/stats` → estadísticas globales

---

## Troubleshooting

| Error | Solución |
|---|---|
| `Faltan SUPABASE_URL o SUPABASE_KEY` | Verifica que el archivo se llame `.env` (sin .txt) |
| `Could not find table 'inventario'` | El esquema SQL ya está aplicado en el proyecto creado — verifica las credenciales |
| `telegram.error.Unauthorized` | Token de Telegram mal copiado |
| `groq.AuthenticationError` | API key de Groq inválida — genera una nueva |
| `ModuleNotFoundError` | Activa venv y corre `pip install -r requirements.txt` |
