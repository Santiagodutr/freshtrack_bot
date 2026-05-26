"""
database.py - Gestión de base de datos Supabase para FreshTrack AI v2
Operador de bodega - Distribuidora de Perecederos
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def test_connection() -> bool:
    """Verifica que la conexion a Supabase funciona."""
    try:
        supabase.table("inventario").select("id").limit(1).execute()
        print("[DB] Conexion a Supabase exitosa.")
        return True
    except Exception as e:
        print(f"[DB] Error de conexion: {e}")
        return False


def _dias_hasta(fecha_str: str) -> int:
    """Calcula dias desde hoy hasta una fecha YYYY-MM-DD."""
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    return (fecha - datetime.now().date()).days


# ============================================================
# INVENTARIO — ENTRADAS
# ============================================================

def registrar_producto(producto: str, cantidad: float, unidad: str,
                       fecha_vencimiento: str, categoria: str = "general",
                       precio_unitario: float = 0,
                       usuario_id: int = None, usuario_nombre: str = None) -> int:
    """Registra entrada de producto. Retorna el ID del lote creado."""
    lote = f"{producto[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    response = supabase.table("inventario").insert({
        "producto": producto.lower().strip(),
        "categoria": categoria,
        "cantidad": cantidad,
        "unidad": unidad,
        "fecha_vencimiento": fecha_vencimiento,
        "lote": lote,
        "estado": "activo",
        "precio_unitario": precio_unitario,
        "usuario_id": usuario_id,
        "usuario_nombre": usuario_nombre
    }).execute()

    inventario_id = response.data[0]["id"]

    supabase.table("movimientos").insert({
        "inventario_id": inventario_id,
        "tipo": "ENTRADA",
        "cantidad": cantidad,
        "motivo": "Registro de entrada",
        "usuario_id": usuario_id
    }).execute()

    return inventario_id


# ============================================================
# INVENTARIO — CONSULTAS
# ============================================================

def consultar_stock(orden_fefo: bool = True) -> List[Dict]:
    """Consulta stock activo. Ordenado FEFO por defecto."""
    query = (
        supabase.table("inventario")
        .select("*")
        .eq("estado", "activo")
        .gt("cantidad", 0)
    )
    if orden_fefo:
        query = query.order("fecha_vencimiento", desc=False)
    else:
        query = query.order("fecha_registro", desc=True)

    productos = query.execute().data
    for p in productos:
        p["dias_para_vencer"] = _dias_hasta(p["fecha_vencimiento"])
    return productos


def consultar_proximos_vencer(dias: int = 3) -> List[Dict]:
    """Productos que vencen en los proximos N dias (incluye vencidos)."""
    fecha_limite = (datetime.now().date() + timedelta(days=dias)).isoformat()
    productos = (
        supabase.table("inventario")
        .select("*")
        .eq("estado", "activo")
        .gt("cantidad", 0)
        .lte("fecha_vencimiento", fecha_limite)
        .order("fecha_vencimiento", desc=False)
        .execute()
        .data
    )
    for p in productos:
        p["dias_para_vencer"] = _dias_hasta(p["fecha_vencimiento"])
    return productos


def buscar_producto(nombre: str) -> List[Dict]:
    """Busca productos activos por nombre (busqueda parcial, insensible a mayusculas)."""
    productos = (
        supabase.table("inventario")
        .select("*")
        .eq("estado", "activo")
        .gt("cantidad", 0)
        .ilike("producto", f"%{nombre.lower().strip()}%")
        .order("fecha_vencimiento", desc=False)
        .execute()
        .data
    )
    for p in productos:
        p["dias_para_vencer"] = _dias_hasta(p["fecha_vencimiento"])
    return productos


def estadisticas_generales() -> Dict:
    """Estadisticas globales del inventario."""
    activos = (
        supabase.table("inventario")
        .select("cantidad, producto")
        .eq("estado", "activo")
        .gt("cantidad", 0)
        .execute()
        .data
    )

    bajas_count = (
        supabase.table("inventario")
        .select("id", count="exact")
        .eq("estado", "baja")
        .execute()
        .count or 0
    )

    despachos_count = (
        supabase.table("despachos")
        .select("id", count="exact")
        .execute()
        .count or 0
    )

    return {
        "total_lotes": len(activos),
        "total_unidades": sum(p["cantidad"] for p in activos),
        "productos_unicos": len(set(p["producto"] for p in activos)),
        "bajas": bajas_count,
        "total_despachos": despachos_count
    }


# ============================================================
# INVENTARIO — BAJAS Y CONSUMO
# ============================================================

def dar_de_baja(inventario_id: int, motivo: str = "Vencido",
                usuario_id: int = None) -> bool:
    """Da de baja un lote especifico."""
    resp = (
        supabase.table("inventario")
        .select("cantidad")
        .eq("id", inventario_id)
        .execute()
    )
    if not resp.data:
        return False

    cantidad = resp.data[0]["cantidad"]
    supabase.table("inventario").update({
        "estado": "baja", "cantidad": 0
    }).eq("id", inventario_id).execute()

    supabase.table("movimientos").insert({
        "inventario_id": inventario_id,
        "tipo": "BAJA",
        "cantidad": cantidad,
        "motivo": motivo,
        "usuario_id": usuario_id
    }).execute()
    return True


def dar_de_baja_vencidos(usuario_id: int = None) -> List[Dict]:
    """Da de baja automatica todos los productos vencidos. Retorna la lista."""
    hoy = datetime.now().date().isoformat()
    vencidos = (
        supabase.table("inventario")
        .select("*")
        .eq("estado", "activo")
        .gt("cantidad", 0)
        .lt("fecha_vencimiento", hoy)
        .execute()
        .data
    )
    for p in vencidos:
        dar_de_baja(p["id"], motivo="Vencido - baja automatica", usuario_id=usuario_id)
    return vencidos


def consumir_producto(nombre: str, cantidad: float,
                      motivo: str = "Consumo interno",
                      usuario_id: int = None) -> Dict:
    """
    Descuenta cantidad del inventario aplicando FEFO.
    Afecta primero el lote que vence mas pronto.
    Retorna dict con resultado y lotes afectados.
    """
    lotes = (
        supabase.table("inventario")
        .select("*")
        .eq("estado", "activo")
        .gt("cantidad", 0)
        .ilike("producto", f"%{nombre.lower().strip()}%")
        .order("fecha_vencimiento", desc=False)
        .execute()
        .data
    )

    if not lotes:
        return {"exito": False, "error": f"No hay stock activo de '{nombre}'"}

    stock_total = sum(l["cantidad"] for l in lotes)
    if cantidad > stock_total:
        return {
            "exito": False,
            "error": (
                f"Stock insuficiente de '{nombre}'. "
                f"Disponible: {stock_total} {lotes[0]['unidad']}"
            )
        }

    lotes_afectados = []
    restante = cantidad

    for lote in lotes:
        if restante <= 0:
            break
        a_descontar = min(lote["cantidad"], restante)
        nueva_cantidad = lote["cantidad"] - a_descontar
        nuevo_estado = "agotado" if nueva_cantidad == 0 else "activo"

        supabase.table("inventario").update({
            "cantidad": nueva_cantidad,
            "estado": nuevo_estado
        }).eq("id", lote["id"]).execute()

        supabase.table("movimientos").insert({
            "inventario_id": lote["id"],
            "tipo": "CONSUMO",
            "cantidad": a_descontar,
            "motivo": motivo,
            "usuario_id": usuario_id
        }).execute()

        lotes_afectados.append({
            "lote": lote["lote"],
            "producto": lote["producto"],
            "cantidad_descontada": a_descontar,
            "unidad": lote["unidad"],
            "fecha_vencimiento": lote["fecha_vencimiento"]
        })
        restante -= a_descontar

    return {"exito": True, "lotes": lotes_afectados, "total_consumido": cantidad}


# ============================================================
# CLIENTES
# ============================================================

def registrar_cliente(nombre: str, contacto: str = None,
                      telefono: str = None, direccion: str = None) -> Dict:
    """Registra un nuevo cliente. Retorna el cliente creado o error."""
    try:
        resp = supabase.table("clientes").insert({
            "nombre": nombre.strip(),
            "contacto": contacto,
            "telefono": telefono,
            "direccion": direccion
        }).execute()
        return {"exito": True, "cliente": resp.data[0]}
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return {"exito": False, "error": f"Ya existe el cliente '{nombre}'"}
        return {"exito": False, "error": str(e)}


def listar_clientes() -> List[Dict]:
    """Lista todos los clientes activos ordenados por nombre."""
    return (
        supabase.table("clientes")
        .select("*")
        .eq("activo", True)
        .order("nombre", desc=False)
        .execute()
        .data
    )


def buscar_cliente(nombre: str) -> Optional[Dict]:
    """Busca un cliente por nombre (busqueda parcial). Retorna el primero que coincida."""
    resp = (
        supabase.table("clientes")
        .select("*")
        .ilike("nombre", f"%{nombre.strip()}%")
        .eq("activo", True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


# ============================================================
# DESPACHOS
# ============================================================

def registrar_despacho(cliente_nombre: str, items: List[Dict],
                       observaciones: str = None,
                       usuario_id: int = None, usuario_nombre: str = None) -> Dict:
    """
    Registra un despacho a cliente aplicando FEFO por cada producto.
    items: [{"producto": str, "cantidad": float}, ...]
    Retorna dict con resultado, ID del despacho y lista de errores.
    """
    cliente = buscar_cliente(cliente_nombre)
    cliente_id = cliente["id"] if cliente else None
    nombre_final = cliente["nombre"] if cliente else cliente_nombre.strip()

    desp = supabase.table("despachos").insert({
        "cliente_id": cliente_id,
        "cliente_nombre": nombre_final,
        "observaciones": observaciones,
        "usuario_id": usuario_id,
        "usuario_nombre": usuario_nombre
    }).execute()
    despacho_id = desp.data[0]["id"]

    productos_despachados = []
    errores = []

    for item in items:
        nombre_prod = item["producto"]
        cantidad = float(item["cantidad"])

        lotes = (
            supabase.table("inventario")
            .select("*")
            .eq("estado", "activo")
            .gt("cantidad", 0)
            .ilike("producto", f"%{nombre_prod.lower().strip()}%")
            .order("fecha_vencimiento", desc=False)
            .execute()
            .data
        )

        if not lotes:
            errores.append(f"Sin stock de '{nombre_prod}'")
            continue

        stock_total = sum(l["cantidad"] for l in lotes)
        if cantidad > stock_total:
            errores.append(
                f"Stock insuficiente de '{nombre_prod}' "
                f"(disponible: {stock_total} {lotes[0]['unidad']})"
            )
            continue

        unidad = lotes[0]["unidad"]
        restante = cantidad

        for lote in lotes:
            if restante <= 0:
                break
            a_descontar = min(lote["cantidad"], restante)
            nueva_cantidad = lote["cantidad"] - a_descontar
            nuevo_estado = "agotado" if nueva_cantidad == 0 else "activo"

            supabase.table("inventario").update({
                "cantidad": nueva_cantidad,
                "estado": nuevo_estado
            }).eq("id", lote["id"]).execute()

            supabase.table("despacho_items").insert({
                "despacho_id": despacho_id,
                "inventario_id": lote["id"],
                "producto": lote["producto"],
                "cantidad": a_descontar,
                "unidad": lote["unidad"]
            }).execute()

            supabase.table("movimientos").insert({
                "inventario_id": lote["id"],
                "tipo": "DESPACHO",
                "cantidad": a_descontar,
                "motivo": f"Despacho #{despacho_id} → {nombre_final}",
                "despacho_id": despacho_id,
                "usuario_id": usuario_id
            }).execute()

            restante -= a_descontar

        productos_despachados.append({
            "producto": nombre_prod,
            "cantidad": cantidad,
            "unidad": unidad
        })

    return {
        "exito": True,
        "despacho_id": despacho_id,
        "cliente": nombre_final,
        "productos": productos_despachados,
        "errores": errores
    }


def consultar_despachos(limit: int = 10) -> List[Dict]:
    """Retorna los ultimos N despachos con sus items."""
    return (
        supabase.table("despachos")
        .select("*, despacho_items(*)")
        .order("fecha", desc=True)
        .limit(limit)
        .execute()
        .data
    )


# ============================================================
# REPORTE DIARIO
# ============================================================

def reporte_diario() -> Dict:
    """Resumen de movimientos del dia de hoy."""
    hoy = datetime.now().date().isoformat()
    manana = (datetime.now().date() + timedelta(days=1)).isoformat()

    movimientos = (
        supabase.table("movimientos")
        .select("tipo, cantidad")
        .gte("fecha", hoy)
        .lt("fecha", manana)
        .execute()
        .data
    )

    despachos_hoy = (
        supabase.table("despachos")
        .select("id", count="exact")
        .gte("fecha", hoy)
        .lt("fecha", manana)
        .execute()
        .count or 0
    )

    stats = estadisticas_generales()
    proximos = consultar_proximos_vencer(dias=3)

    return {
        "entradas_hoy": sum(m["cantidad"] for m in movimientos if m["tipo"] == "ENTRADA"),
        "consumos_hoy": sum(m["cantidad"] for m in movimientos if m["tipo"] == "CONSUMO"),
        "bajas_hoy": sum(m["cantidad"] for m in movimientos if m["tipo"] == "BAJA"),
        "despachos_hoy": despachos_hoy,
        "proximos_vencer": len(proximos),
        "stock_total_lotes": stats["total_lotes"],
        "stock_total_unidades": stats["total_unidades"]
    }


if __name__ == "__main__":
    print("Probando conexion a Supabase...")
    if test_connection():
        print("\nEstadisticas actuales:")
        for k, v in estadisticas_generales().items():
            print(f"  {k}: {v}")
