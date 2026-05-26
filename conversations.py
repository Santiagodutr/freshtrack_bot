"""
conversations.py - Flujos guiados (ConversationHandlers) para FreshTrack AI

Flujos implementados:
  - CONV_ENTRADA  : Wizard paso a paso para registrar nueva entrada
  - CONV_CONSUMO  : Selección interactiva de stock + cantidad + motivo
  - CONV_DESPACHO : Selección de cliente + productos en loop + confirmación
"""

import re
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

import keyboards as kb
import database as db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# ESTADOS
# ─────────────────────────────────────────────────────────────

# CONV_ENTRADA (wizard de nueva entrada)
PROD, CANT, UNID, FECH, CONF = range(5)

# CONV_CONSUMO
C_PROD, C_CANT, C_MOT = range(3)

# CONV_DESPACHO
D_CLI, D_PRODS, D_CANT, D_CONF = range(4)


# ─────────────────────────────────────────────────────────────
# UTILIDADES COMPARTIDAS
# ─────────────────────────────────────────────────────────────

def _parsear_fecha(texto: str) -> str | None:
    """
    Convierte texto a fecha en formato YYYY-MM-DD.
    Acepta: DD/MM  o  DD/MM/AAAA
    Si la fecha ya pasó en el año actual, la adelanta al siguiente año.
    """
    texto = texto.strip()
    anio = datetime.now().year

    patrones = [
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", True),
        (r"^(\d{1,2})/(\d{1,2})$",          False),
    ]
    for patron, tiene_anio in patrones:
        m = re.match(patron, texto)
        if m:
            dia, mes = int(m.group(1)), int(m.group(2))
            yr = int(m.group(3)) if tiene_anio else anio
            try:
                fecha_dt = datetime.strptime(f"{yr}-{mes:02d}-{dia:02d}", "%Y-%m-%d")
                if fecha_dt.date() < datetime.now().date():
                    fecha_dt = fecha_dt.replace(year=fecha_dt.year + 1)
                return fecha_dt.strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancelar — sale de cualquier conversación activa."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Operación cancelada.\n\nUsa el menú para empezar de nuevo.",
        reply_markup=kb.MENU_PRINCIPAL,
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────
# CONV_ENTRADA — Wizard paso a paso
# ─────────────────────────────────────────────────────────────

async def entrada_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el wizard al presionar 📦 Nueva Entrada."""
    context.user_data["wizard"] = {"guardados": []}
    await update.message.reply_text(
        "📦 *Nueva Entrada de Inventario*\n\n"
        "¿Qué producto llegó?\n"
        "_Escribe el nombre (ej: tomate, lechuga, yogur)_",
        parse_mode="Markdown",
    )
    return PROD


async def entrada_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre del producto."""
    nombre = update.message.text.strip().lower()
    context.user_data["wizard"]["producto"] = nombre
    await update.message.reply_text(
        f"¿Cuánto *{nombre}*? (escribe solo el número, ej: 3.5)",
        parse_mode="Markdown",
    )
    return CANT


async def entrada_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la cantidad numérica."""
    try:
        cantidad = float(update.message.text.replace(",", ".").strip())
        if cantidad <= 0:
            raise ValueError("cantidad <= 0")
    except ValueError:
        await update.message.reply_text(
            "⚠️ Escribe solo un número mayor a 0 (ej: *3.5* o *10*)",
            parse_mode="Markdown",
        )
        return CANT

    context.user_data["wizard"]["cantidad"] = cantidad
    await update.message.reply_text("¿En qué unidad?", reply_markup=kb.KB_UNIDADES)
    return UNID


async def entrada_unidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la unidad desde el InlineKeyboard."""
    query = update.callback_query
    await query.answer()
    unidad = query.data.split(":")[1]
    context.user_data["wizard"]["unidad"] = unidad
    prod = context.user_data["wizard"]["producto"]
    await query.edit_message_text(
        f"¿Fecha de vencimiento de *{prod}*?\n"
        f"Escribe DD/MM o DD/MM/AAAA _(ej: 15/06 o 15/06/2026)_",
        parse_mode="Markdown",
    )
    return FECH


