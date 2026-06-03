"""
ai_parser.py - Parser de inventario y movimientos usando Groq (LLM gratuito)
Convierte texto natural en datos estructurados para FreshTrack AI.
"""

import os
import json
from datetime import datetime
# pyrefly: ignore [missing-import]
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODELO = "llama-3.3-70b-versatile"

# ──────────────────────────────────────────────────────────
# PROMPT: Registro de entradas de inventario
# ──────────────────────────────────────────────────────────
_PROMPT_ENTRADA = """Eres un asistente que extrae datos de inventario de mensajes en español colombiano.

Tu unica tarea es devolver un JSON valido con esta estructura:
{
  "productos": [
    {
      "producto": "nombre en minusculas",
      "cantidad": numero,
      "unidad": "kg|g|litros|ml|unidades|cajas|bolsas|canastas",
      "fecha_vencimiento": "YYYY-MM-DD",
      "categoria": "lacteos|carnes|verduras|frutas|congelados|procesados|general"
    }
  ]
}

REGLAS:
1. Varios productos en un mensaje → todos en el array.
2. Fechas en DD/MM o DD/MM/YYYY. Sin año → usa el año actual (ANIO_ACTUAL).
3. Si la fecha ya paso este año → asume el siguiente año.
4. Sin unidad → "unidades".
5. Normaliza nombres: "tomates"→"tomate", "yogures"→"yogur", "lechugas"→"lechuga".
6. Asigna categoria segun el producto (lacteos: leche/yogur/queso; carnes: res/pollo/cerdo/salmon; verduras: lechuga/tomate/zanahoria; frutas: mango/banano; congelados: helado/pizza; procesados: embutidos/enlatados).
7. Sin datos extraibles → {"productos": []}.
8. SOLO JSON, sin texto adicional.

EJEMPLOS:
Input: "Lechuga 5 unidades 10/05, Tomate 8 kg 09/05"
Output: {"productos":[{"producto":"lechuga","cantidad":5,"unidad":"unidades","fecha_vencimiento":"ANIO_ACTUAL-05-10","categoria":"verduras"},{"producto":"tomate","cantidad":8,"unidad":"kg","fecha_vencimiento":"ANIO_ACTUAL-05-09","categoria":"verduras"}]}

Input: "Llegaron 12 litros de leche que vencen el 20 de junio"
Output: {"productos":[{"producto":"leche","cantidad":12,"unidad":"litros","fecha_vencimiento":"ANIO_ACTUAL-06-20","categoria":"lacteos"}]}
"""

# ──────────────────────────────────────────────────────────
# PROMPT: Consumo interno
# ──────────────────────────────────────────────────────────
_PROMPT_CONSUMO = """Eres un asistente que extrae datos de consumo interno de bodega de mensajes en español.

Devuelve SOLO este JSON:
{
  "items": [
    {
      "producto": "nombre en minusculas",
      "cantidad": numero,
      "motivo": "descripcion del motivo o null"
    }
  ]
}

REGLAS:
1. Extrae producto, cantidad y motivo (si se menciona).
2. Sin cantidad explicita → null (no incluir el item).
3. Normaliza nombres de productos.
4. SOLO JSON.

EJEMPLOS:
Input: "consumi 3 kg de lechuga para el almuerzo"
Output: {"items":[{"producto":"lechuga","cantidad":3,"motivo":"almuerzo"}]}

Input: "se dañaron 2 litros de leche"
Output: {"items":[{"producto":"leche","cantidad":2,"motivo":"producto dañado"}]}

Input: "usamos 5 unidades de queso y 1 kg de jamon para preparacion"
Output: {"items":[{"producto":"queso","cantidad":5,"motivo":"preparacion"},{"producto":"jamon","cantidad":1,"motivo":"preparacion"}]}
"""

