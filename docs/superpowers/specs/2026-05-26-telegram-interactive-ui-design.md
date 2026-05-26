# FreshTrack AI — Diseño UX Interactiva Telegram

**Fecha:** 2026-05-26  
**Proyecto:** freshtrack_bot  
**Stack:** python-telegram-bot 21.6 · Groq/Llama 3.3 70B · Supabase  
**Estado:** Aprobado por el equipo

---

## 1. Objetivo

Hacer la interfaz del bot más intuitiva agregando elementos interactivos nativos de Telegram (ReplyKeyboard, InlineKeyboard, ConversationHandler) sin romper el flujo de texto libre + IA que ya existe.

**Motivación:**
- Reducir errores de formato al registrar entradas (el flujo más propenso a fallos)
- Acelerar operaciones frecuentes (consumo, despacho)
- Mejorar la presentación para la sustentación académica

---

## 2. Principio de diseño: Híbrido inteligente

Tres capas conviven sin conflicto:

| Capa | Cuándo activa | Mecanismo |
|---|---|---|
| ReplyKeyboard fijo | Siempre | Menú principal pegado al teclado |
| ConversationHandler | Al presionar un botón del menú | Flujo guiado paso a paso |
| IA + confirmación inline | Al escribir texto libre | Groq parsea → InlineKeyboard confirma |

El operario puede usar cualquiera de las tres en cualquier momento. `/cancelar` sale de cualquier flujo activo.

---

## 3. Arquitectura

```
bot.py (modificado)
├── keyboards.py         ← NUEVO: todos los teclados centralizados
├── conversations.py     ← NUEVO: ConversationHandlers
├── ai_parser.py         ← sin cambios
└── database.py          ← sin cambios
```

### Flujo general

```
Usuario
  │
  ├── presiona botón menú → ConversationHandler (guiado)
  │                                │
  └── escribe texto libre → IA parsea → InlineKeyboard confirmar
                                             │
                                        database.py → Supabase
```

---

## 4. Menú principal (ReplyKeyboard fijo)

Visible siempre en la parte inferior del chat. Se activa en `/start` y nunca desaparece.

```
[ 📦 Nueva Entrada ] [ 🔍 Ver Stock  ]
[ 🔥 Consumo        ] [ 🚚 Despacho   ]
[ ⚠️ Alertas        ] [ 📊 Reporte    ]
```

- `resize_keyboard=True` para que no ocupe demasiado espacio
- Los 4 comandos de consulta (`/stock`, `/alertas`, `/vencidos`, `/reporte`) siguen funcionando como texto también

---

## 5. Flujo de Entrada

### 5a. Texto libre → IA → confirmación

```
Usuario: "Lechuga 5 kg 10/12, Tomate 8 kg 09/12"
   ↓ IA parsea (ai_parser.parsear_mensaje)
Bot:
  "📋 Entendí esto:
   • 🥬 Lechuga — 5 kg — vence 10/06/2026
   • 🍅 Tomate — 8 kg — vence 09/06/2026

   [✅ Confirmar todo]  [✏️ Editar]  [❌ Cancelar]"
```

- `✅ Confirmar todo` → registra todos los productos de una vez
- `✏️ Editar` → inicia el wizard para el primer producto con error
- `❌ Cancelar` → descarta sin guardar

### 5b. Botón 📦 Nueva Entrada → wizard

```
Bot: "¿Qué producto llegó?"
  → Usuario escribe nombre (texto libre)

Bot: "¿Cuánto?"
  → Usuario escribe número (texto libre)

Bot: "¿En qué unidad?"
  → [ kg ] [ litros ] [ unidades ] [ cajas ] [ bolsas ] [ canastas ]

Bot: "¿Fecha de vencimiento? Escribe DD/MM o DD/MM/AAAA"
  → Usuario escribe fecha (texto libre, IA valida)

Bot: "✅ Listo para registrar:
      [emoji] Producto — X unidad — vence DD/MM/AAAA
      [💾 Guardar]  [➕ Agregar otro]  [❌ Cancelar]"
```

**Estados del ConversationHandler `CONV_ENTRADA`:**

| Estado | Qué espera | Siguiente |
|---|---|---|
| `PRODUCTO` | Texto libre | → `CANTIDAD` |
| `CANTIDAD` | Número | → `UNIDAD` |
| `UNIDAD` | CallbackQuery de botón | → `FECHA` |
| `FECHA` | Texto DD/MM | → `CONFIRMAR` |
| `CONFIRMAR` | CallbackQuery Guardar/Agregar/Cancelar | → END o PRODUCTO |

---

## 6. Flujo de Consumo

```
Usuario presiona: 🔥 Consumo
   ↓ Bot carga stock activo de Supabase
Bot:
  "¿Qué producto vas a consumir?
   [ 🥬 Lechuga (8 kg) ] [ 🍅 Tomate (5 kg) ]
   [ 🐟 Salmón (3.5 kg)] [ 🧀 Queso (2 kg)  ]
   [ ✏️ Escribir nombre ]"

Usuario selecciona producto
   ↓
Bot: "¿Cuánto? (disponible: X unidad)"
  → Usuario escribe número

Bot: "¿Motivo? (opcional)"
  → [ 🍳 Preparación ] [ 🗑️ Dañado/Vencido ] [ ➡️ Omitir ]

Bot: "✅ Consumo registrado:
      [emoji] Producto — X unidad — Motivo
      📦 Stock restante: Y unidad"
```