async def entrada_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe y valida la fecha de vencimiento."""
    fecha = _parsear_fecha(update.message.text)
    if not fecha:
        await update.message.reply_text(
            "❌ No reconocí la fecha.\n\n"
            "Usa el formato *DD/MM* o *DD/MM/AAAA*\n"
            "Ejemplo: *15/06* o *15/06/2026*",
            parse_mode="Markdown",
        )
        return FECH

    context.user_data["wizard"]["fecha"] = fecha
    w = context.user_data["wizard"]
    emoji = kb.emoji_cat("general")

    await update.message.reply_text(
        f"✅ *Listo para guardar:*\n\n"
        f"{emoji} *{w['producto'].title()}* — {w['cantidad']} {w['unidad']} — vence *{fecha}*",
        parse_mode="Markdown",
        reply_markup=kb.kb_guardar_entrada(),
    )
    return CONF


async def entrada_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja Guardar / Otro producto / Cancelar del wizard."""
    query = update.callback_query
    await query.answer()
    accion = query.data.split(":")[1]
    user = update.effective_user
    w = context.user_data.get("wizard", {})

    if accion == "cancelar":
        await query.edit_message_text("❌ Entrada cancelada.")
        return ConversationHandler.END

    # Guardar producto actual (accion == 'guardar' o 'otro')
    try:
        db.registrar_producto(
            producto=w["producto"],
            cantidad=w["cantidad"],
            unidad=w["unidad"],
            fecha_vencimiento=w["fecha"],
            usuario_id=user.id,
            usuario_nombre=user.first_name,
        )
        w.setdefault("guardados", []).append(w["producto"].title())
        logger.info(f"[wizard] Guardado: {w['producto']} x{w['cantidad']} {w['unidad']}")
    except Exception as e:
        logger.error(f"[wizard] Error guardando {w.get('producto')}: {e}")
        await query.edit_message_text(f"❌ Error al guardar: {e}")
        return ConversationHandler.END

    if accion == "otro":
        ya = ", ".join(w["guardados"])
        await query.edit_message_text(
            f"✅ *{w['producto'].title()}* guardado.\n"
            f"_Ya registrados: {ya}_\n\n"
            f"¿Qué otro producto llegó?",
            parse_mode="Markdown",
        )
        return PROD

    # accion == 'guardar' → fin
    total = len(w["guardados"])
    nombres = ", ".join(w["guardados"])
    await query.edit_message_text(
        f"✅ *{total} producto(s) registrado(s):*\n_{nombres}_\n\n"
        f"Usa /stock para ver el inventario actualizado.",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


def get_conv_entrada() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📦 Nueva Entrada$"), entrada_inicio)
        ],
        states={
            PROD: [MessageHandler(filters.TEXT & ~filters.COMMAND, entrada_producto)],
            CANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, entrada_cantidad)],
            UNID: [CallbackQueryHandler(entrada_unidad, pattern="^unidad:")],
            FECH: [MessageHandler(filters.TEXT & ~filters.COMMAND, entrada_fecha)],
            CONF: [CallbackQueryHandler(entrada_confirmar, pattern="^wizard:")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
        conversation_timeout=300,
        name="conv_entrada",
    )


# ─────────────────────────────────────────────────────────────
# CONV_CONSUMO — Consumo interno guiado
# ─────────────────────────────────────────────────────────────

async def consumo_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de consumo al presionar 🔥 Consumo."""
    productos = db.consultar_stock(orden_fefo=True)
    if not productos:
        await update.message.reply_text(
            "📦 No hay stock activo.\n\n"
            "Registra productos primero con *📦 Nueva Entrada* o enviando texto libre.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    context.user_data["consumo"] = {"stock": productos}
    await update.message.reply_text(
        "🔥 *Consumo Interno*\n\n¿Qué producto vas a consumir?",
        parse_mode="Markdown",
        reply_markup=kb.kb_productos_stock(productos, prefix="consumo"),
    )
    return C_PROD


async def consumo_prod_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Producto seleccionado desde botón."""
    query = update.callback_query
    await query.answer()
    producto = query.data.split(":", 2)[2]

    if producto == "__manual__":
        await query.edit_message_text(
            "¿Qué producto vas a consumir? Escribe el nombre:"
        )
        return C_PROD

    stock = db.buscar_producto(producto)
    disponible = sum(p["cantidad"] for p in stock) if stock else 0
    unidad = stock[0]["unidad"] if stock else "uds"

    context.user_data["consumo"]["producto"] = producto
    context.user_data["consumo"]["unidad"] = unidad

    await query.edit_message_text(
        f"🔥 *{producto.title()}*\n\n"
        f"¿Cuánto vas a consumir? (disponible: *{disponible} {unidad}*)",
        parse_mode="Markdown",
    )
    return C_CANT


