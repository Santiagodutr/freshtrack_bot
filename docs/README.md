# FreshTrack AI — Documentación Técnica

> Bot de Telegram para gestión de inventario de perecederos con IA  
> Metodología FEFO · Groq LLM · Supabase · Python

---

## Índice de documentos

| Documento | Descripción |
|-----------|-------------|
| [informe_tecnico.md](informe_tecnico.md) | Informe técnico completo: stack, módulos, BD, flujos, despliegue |
| [diagramas.md](diagramas.md) | Todos los diagramas Mermaid con enlaces interactivos |

---

## Resumen del sistema

FreshTrack AI es un bot de Telegram que permite a operadores de bodega:

- **Registrar** productos perecederos por texto libre (IA parsea la entrada) o wizard manual
- **Consultar** el inventario ordenado por FEFO (primero vence, primero sale)
- **Consumir** productos internamente con descuento automático multi-lote FEFO
- **Despachar** pedidos a clientes con selección multi-producto y FEFO automático
- **Recibir alertas** diarias a las 8 AM sobre productos próximos a vencer
- **Auditar** todos los movimientos (entradas, consumos, despachos, bajas)

---

## Stack técnico en una línea

```
Python 3.10 · python-telegram-bot 21.6 · Groq API (Llama 3.3 70B) · Supabase (PostgreSQL) · APScheduler
```

---

## Diagramas disponibles

1. **Arquitectura General** — componentes del sistema y conexiones
2. **Esquema ER** — modelo relacional de las 5 tablas
3. **Algoritmo FEFO** — lógica de consumo multi-lote
4. **Máquina de Estados** — flujos de conversación Telegram
5. **Secuencia Despacho** — flujo completo de un despacho a cliente

Ver todos en [diagramas.md](diagramas.md)

---

## Estructura de archivos del proyecto

```
freshtrack_bot/
├── bot.py              # Orquestador principal (668 líneas)
├── database.py         # Capa de datos Supabase + FEFO (509 líneas)
├── conversations.py    # Wizards multi-paso Telegram (607 líneas)
├── ai_parser.py        # NLP con Groq Llama 3.3 70B (205 líneas)
├── keyboards.py        # UI Telegram (143 líneas)
├── scheduler.py        # Daemon alertas 8 AM (100 líneas)
├── requirements.txt    # Dependencias Python
├── .env.example        # Template de configuración
├── supabase_schema.sql # DDL de base de datos
├── README.md           # Guía de usuario
├── GUIA_EQUIPO.md      # Guía del equipo de desarrollo
└── docs/               # ← Esta carpeta
    ├── README.md        # Índice de documentación
    ├── informe_tecnico.md   # Informe técnico completo
    └── diagramas.md     # Diagramas Mermaid
```

---

## Inicio rápido

```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con credenciales reales
python bot.py
```

---

*Documentación generada — FreshTrack AI v1.0 · 2026-06-03*
