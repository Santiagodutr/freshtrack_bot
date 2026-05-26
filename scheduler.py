"""
scheduler.py - Alertas automáticas diarias a las 8:00 AM
Ejecutar en terminal separada: python scheduler.py
"""

import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


async def enviar_alerta_diaria():
    """Envía reporte matutino al operador a las 8 AM."""
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID no configurado. Configúralo en .env")
        return

    bot = Bot(token=TOKEN)
    productos = db.consultar_proximos_vencer(dias=3)
    rep = db.reporte_diario()
    hoy = datetime.now().strftime("%d/%m/%Y")

    if not productos:
        mensaje = (
            f"☀️ *Buenos días — {hoy}*\n\n"
            f"✅ Sin alertas de vencimiento hoy.\n\n"
            f"📦 Stock: *{rep['stock_total_lotes']}* lotes activos\n"
            f"📏 Unidades: *{float(rep['stock_total_unidades']):.1f}*\n\n"
            f"_Usa /reporte para ver el detalle del día._"
        )
    else:
        lineas = [
            f"☀️ *Buenos días — {hoy}*\n",
            f"⚠️ *{len(productos)} producto(s) requieren atención:*\n"
        ]
        for p in productos:
            dias = p["dias_para_vencer"]
            if dias < 0:
                estado = f"🔴 VENCIDO hace {abs(dias)}d"
            elif dias == 0:
                estado = "🔴 VENCE HOY"
            elif dias == 1:
                estado = "🟠 vence MAÑANA"
            else:
                estado = f"🟡 vence en {dias}d"

            lineas.append(
                f"{estado}\n"
                f"   *{p['producto'].title()}* — {p['cantidad']} {p['unidad']}\n"
                f"   Lote: `{p['lote']}`"
            )

        lineas.append(
            f"\n📦 Stock: *{rep['stock_total_lotes']}* lotes | "
            f"*{float(rep['stock_total_unidades']):.1f}* uds totales\n"
            f"💡 _Usa /vencidos para dar de baja automáticamente._"
        )
        mensaje = "\n\n".join(lineas)

    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=mensaje,
        parse_mode="Markdown"
    )
    logger.info(f"Alerta diaria enviada a {ADMIN_CHAT_ID}")


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(enviar_alerta_diaria, "cron", hour=8, minute=0)
    scheduler.start()

    logger.info("Scheduler iniciado. Alertas diarias a las 8:00 AM.")
    logger.info("Presiona Ctrl+C para detener.")

    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScheduler detenido.")