async def consumo_prod_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Producto escrito manualmente (tras pulsar ✏️ Escribir nombre)."""
    producto = update.message.text.strip().lower()
    stock = db.buscar_producto(producto)

    if not stock:
        await update.message.reply_text(
            f"❌ No hay stock de *{producto}*.\n\n"
            f"Intenta con otro nombre o usa /stock para ver el inventario.",
            parse_mode="Markdown",
        )
        return C_PROD

    disponible = sum(p["cantidad"] for p in stock)
    unidad = stock[0]["unidad"]
    context.user_data["consumo"]["producto"] = producto
    context.user_data["consumo"]["unidad"] = unidad

    await update.message.reply_text(
        f"¿Cuánto *{producto}*? (disponible: *{disponible} {unidad}*)",
        parse_mode="Markdown",
    )
    return C_CANT


async def consumo_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la cantidad a consumir."""
    try:
        cantidad = float(update.message.text.replace(",", ".").strip())
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Escribe solo un número mayor a 0 (ej: *3.5*)",
            parse_mode="Markdown",
        )
        return C_CANT

    context.user_data["consumo"]["cantidad"] = cantidad
    await update.message.reply_text("¿Motivo del consumo?", reply_markup=kb.KB_MOTIVOS)
    return C_MOT


async def consumo_motivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el motivo y ejecuta el consumo en base de datos."""
    query = update.callback_query
    await query.answer()
    motivo = query.data.split(":", 1)[1]
    user = update.effective_user
    c = context.user_data["consumo"]

    res = db.consumir_producto(
        nombre=c["producto"],
        cantidad=c["cantidad"],
        motivo=motivo,
        usuario_id=user.id,
    )

    if res["exito"]:
        stock_restante = db.buscar_producto(c["producto"])
        restante = sum(p["cantidad"] for p in stock_restante) if stock_restante else 0
        await query.edit_message_text(
            f"✅ *Consumo registrado:*\n\n"
            f"🔥 *{c['producto'].title()}* — {c['cantidad']} {c['unidad']}\n"
            f"📝 Motivo: _{motivo}_\n"
            f"📦 Stock restante: *{restante} {c['unidad']}*",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            f"❌ {res['error']}\n\nUsa /stock para ver el stock disponible.",
            parse_mode="Markdown",
        )

    return ConversationHandler.END


def get_conv_consumo() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔥 Consumo$"), consumo_inicio)
        ],
        states={
            C_PROD: [
                CallbackQueryHandler(consumo_prod_btn, pattern="^consumo:prod:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, consumo_prod_texto),
            ],
            C_CANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, consumo_cantidad)],
            C_MOT: [CallbackQueryHandler(consumo_motivo, pattern="^motivo:")],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
        conversation_timeout=300,
        name="conv_consumo",
    )


# ─────────────────────────────────────────────────────────────
# CONV_DESPACHO — Despacho a cliente guiado
# ─────────────────────────────────────────────────────────────

async def despacho_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de despacho al presionar 🚚 Despacho."""
    stock = db.consultar_stock(orden_fefo=True)
    if not stock:
        await update.message.reply_text(
            "📦 No hay stock activo para despachar.\n\n"
            "Registra productos primero con *📦 Nueva Entrada*.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    context.user_data["despacho"] = {
        "cliente": None,
        "items": [],
        "current_prod": None,
        "current_unidad": None,
        "stock": stock,
    }

    clientes = db.listar_clientes()
    texto = "🚚 *Despacho a Cliente*\n\n¿Para qué cliente?"

    if clientes:
        await update.message.reply_text(
            texto, parse_mode="Markdown",
            reply_markup=kb.kb_clientes(clientes),
        )
    else:
        await update.message.reply_text(
            texto + "\n\n_No hay clientes registrados. Escribe el nombre:_",
            parse_mode="Markdown",
        )
    return D_CLI


async def despacho_cliente_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cliente seleccionado desde botón."""
    query = update.callback_query
    await query.answer()
    cliente = query.data.split(":", 2)[2]

    if cliente == "__manual__":
        await query.edit_message_text("¿Para qué cliente? Escribe el nombre:")
        return D_CLI

    context.user_data["despacho"]["cliente"] = cliente
    d = context.user_data["despacho"]
    seleccionados = [i["producto"] for i in d["items"]]

    await query.edit_message_text(
        f"🚚 *Despacho → {cliente}*\n\n¿Qué productos? Toca para agregar:",
        parse_mode="Markdown",
        reply_markup=kb.kb_productos_despacho(d["stock"], seleccionados),
    )
    return D_PRODS


async def despacho_cliente_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cliente escrito manualmente."""
    cliente = update.message.text.strip()
    context.user_data["despacho"]["cliente"] = cliente
    d = context.user_data["despacho"]
    seleccionados = [i["producto"] for i in d["items"]]

    await update.message.reply_text(
        f"🚚 *Despacho → {cliente}*\n\n¿Qué productos? Toca para agregar:",
        parse_mode="Markdown",
        reply_markup=kb.kb_productos_despacho(d["stock"], seleccionados),
    )
    return D_PRODS