# ──────────────────────────────────────────────────────────
# PROMPT: Despacho a cliente
# ──────────────────────────────────────────────────────────
_PROMPT_DESPACHO = """Eres un asistente que extrae datos de despacho a clientes de mensajes en español.

Devuelve SOLO este JSON:
{
  "cliente": "nombre del cliente",
  "items": [
    {
      "producto": "nombre en minusculas",
      "cantidad": numero
    }
  ],
  "observaciones": "texto adicional o null"
}

REGLAS:
1. Extrae el nombre del cliente (puede venir antes o despues de los productos).
2. Extrae cada producto y su cantidad.
3. Normaliza nombres de productos.
4. Si hay notas u observaciones adicionales, ponlas en "observaciones".
5. SOLO JSON.

EJEMPLOS:
Input: "despachar al cliente Exito: 10 kg de tomate y 5 cajas de lechuga"
Output: {"cliente":"Exito","items":[{"producto":"tomate","cantidad":10},{"producto":"lechuga","cantidad":5}],"observaciones":null}

Input: "salida para Carulla: 2 litros de leche, 3 kg de queso. Pedido urgente."
Output: {"cliente":"Carulla","items":[{"producto":"leche","cantidad":2},{"producto":"queso","cantidad":3}],"observaciones":"Pedido urgente"}
"""


def _llamar_groq(system_prompt: str, texto: str) -> dict:
    """Llama a la API de Groq y parsea el JSON de respuesta."""
    try:
        resp = client.chat.completions.create(
            model=MODELO,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto}
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"[AI] Error JSON: {e}")
        return {}
    except Exception as e:
        print(f"[AI] Error Groq: {e}")
        return {}


def _corregir_fechas(productos: list) -> list:
    """
    Valida y corrige fechas de productos.
    Si una fecha ya paso este año, la adelanta al siguiente.
    """
    validados = []
    for p in productos:
        try:
            fecha_dt = datetime.strptime(p.get("fecha_vencimiento", ""), "%Y-%m-%d")
            if fecha_dt.date() < datetime.now().date():
                fecha_dt = fecha_dt.replace(year=fecha_dt.year + 1)
                p["fecha_vencimiento"] = fecha_dt.strftime("%Y-%m-%d")
            validados.append(p)
        except (ValueError, TypeError):
            continue
    return validados


def parsear_mensaje(texto: str) -> dict:
    """
    Interpreta un mensaje de texto como registro de entrada de inventario.
    Retorna: {"productos": [...]}
    """
    anio = str(datetime.now().year)
    prompt = _PROMPT_ENTRADA.replace("ANIO_ACTUAL", anio)
    data = _llamar_groq(prompt, texto)
    productos = _corregir_fechas(data.get("productos", []))
    return {"productos": productos}


def parsear_consumo(texto: str) -> dict:
    """
    Interpreta un mensaje como consumo interno de bodega.
    Retorna: {"items": [{"producto": str, "cantidad": float, "motivo": str}]}
    """
    data = _llamar_groq(_PROMPT_CONSUMO, texto)
    return {"items": data.get("items", [])}


def parsear_despacho(texto: str) -> dict:
    """
    Interpreta un mensaje como despacho a un cliente.
    Retorna: {"cliente": str, "items": [...], "observaciones": str}
    """
    data = _llamar_groq(_PROMPT_DESPACHO, texto)
    return {
        "cliente": data.get("cliente", ""),
        "items": data.get("items", []),
        "observaciones": data.get("observaciones")
    }


if __name__ == "__main__":
    print("=== Test: Entrada de inventario ===")
    r = parsear_mensaje("Lechuga 5 unidades 10/12, Tomate 8 kg 09/12, Yogur 10 litros 15/12")
    print(json.dumps(r, indent=2, ensure_ascii=False))

    print("\n=== Test: Consumo interno ===")
    r = parsear_consumo("consumi 3 kg de lechuga para preparacion del almuerzo")
    print(json.dumps(r, indent=2, ensure_ascii=False))

    print("\n=== Test: Despacho a cliente ===")
    r = parsear_despacho("despachar a Éxito: 10 kg tomate, 5 cajas lechuga")
    print(json.dumps(r, indent=2, ensure_ascii=False))