- Máximo 8 productos en los botones (los primeros en FEFO). Si hay más, se agrega botón `[ Ver más ]`
- `[ ✏️ Escribir nombre ]` permite búsqueda libre si el producto no aparece

**Estados `CONV_CONSUMO`:**

| Estado | Qué espera | Siguiente |
|---|---|---|
| `PRODUCTO` | CallbackQuery o texto libre | → `CANTIDAD` |
| `CANTIDAD` | Número | → `MOTIVO` |
| `MOTIVO` | CallbackQuery de botón | → END |

---

## 7. Flujo de Despacho

```
Usuario presiona: 🚚 Despacho
   ↓ Bot carga clientes de Supabase
Bot:
  "¿Para qué cliente?"
   [ Éxito ] [ Carulla ] [ Olímpica ]
   [ ✏️ Otro cliente ]

Usuario selecciona cliente
   ↓
Bot:
  "¿Qué productos despachás? Toca para agregar:
   [ 🥬 Lechuga (8 kg)  ] [ 🍅 Tomate (5 kg) ]
   [ 🐟 Salmón (3.5 kg) ] [ 🧀 Queso (2 kg)  ]
   [ ✅ Listo, despachar ]"

Usuario toca producto → Bot: "¿Cuánto? (disponible: X)"
Usuario escribe cantidad → Bot: "✓ Producto X unidad agregado"
  (vuelve a mostrar lista con el producto marcado ✓)

Usuario toca ✅ Listo
   ↓
Bot:
  "🚚 Resumen despacho → Cliente
   • Producto 1 — X unidad ✅
   • Producto 2 — X unidad ✅
   [✅ Confirmar despacho]  [❌ Cancelar]"
```

**Estados `CONV_DESPACHO`:**

| Estado | Qué espera | Siguiente |
|---|---|---|
| `CLIENTE` | CallbackQuery o texto libre | → `PRODUCTOS` |
| `PRODUCTOS` | CallbackQuery producto o "Listo" | → `CANTIDAD` o `CONFIRMAR` |
| `CANTIDAD` | Número | → `PRODUCTOS` (loop) |
| `CONFIRMAR` | CallbackQuery | → END |

---

## 8. `keyboards.py` — estructura completa

```python
# Teclados estáticos
MENU_PRINCIPAL: ReplyKeyboardMarkup      # menú fijo 2x3
KB_UNIDADES: InlineKeyboardMarkup        # kg/litros/unidades/cajas/bolsas/canastas
KB_MOTIVOS: InlineKeyboardMarkup         # Preparación / Dañado / Omitir

# Teclados dinámicos (funciones)
def kb_confirmar_entrada(productos: list) -> InlineKeyboardMarkup
    # ✅ Confirmar todo | ✏️ Editar | ❌ Cancelar

def kb_productos_stock(productos: list) -> InlineKeyboardMarkup
    # Máx 8 productos + "✏️ Escribir" como último botón

def kb_clientes(clientes: list) -> InlineKeyboardMarkup
    # Lista de clientes + "✏️ Otro cliente"

def kb_confirmar_despacho() -> InlineKeyboardMarkup
    # ✅ Confirmar despacho | ❌ Cancelar

def kb_guardar_entrada() -> InlineKeyboardMarkup
    # 💾 Guardar | ➕ Agregar otro | ❌ Cancelar
```

---

## 9. Cambios a `bot.py`

- Importar y registrar los dos `ConversationHandler` (entrada, consumo, despacho)
- Agregar handler para CallbackQuery (botones inline)
- El handler de texto libre existente se mantiene **igual**, solo se le añade al final la llamada a `kb_confirmar_entrada()` en lugar de guardar directamente
- Agregar `/cancelar` como comando que llama `ConversationHandler.END`
- En `/start`: enviar `reply_markup=MENU_PRINCIPAL`

**Comandos existentes que NO cambian:**  
`/stock`, `/alertas`, `/vencidos`, `/buscar`, `/clientes`, `/addcliente`, `/reporte`, `/stats`, `/ayuda`

---

## 10. Emoji por categoría de producto

Para hacer las listas más visuales:

| Categoría | Emoji |
|---|---|
| verduras | 🥬 |
| frutas | 🍎 |
| lacteos | 🥛 |
| carnes | 🥩 |
| congelados | 🧊 |
| procesados | 🥫 |
| general | 📦 |

---

## 11. Manejo de errores

- Si Supabase no devuelve productos para `kb_productos_stock()`, el bot responde: *"No hay stock activo. Registra productos primero con 📦 Nueva Entrada"*
- Si Supabase no devuelve clientes para `kb_clientes()`, el bot pide el nombre directamente por texto
- Si el usuario envía texto donde se espera un número, el bot repite la pregunta: *"Por favor escribe solo el número (ej: 3.5)"*
- Timeout de ConversationHandler: 5 minutos de inactividad → `END` automático con mensaje *"⏱ Operación cancelada por inactividad. Usa el menú para empezar de nuevo."*

---

## 12. Lo que NO cambia

- `ai_parser.py` — sin modificaciones
- `database.py` — sin modificaciones  
- `scheduler.py` — sin modificaciones
- Todos los comandos de texto existentes siguen funcionando
- El texto libre sigue siendo procesado por IA en todo momento