async def despacho_prod_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Producto seleccionado o botón 'Listo' presionado."""
    query = update.callback_query
    await query.answer()
    producto = query.data.split(":", 2)[2]
    d = context.user_data["despacho"]

    # ── "Listo, despachar" ──
    if producto == "__listo__":
        if not d["items"]:
            await query.answer("⚠️ Agrega al menos un producto primero", show_alert=True)
            return D_PRODS

        cliente = d["cliente"]
        lineas = [f"🚚 *Resumen despacho → {cliente}*\n"]
        for item in d["items"]:
            lineas.append(
                f"• *{item['producto'].title()}* — {item['cantidad']} {item['unidad']}"
            )
        lineas.append("\n¿Confirmamos?")

        await query.edit_message_text(
            "\n".join(lineas),
            parse_mode="Markdown",
            reply_markup=kb.kb_confirmar_despacho(),
        )
        return D_CONF

    # ── Producto seleccionado ──
    stock_prod = db.buscar_producto(producto)
    disponible = sum(p["cantidad"] for p in stock_prod) if stock_prod else 0
    unidad = stock_prod[0]["unidad"] if stock_prod else "uds"

    d["current_prod"] = producto
    d["current_unidad"] = unidad

    await query.edit_message_text(
        f"¿Cuánto *{producto.title()}*? (disponible: *{disponible} {unidad}*)",
        parse_mode="Markdown",
    )
    return D_CANT


async def despacho_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la cantidad del producto seleccionado."""
    try:
        cantidad = float(update.message.text.replace(",", ".").strip())
        if cantidad <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Escribe solo un número mayor a 0 (ej: *3.5*)",
            parse_mode="Markdown",
        )
        return D_CANT

    d = context.user_data["despacho"]
    producto = d["current_prod"]
    unidad = d["current_unidad"]

    # Actualizar o agregar item
    d["items"] = [i for i in d["items"] if i["producto"] != producto]
    d["items"].append({"producto": producto, "cantidad": cantidad, "unidad": unidad})

    seleccionados = [i["producto"] for i in d["items"]]
    cliente = d["cliente"]
    ya_str = ", ".join(
        f"{i['producto'].title()} {i['cantidad']} {i['unidad']}" for i in d["items"]
    )

    await update.message.reply_text(
        f"✓ *{producto.title()}* {cantidad} {unidad} agregado.\n\n"
        f"🚚 *{cliente}* — ¿Más productos?\n"
        f"_Agregados: {ya_str}_",
        parse_mode="Markdown",
        reply_markup=kb.kb_productos_despacho(d["stock"], seleccionados),
    )
    return D_PRODS


async def despacho_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirmación final: ejecuta el despacho o cancela."""
    query = update.callback_query
    await query.answer()
    accion = query.data.split(":")[1]

    if accion == "cancelar":
        await query.edit_message_text("❌ Despacho cancelado.")
        return ConversationHandler.END

    user = update.effective_user
    d = context.user_data["despacho"]

    resultado = db.registrar_despacho(
        cliente_nombre=d["cliente"],
        items=d["items"],
        usuario_id=user.id,
        usuario_nombre=user.first_name,
    )

    lineas = [
        f"🚚 *Despacho #{resultado['despacho_id']} registrado*\n",
        f"👥 Cliente: *{resultado['cliente']}*\n",
    ]
    if resultado["productos"]:
        lineas.append("*Productos despachados (FEFO):*")
        for p in resultado["productos"]:
            lineas.append(f"  ✅ *{p['producto'].title()}* — {p['cantidad']} {p['unidad']}")
    if resultado["errores"]:
        lineas.append("\n⚠️ *Advertencias:*")
        for e in resultado["errores"]:
            lineas.append(f"  • {e}")
    lineas.append("\n_Usa /reporte para ver los movimientos del día._")

    await query.edit_message_text("\n".join(lineas), parse_mode="Markdown")
    return ConversationHandler.END


def get_conv_despacho() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🚚 Despacho$"), despacho_inicio)
        ],
        states={
            D_CLI: [
                CallbackQueryHandler(despacho_cliente_btn,  pattern="^despacho:cliente:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, despacho_cliente_texto),
            ],
            D_PRODS: [
                CallbackQueryHandler(despacho_prod_btn, pattern="^despacho:prod:"),
            ],
            D_CANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, despacho_cantidad)],
            D_CONF: [
                CallbackQueryHandler(
                    despacho_confirmar,
                    pattern="^despacho:(confirmar|cancelar)$"
                ),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
        conversation_timeout=300,
        name="conv_despacho",
    )
