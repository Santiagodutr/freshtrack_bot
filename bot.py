"""
bot.py - FreshTrack AI Bot de Telegram v2
Sistema completo de control de inventario para bodegas de perecederos.

Comandos:
  /start       - Bienvenida
  /stock       - Inventario ordenado FEFO
  /alertas     - Productos que vencen en ≤3 días
  /vencidos    - Dar de baja productos vencidos
  /stats       - Estadísticas generales
  /reporte     - Reporte de movimientos del día
  /buscar      - Buscar producto por nombre
  /consumir    - Registrar consumo interno (FEFO)
  /despachar   - Registrar despacho a cliente (FEFO)
  /clientes    - Ver lista de clientes
  /addcliente  - Agregar nuevo cliente
  /ayuda       - Ayuda completa
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

import database as db
import ai_parser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("Falta TELEGRAM_BOT_TOKEN en el archivo .env")


# ============================================================
# UTILIDADES
# ============================================================

def _emoji_dias(dias: int) -> str:
    if dias < 0:
        return "🔴"
    if dias <= 1:
        return "🔴"
    if dias <= 3:
        return "🟠"
    if dias <= 7:
        return "🟡"
    return "🟢"


def _texto_dias(dias: int) -> str:
    if dias < 0:
        return f"VENCIDO hace {abs(dias)}d"
    if dias == 0:
        return "VENCE HOY"
    if dias == 1:
        return "vence MAÑANA"
    return f"vence en {dias}d"


def _truncar(texto: str, limite: int = 4000) -> str:
    if len(texto) > limite:
        return texto[:limite] + "\n\n_...lista truncada_"
    return texto


# ============================================================
# /start y /ayuda
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mensaje = (
        f"👋 Hola *{user.first_name}*, soy *FreshTrack AI*\n\n"
        f"🥬 Control de inventario para bodegas de perecederos.\n\n"
        f"📥 *Registrar entrada* — escribe en lenguaje natural:\n"
        f"`Lechuga 5 kg 10/12`\n"
        f"`Tomate 8 kg 09/12, Yogur 10 litros 15/12`\n\n"
        f"⚙️ *Comandos disponibles:*\n"
        f"/stock — Inventario FEFO completo\n"
        f"/alertas — Próximos a vencer (≤3 días)\n"
        f"/vencidos — Dar de baja vencidos\n"
        f"/buscar `[producto]` — Buscar en stock\n"
        f"/consumir `[producto] [cantidad]` — Consumo interno\n"
        f"/despachar `[cliente]: [productos]` — Salida a cliente\n"
        f"/clientes — Lista de clientes\n"
        f"/addcliente `[nombre]` — Agregar cliente\n"
        f"/reporte — Resumen del día\n"
        f"/stats — Estadísticas globales\n"
        f"/ayuda — Esta ayuda\n\n"
        f"🆔 Tu chat ID: `{update.effective_chat.id}`"
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "📖 *AYUDA — FreshTrack AI*\n\n"
        "*📥 REGISTRAR ENTRADA (texto libre):*\n"
        "`Lechuga 5 kg 10/12`\n"
        "`Tomate 8 kg 09/12, Yogur 10 litros 15/12`\n"
        "`Llegaron 12 cajas de queso que vencen el 20 de junio`\n\n"
        "*🔍 BUSCAR PRODUCTO:*\n"
        "`/buscar tomate`\n\n"
        "*📤 CONSUMO INTERNO:*\n"
        "`/consumir 5 kg de lechuga para almuerzo`\n"
        "`/consumir 3 litros de leche — dañada`\n\n"
        "*🚚 DESPACHO A CLIENTE:*\n"
        "`/despachar Éxito: 10 kg tomate, 5 cajas lechuga`\n"
        "`/despachar cliente Carulla 3 kg queso y 2 litros leche`\n\n"
        "*👥 CLIENTES:*\n"
        "`/clientes` — Ver todos\n"
        "`/addcliente Almacenes Éxito`\n\n"
        "*📊 REPORTES:*\n"
        "`/stock` — Inventario FEFO\n"
        "`/alertas` — Próximos a vencer\n"
        "`/vencidos` — Dar de baja vencidos\n"
        "`/reporte` — Movimientos del día\n"
        "`/stats` — Estadísticas globales"
    )
    await update.message.reply_text(mensaje, parse_mode="Markdown")


# ============================================================
# /stock
# ============================================================

async def consultar_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    productos = db.consultar_stock(orden_fefo=True)

    if not productos:
        await update.message.reply_text(
            "📦 El inventario está vacío.\n\n"
            "Envíame un mensaje con productos para registrar una entrada."
        )
        return

    lineas = ["📦 *INVENTARIO ACTUAL — FEFO*\n",
              "_Lo que vence primero aparece primero_\n"]

    for p in productos:
        dias = p["dias_para_vencer"]
        emoji = _emoji_dias(dias)
        estado = _texto_dias(dias)
        cat = f" _[{p.get('categoria','general')}]_" if p.get("categoria") else ""
        lineas.append(
            f"{emoji} *{p['producto'].title()}*{cat}\n"
            f"   {p['cantidad']} {p['unidad']} | Lote: `{p['lote']}`\n"
            f"   Vence: {p['fecha_vencimiento']} ({estado})"
        )

    await update.message.reply_text(
        _truncar("\n\n".join(lineas)), parse_mode="Markdown"
    )


# ============================================================
# /alertas
# ============================================================

async def alertas_vencimiento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    productos = db.consultar_proximos_vencer(dias=3)

    if not productos:
        await update.message.reply_text(
            "✅ Sin alertas. Ningún producto vence en los próximos 3 días."
        )
        return

    lineas = [f"⚠️ *ALERTAS DE VENCIMIENTO* ({len(productos)} producto(s))\n",
              "_Despacha o consume estos primero (FEFO):_\n"]

    for p in productos:
        dias = p["dias_para_vencer"]
        emoji = _emoji_dias(dias)
        estado = _texto_dias(dias)
        lineas.append(
            f"{emoji} *{p['producto'].title()}* — {estado}\n"
            f"   {p['cantidad']} {p['unidad']} | Lote: `{p['lote']}`\n"
            f"   Vence: {p['fecha_vencimiento']}"
        )

    await update.message.reply_text(
        _truncar("\n\n".join(lineas)), parse_mode="Markdown"
    )


# ============================================================
# /vencidos
# ============================================================

async def dar_baja_vencidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    vencidos = db.dar_de_baja_vencidos(usuario_id=user_id)

    if not vencidos:
        await update.message.reply_text("✅ No hay productos vencidos para dar de baja.")
        return

    lineas = [f"🗑 *BAJA AUTOMÁTICA — {len(vencidos)} lote(s) vencido(s):*\n"]
    for p in vencidos:
        lineas.append(
            f"❌ *{p['producto'].title()}* — {p['cantidad']} {p['unidad']}\n"
            f"   Lote: `{p['lote']}` | Venció: {p['fecha_vencimiento']}"
        )
    lineas.append(
        "\n💡 _Registrado como merma en el historial de movimientos._"
    )
    await update.message.reply_text("\n\n".join(lineas), parse_mode="Markdown")


# ============================================================
# /stats
# ============================================================

async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.estadisticas_generales()
    proximos = db.consultar_proximos_vencer(dias=3)

    await update.message.reply_text(
        "📊 *ESTADÍSTICAS DEL INVENTARIO*\n\n"
        f"📦 Lotes activos: *{stats['total_lotes']}*\n"
        f"🥬 Productos únicos: *{stats['productos_unicos']}*\n"
        f"📏 Unidades totales: *{float(stats['total_unidades']):.1f}*\n"
        f"🗑 Lotes dados de baja: *{stats['bajas']}*\n"
        f"🚚 Despachos realizados: *{stats['total_despachos']}*\n"
        f"⚠️ Próximos a vencer (3d): *{len(proximos)}*\n\n"
        f"_Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}_",
        parse_mode="Markdown"
    )


# ============================================================
# /reporte
# ============================================================

async def reporte_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rep = db.reporte_diario()
    hoy = datetime.now().strftime("%d/%m/%Y")

    await update.message.reply_text(
        f"📋 *REPORTE DEL DÍA — {hoy}*\n\n"
        f"📥 Entradas registradas: *{rep['entradas_hoy']:.1f}* uds\n"
        f"🔄 Consumo interno: *{rep['consumos_hoy']:.1f}* uds\n"
        f"🗑 Bajas por vencimiento: *{rep['bajas_hoy']:.1f}* uds\n"
        f"🚚 Despachos a clientes: *{rep['despachos_hoy']}*\n\n"
        f"📦 Stock actual — Lotes: *{rep['stock_total_lotes']}* | "
        f"Unidades: *{float(rep['stock_total_unidades']):.1f}*\n"
        f"⚠️ Próximos a vencer (≤3d): *{rep['proximos_vencer']}*",
        parse_mode="Markdown"
    )


# ============================================================
# /buscar
# ============================================================

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔍 *Uso:* `/buscar [nombre del producto]`\n\n"
            "Ejemplo: `/buscar tomate`",
            parse_mode="Markdown"
        )
        return

    nombre = " ".join(context.args)
    productos = db.buscar_producto(nombre)

    if not productos:
        await update.message.reply_text(
            f"🔍 No se encontró stock activo de *{nombre}*.\n\n"
            f"Usa /stock para ver todo el inventario.",
            parse_mode="Markdown"
        )
        return

    lineas = [f"🔍 *BÚSQUEDA: '{nombre}'* — {len(productos)} lote(s)\n"]
    stock_total = sum(p["cantidad"] for p in productos)
    unidad = productos[0]["unidad"]
    lineas.append(f"_Stock total: {stock_total} {unidad}_\n")

    for p in productos:
        dias = p["dias_para_vencer"]
        emoji = _emoji_dias(dias)
        estado = _texto_dias(dias)
        lineas.append(
            f"{emoji} *{p['producto'].title()}* — {p['cantidad']} {p['unidad']}\n"
            f"   Lote: `{p['lote']}` | {estado}\n"
            f"   Vence: {p['fecha_vencimiento']}"
        )

    await update.message.reply_text(
        _truncar("\n\n".join(lineas)), parse_mode="Markdown"
    )


# ============================================================
# /consumir
# ============================================================

async def consumir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🔄 *Uso:* `/consumir [descripción]`\n\n"
            "Ejemplos:\n"
            "`/consumir 5 kg de lechuga`\n"
            "`/consumir 3 litros de leche — dañada`\n"
            "`/consumir 2 kg tomate y 1 kg zanahoria para cocina`",
            parse_mode="Markdown"
        )
        return

    texto = " ".join(context.args)
    user = update.effective_user

    msg = await update.message.reply_text("🤖 _Procesando consumo..._", parse_mode="Markdown")

    resultado = ai_parser.parsear_consumo(texto)
    items = resultado.get("items", [])

    if not items:
        await msg.edit_text(
            "❌ No pude identificar el producto y cantidad.\n\n"
            "*Ejemplo:* `/consumir 5 kg de lechuga`",
            parse_mode="Markdown"
        )
        return

    lineas = [f"🔄 *CONSUMO INTERNO REGISTRADO:*\n"]
    errores = []

    for item in items:
        res = db.consumir_producto(
            nombre=item["producto"],
            cantidad=item["cantidad"],
            motivo=item.get("motivo") or "Consumo interno",
            usuario_id=user.id
        )
        if res["exito"]:
            lotes_str = ", ".join(
                f"`{l['lote']}` ({l['cantidad_descontada']} {l['unidad']})"
                for l in res["lotes"]
            )
            lineas.append(
                f"✅ *{item['producto'].title()}* — {item['cantidad']} descontado(s)\n"
                f"   Lotes FEFO: {lotes_str}"
            )
        else:
            errores.append(f"❌ *{item['producto'].title()}*: {res['error']}")

    if errores:
        lineas.append("\n*Errores:*\n" + "\n".join(errores))

    lineas.append("\n_Usa /stock para ver el inventario actualizado._")
    await msg.edit_text("\n\n".join(lineas), parse_mode="Markdown")


# ============================================================
# /despachar
# ============================================================

async def despachar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "🚚 *Uso:* `/despachar [cliente]: [productos]`\n\n"
            "Ejemplos:\n"
            "`/despachar Éxito: 10 kg tomate, 5 unidades lechuga`\n"
            "`/despachar cliente Carulla 3 kg queso y 2 litros leche`\n"
            "`/despachar Olimpica 8 kg salmon`",
            parse_mode="Markdown"
        )
        return

    texto = " ".join(context.args)
    user = update.effective_user

    msg = await update.message.reply_text("🤖 _Procesando despacho..._", parse_mode="Markdown")

    resultado_ai = ai_parser.parsear_despacho(texto)
    cliente = resultado_ai.get("cliente", "").strip()
    items = resultado_ai.get("items", [])
    obs = resultado_ai.get("observaciones")

    if not cliente or not items:
        await msg.edit_text(
            "❌ No pude identificar el cliente o los productos.\n\n"
            "*Ejemplo:* `/despachar Éxito: 10 kg tomate, 5 unidades lechuga`",
            parse_mode="Markdown"
        )
        return

    resultado = db.registrar_despacho(
        cliente_nombre=cliente,
        items=items,
        observaciones=obs,
        usuario_id=user.id,
        usuario_nombre=user.first_name
    )

    lineas = [
        f"🚚 *DESPACHO #{resultado['despacho_id']} REGISTRADO*\n",
        f"👥 Cliente: *{resultado['cliente']}*\n"
    ]

    if resultado["productos"]:
        lineas.append("*Productos despachados (FEFO):*")
        for p in resultado["productos"]:
            lineas.append(f"  ✅ *{p['producto'].title()}* — {p['cantidad']} {p['unidad']}")

    if resultado["errores"]:
        lineas.append("\n*Advertencias:*")
        for e in resultado["errores"]:
            lineas.append(f"  ⚠️ {e}")

    if obs:
        lineas.append(f"\n📝 Obs: _{obs}_")

    lineas.append("\n_Usa /reporte para ver los movimientos del día._")
    await msg.edit_text("\n".join(lineas), parse_mode="Markdown")


# ============================================================
# /clientes
# ============================================================

async def clientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lista = db.listar_clientes()

    if not lista:
        await update.message.reply_text(
            "👥 No hay clientes registrados.\n\n"
            "Usa `/addcliente [nombre]` para agregar uno.",
            parse_mode="Markdown"
        )
        return

    lineas = [f"👥 *CLIENTES REGISTRADOS ({len(lista)})*\n"]
    for c in lista:
        info = [f"*{c['nombre']}*"]
        if c.get("telefono"):
            info.append(f"📞 {c['telefono']}")
        if c.get("direccion"):
            info.append(f"📍 {c['direccion']}")
        lineas.append("• " + " | ".join(info))

    lineas.append(
        f"\n_Usa `/addcliente [nombre]` para agregar un cliente._\n"
        f"_Usa `/despachar [cliente]: [productos]` para registrar una salida._"
    )
    await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")


# ============================================================
# /addcliente
# ============================================================

async def addcliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "👥 *Uso:* `/addcliente [nombre del cliente]`\n\n"
            "Ejemplo: `/addcliente Almacenes Éxito`",
            parse_mode="Markdown"
        )
        return

    nombre = " ".join(context.args)
    resultado = db.registrar_cliente(nombre)

    if resultado["exito"]:
        cliente = resultado["cliente"]
        await update.message.reply_text(
            f"✅ *Cliente registrado:*\n\n"
            f"👥 Nombre: *{cliente['nombre']}*\n"
            f"🆔 ID: `{cliente['id']}`\n\n"
            f"_Ya puedes usar `/despachar {cliente['nombre']}: [productos]`_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ {resultado['error']}",
            parse_mode="Markdown"
        )


# ============================================================
# HANDLER DE MENSAJES (REGISTRO DE ENTRADAS)
# ============================================================

async def procesar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa mensajes de texto como registros de entrada de inventario."""
    texto = update.message.text
    user = update.effective_user

    msg = await update.message.reply_text("🤖 _Procesando con IA..._", parse_mode="Markdown")

    resultado = ai_parser.parsear_mensaje(texto)
    productos = resultado.get("productos", [])

    if not productos:
        await msg.edit_text(
            "❌ No identifiqué productos en tu mensaje.\n\n"
            "*Ejemplos válidos:*\n"
            "`Lechuga 5 kg 10/12`\n"
            "`Tomate 8 unidades 09/12, Yogur 10 litros 15/12`\n"
            "`Llegaron 12 cajas de queso que vencen el 20 de junio`\n\n"
            "Usa /ayuda para ver más ejemplos.",
            parse_mode="Markdown"
        )
        return

    lineas = [f"📝 *{len(productos)} producto(s) registrado(s):*\n"]
    for p in productos:
        try:
            db.registrar_producto(
                producto=p["producto"],
                cantidad=p["cantidad"],
                unidad=p.get("unidad", "unidades"),
                fecha_vencimiento=p["fecha_vencimiento"],
                categoria=p.get("categoria", "general"),
                usuario_id=user.id,
                usuario_nombre=user.first_name
            )
            cat = f" [{p.get('categoria','general')}]" if p.get("categoria") else ""
            lineas.append(
                f"✅ *{p['producto'].title()}*{cat}\n"
                f"   {p['cantidad']} {p.get('unidad','unidades')} | "
                f"Vence: {p['fecha_vencimiento']}"
            )
        except Exception as e:
            logger.error(f"Error registrando {p}: {e}")
            lineas.append(f"❌ Error con: *{p.get('producto','?')}*")

    lineas.append("\n_Usa /stock para ver el inventario actualizado (FEFO)._")
    await msg.edit_text("\n\n".join(lineas), parse_mode="Markdown")


# ============================================================
# MAIN
# ============================================================

def main():
    if not db.test_connection():
        print("\n[ERROR] No se pudo conectar a Supabase.")
        print("Revisa SUPABASE_URL y SUPABASE_KEY en tu .env\n")
        return

    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("help", ayuda))
    app.add_handler(CommandHandler("stock", consultar_stock))
    app.add_handler(CommandHandler("alertas", alertas_vencimiento))
    app.add_handler(CommandHandler("vencidos", dar_baja_vencidos))
    app.add_handler(CommandHandler("stats", estadisticas))
    app.add_handler(CommandHandler("reporte", reporte_diario))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("consumir", consumir))
    app.add_handler(CommandHandler("despachar", despachar))
    app.add_handler(CommandHandler("clientes", clientes))
    app.add_handler(CommandHandler("addcliente", addcliente))

    # Mensajes de texto = entradas de inventario
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_mensaje))

    print("=" * 60)
    print("🥬 FreshTrack AI Bot v2")
    print("=" * 60)
    print("Bot iniciado. Esperando mensajes en Telegram...")
    print("Presiona Ctrl+C para detener.\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    main()
