"""
keyboards.py - Teclados centralizados para FreshTrack AI
Contiene todos los ReplyKeyboard e InlineKeyboard del bot.
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# ── Emojis por categoría de producto ─────────────────────────
_EMOJIS: dict[str, str] = {
    "verduras": "🥬",
    "frutas": "🍎",
    "lacteos": "🥛",
    "carnes": "🥩",
    "congelados": "🧊",
    "procesados": "🥫",
    "general": "📦",
}


def emoji_cat(categoria: str) -> str:
    """Retorna el emoji correspondiente a la categoría del producto."""
    return _EMOJIS.get((categoria or "general").lower(), "📦")


# ── Menú principal (siempre visible en el teclado del chat) ───
MENU_PRINCIPAL = ReplyKeyboardMarkup(
    [
        ["📦 Nueva Entrada", "🔍 Ver Stock"],
        ["🔥 Consumo",       "🚚 Despacho"],
        ["⚠️ Alertas",       "📊 Reporte"],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# ── Unidades (inline, estático) ───────────────────────────────
KB_UNIDADES = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("kg",       callback_data="unidad:kg"),
        InlineKeyboardButton("litros",   callback_data="unidad:litros"),
        InlineKeyboardButton("unidades", callback_data="unidad:unidades"),
    ],
    [
        InlineKeyboardButton("cajas",    callback_data="unidad:cajas"),
        InlineKeyboardButton("bolsas",   callback_data="unidad:bolsas"),
        InlineKeyboardButton("canastas", callback_data="unidad:canastas"),
    ],
])

# ── Motivos de consumo (inline, estático) ─────────────────────
KB_MOTIVOS = InlineKeyboardMarkup([
    [InlineKeyboardButton("🍳 Preparación",      callback_data="motivo:Preparación")],
    [InlineKeyboardButton("🗑️ Dañado / Vencido", callback_data="motivo:Producto dañado")],
    [InlineKeyboardButton("➡️ Omitir",            callback_data="motivo:Consumo interno")],
])


# ── Confirmación de entrada parseada por IA (inline, dinámico) ─
def kb_confirmar_entrada(productos: list) -> InlineKeyboardMarkup:
    """Botones ✅/❌ que aparecen tras el parseo con Groq."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar todo", callback_data="entrada:confirmar"),
            InlineKeyboardButton("❌ Cancelar",       callback_data="entrada:cancelar"),
        ],
    ])


# ── Lista de productos del stock (inline, dinámico) ───────────
def kb_productos_stock(productos: list, prefix: str = "prod") -> InlineKeyboardMarkup:
    """
    Genera botones con los primeros 8 productos activos del stock.
    prefix: 'consumo' → callback 'consumo:prod:<nombre>'
    """
    MAX = 8
    buttons = []
    for p in productos[:MAX]:
        emoji = emoji_cat(p.get("categoria", "general"))
        label = f"{emoji} {p['producto'].title()} ({p['cantidad']} {p['unidad']})"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"{prefix}:prod:{p['producto']}")
        ])
    buttons.append([
        InlineKeyboardButton("✏️ Escribir nombre", callback_data=f"{prefix}:prod:__manual__")
    ])
    return InlineKeyboardMarkup(buttons)


# ── Lista de clientes (inline, dinámico) ─────────────────────
def kb_clientes(clientes: list) -> InlineKeyboardMarkup:
    """Genera botones con clientes registrados (máx 6 + opción manual)."""
    MAX = 6
    buttons = [
        [InlineKeyboardButton(c["nombre"], callback_data=f"despacho:cliente:{c['nombre']}")]
        for c in clientes[:MAX]
    ]
    buttons.append([
        InlineKeyboardButton("✏️ Otro cliente", callback_data="despacho:cliente:__manual__")
    ])
    return InlineKeyboardMarkup(buttons)


# ── Selección de productos para despacho (inline, dinámico) ──
def kb_productos_despacho(productos: list, seleccionados: list) -> InlineKeyboardMarkup:
    """
    Teclado de selección múltiple para despacho.
    Marca con ✓ los productos ya agregados al pedido.
    """
    MAX = 8
    buttons = []
    for p in productos[:MAX]:
        emoji = emoji_cat(p.get("categoria", "general"))
        marca = "✓ " if p["producto"] in seleccionados else ""
        label = f"{marca}{emoji} {p['producto'].title()} ({p['cantidad']} {p['unidad']})"
        buttons.append([
            InlineKeyboardButton(label, callback_data=f"despacho:prod:{p['producto']}")
        ])
    buttons.append([
        InlineKeyboardButton("✅ Listo, despachar", callback_data="despacho:prod:__listo__")
    ])
    return InlineKeyboardMarkup(buttons)


# ── Wizard de entrada: guardar / agregar otro / cancelar ──────
def kb_guardar_entrada() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💾 Guardar",          callback_data="wizard:guardar"),
            InlineKeyboardButton("➕ Otro producto",     callback_data="wizard:otro"),
        ],
        [InlineKeyboardButton("❌ Cancelar",             callback_data="wizard:cancelar")],
    ])


# ── Confirmar despacho final (inline, estático) ───────────────
def kb_confirmar_despacho() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar despacho", callback_data="despacho:confirmar"),
            InlineKeyboardButton("❌ Cancelar",            callback_data="despacho:cancelar"),
        ],
    ])
