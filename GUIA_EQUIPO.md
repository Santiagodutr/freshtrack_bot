# 🥬 FreshTrack AI — Guía del Equipo

> **Sustentación:** entre 3 y 4 de junio
> **Equipo:** Sofía García, David Arango, Santiago Duarte

---

## 📌 ¿Qué vamos a construir?

Un ChatBot de Telegram que recibe mensajes de inventario en lenguaje natural, los procesa con IA, y los guarda en una base de datos en la nube (Supabase). Aplica la metodología **FEFO** (First Expired, First Out) para alertar sobre productos próximos a vencer.

### Arquitectura
```
Usuario → Telegram → bot.py → IA (Groq) → Supabase (PostgreSQL cloud)
                          ↓
                   scheduler.py (alertas 8 AM)
```

---

## 👥 División de tareas

### 👤 Sofía — Backend / Bot Telegram
**Responsabilidades:**
- Crear el bot en Telegram con @BotFather y obtener el TOKEN
- Correr `python bot.py` en su PC durante el demo
- Mostrar el flujo conversacional en Telegram

**Lo que muestra en el video:**
- Pantalla de Telegram con el bot
- Envío de un mensaje natural: *"Lechuga 5 unidades 10/12, Tomate 8 kg 09/12"*
- Comandos `/start`, `/stock`, `/alertas`

### 👤 David — IA / Parser
**Responsabilidades:**
- Crear cuenta en Groq y obtener API KEY
- Probar y entender el archivo `ai_parser.py`
- Explicar cómo la IA convierte texto natural en datos estructurados

**Lo que muestra en el video:**
- Ejecuta `python ai_parser.py` y muestra el JSON resultante
- Explica el prompt al LLM (Llama 3.3 70B)
- Argumenta por qué Groq: gratis, rápido, sin tarjeta de crédito

### 👤 Santiago — Base de Datos / Supabase
**Responsabilidades:**
- Crear el proyecto en Supabase y ejecutar el SQL de creación de tablas
- Compartir SUPABASE_URL y SUPABASE_KEY con el equipo
- Tener el dashboard de Supabase abierto durante el demo

**Lo que muestra en el video:**
- Dashboard de Supabase → Table Editor → `inventario`
- Muestra los datos en tiempo real mientras Sofía registra productos
- Tabla `movimientos` con la auditoría
- Comandos `/vencidos` y `/stats`

---

## 🚀 SETUP — Sigue estos pasos EN ORDEN

### PASO 1 — Santiago crea Supabase (10 min)

#### 1.1 Crear el proyecto
1. Ve a https://supabase.com
2. Click **"Start your project"** → inicia sesión con GitHub
3. Click **"New Project"**:
   - **Name:** `freshtrack-ai`
   - **Database Password:** crea una contraseña fuerte y guárdala
   - **Region:** South America (São Paulo)
   - **Plan:** Free
4. Espera ~2 minutos a que se cree

#### 1.2 Crear las tablas
1. Panel izquierdo → **SQL Editor** → **New query**
2. Pega este SQL completo:

```sql
-- Tabla inventario
CREATE TABLE inventario (
    id BIGSERIAL PRIMARY KEY,
    producto TEXT NOT NULL,
    cantidad NUMERIC NOT NULL,
    unidad TEXT DEFAULT 'unidades',
    fecha_vencimiento DATE NOT NULL,
    fecha_registro TIMESTAMPTZ DEFAULT NOW(),
    lote TEXT,
    estado TEXT DEFAULT 'activo',
    usuario_id BIGINT,
    usuario_nombre TEXT
);

-- Tabla movimientos
CREATE TABLE movimientos (
    id BIGSERIAL PRIMARY KEY,
    inventario_id BIGINT REFERENCES inventario(id),
    tipo TEXT NOT NULL,
    cantidad NUMERIC,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    motivo TEXT,
    usuario_id BIGINT
);

-- Indices para mejor performance
CREATE INDEX idx_inv_fecha_venc ON inventario(fecha_vencimiento);
CREATE INDEX idx_inv_estado ON inventario(estado);
```

3. Click **"Run"** → debe decir "Success. No rows returned"

#### 1.3 Copiar las credenciales
1. **Settings** (engranaje abajo a la izquierda) → **API**
2. Copia y guarda:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: string largo que empieza con `eyJ...`
3. **Compartir con el equipo** estos dos valores

---

### PASO 2 — Sofía crea el Bot de Telegram (3 min)

1. Abre Telegram (puede ser web o móvil)
2. Busca **@BotFather** y abre el chat
3. Envía `/newbot`
4. **Nombre del bot:** `FreshTrack AI`
5. **Username:** debe terminar en `bot` y ser único. Ejemplos:
   - `freshtrack_paraiso_bot`
   - `freshtrack_ai_demo_bot`
   - `paraiso_inventario_bot`
6. BotFather te dará un **TOKEN** tipo:
   ```
   7891234567:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
7. **Guarda el token y compártelo con el equipo**

---

### PASO 3 — David crea la cuenta de Groq (2 min)

1. Ve a https://console.groq.com/keys
2. Regístrate con Google o GitHub (sin tarjeta de crédito)
3. Click **"Create API Key"**
4. Ponle nombre: `freshtrack-bot`
5. Copia la key (empieza con `gsk_...`)
6. **Compartir con el equipo**

---

### PASO 4 — Cualquiera del equipo: instalar y correr (10 min)

> ⚠️ Solo UNA persona necesita correr el bot durante el demo. Recomendado: **Sofía**.

#### 4.1 Tener Python instalado
Verifica con:
```bash
python --version
```
Si no tienes Python 3.10+, descárgalo de https://python.org

#### 4.2 Descomprimir el proyecto
Descomprime `freshtrack_bot_supabase.zip` en una carpeta cómoda (ej. Escritorio).

#### 4.3 Abrir terminal en la carpeta
- **Windows:** abre la carpeta en el Explorador, escribe `cmd` en la barra de dirección y presiona Enter
- **Mac:** abre Terminal y escribe `cd ` luego arrastra la carpeta a la terminal

#### 4.4 Crear entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

Debes ver `(venv)` al inicio de la línea de comandos.

#### 4.5 Instalar dependencias
```bash
pip install -r requirements.txt
```
Tarda 1-2 minutos. Debe terminar sin errores.

#### 4.6 Crear archivo `.env`
1. Copia `.env.example` y renómbralo a `.env`
2. Ábrelo con Bloc de Notas (o cualquier editor)
3. Pega los valores que obtuvieron en pasos 1, 2 y 3:

```env
TELEGRAM_BOT_TOKEN=7891234567:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ADMIN_CHAT_ID=
```

Guarda el archivo.

#### 4.7 Probar conexión a Supabase
```bash
python database.py
```
Debe imprimir: `[DB] Conexion a Supabase exitosa.`

Si falla, revisa que SUPABASE_URL y SUPABASE_KEY estén bien escritos en `.env`.

#### 4.8 Probar el parser de IA
```bash
python ai_parser.py
```
Debe imprimir un JSON con productos.

#### 4.9 Arrancar el bot 🚀
```bash
python bot.py
```

Deberías ver:
```
============================================================
🥬 FreshTrack AI Bot
============================================================
Bot iniciado. Esperando mensajes en Telegram...
```

**¡Listo!** Dejar esta terminal abierta.

---

### PASO 5 — Probar en Telegram

1. En Telegram, busca el bot por el username que pusiste (ej. `@freshtrack_paraiso_bot`)
2. Envía `/start` → debe responder con bienvenida
3. Envía: `Lechuga 5 unidades 10/12, Tomate 8 kg 09/12, Yogur 10 litros 15/12`
4. Espera ~3 segundos → el bot confirma los 3 productos registrados
5. Envía `/stock` → ver inventario ordenado FEFO
6. Envía `/alertas` → ver próximos a vencer
7. Envía `/stats` → ver estadísticas

**Ve a Supabase → Table Editor → inventario → los datos están ahí** ✨

---

## 💬 Comandos del bot

| Comando | Qué hace |
|---|---|
| `/start` | Bienvenida e instrucciones |
| `/stock` | Inventario ordenado FEFO (lo que vence primero, primero) |
| `/alertas` | Productos que vencen en ≤ 3 días |
| `/vencidos` | Da de baja automática a productos vencidos |
| `/stats` | Estadísticas (lotes activos, unidades, bajas) |
| `/ayuda` | Ayuda |

**Para registrar productos**, simplemente escribe en lenguaje natural:
- `Lechuga 5 unidades 10/12`
- `Yogur natural 10 litros 15/12, Queso fresco 2 kg 12/12`
- `Acabo de recibir 12 cajas de tomate que vencen el 20 de diciembre`

---

## 🎬 Guion del demo para el video

### ESCENA 1 — Sofía (Bot funcionando)
*"Hola, somos FreshTrack AI. Les voy a mostrar cómo nuestro chatbot resuelve el problema de las pérdidas de inventario que sufre Distribuidora El Paraíso. El operario solo necesita Telegram, no descargar apps, no aprender software complicado. Yo, como operario, simplemente le digo al bot lo que recibí en bodega."*

→ Escribe en Telegram:
`Lechuga 5 unidades 10/12, Tomate 8 kg 09/12, Yogur natural 10 unidades 15/12, Queso fresco 2 unidades 12/12, Salmón filete 1.5 kg 08/12`

→ El bot responde en segundos con 5 productos registrados.

### ESCENA 2 — David (la IA por dentro)
*"Lo que acaba de pasar es que la IA de Groq, usando Llama 3.3 de 70 mil millones de parámetros, leyó ese mensaje en español natural y extrajo los datos estructurados. No usamos reglas rígidas, usamos un modelo de lenguaje real."*

→ Comparte pantalla: muestra el archivo `ai_parser.py`, el `SYSTEM_PROMPT`.

→ Corre `python ai_parser.py` y muestra el JSON.

*"Esto significa que el operario puede escribir como quiera, el bot entiende. 'Acabo de recibir', 'Tengo', 'Llegaron' — todo funciona."*

### ESCENA 3 — Santiago (Supabase en vivo)
*"Y todos esos datos están en una base de datos PostgreSQL en la nube, en Supabase. Esto es importante: no son archivos de Excel locales, es una base de datos profesional accesible desde cualquier lugar."*

→ Comparte pantalla: dashboard de Supabase, Table Editor, tabla `inventario`.

→ Refresca y muestra los 5 productos que Sofía acaba de registrar.

→ Vuelve a Telegram y escribe `/stock`.

*"El bot devuelve el inventario aplicando FEFO — First Expired, First Out. Esto es clave para perecederos: lo que vence primero debe salir primero. Si la distribuidora El Paraíso hubiera tenido esto, no perdería el 18% del inventario cada mes."*

→ Muestra `/alertas`, luego `/vencidos`, luego vuelve a Supabase y muestra la tabla `movimientos` con el log de auditoría.

→ Muestra `/stats`.

---

## 🐛 Problemas comunes

### "Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env"
- Revisa que el archivo se llame exactamente `.env` (no `.env.txt`)
- En Windows, activa "ver extensiones de archivos" para verificar
- Que no tenga espacios extra: `SUPABASE_URL=https://...` (sin espacios alrededor del `=`)

### "Could not find the table 'public.inventario'"
- No ejecutaste el SQL del Paso 1.2 en Supabase
- O lo ejecutaste en otro proyecto distinto al que estás conectado

### "telegram.error.Unauthorized"
- El token de Telegram está mal copiado
- Pídele a Sofía que vuelva a enviarlo (a veces el último caracter se corta al pegar)

### "groq.AuthenticationError"
- La API key de Groq está mal o expirada
- Genera una nueva en https://console.groq.com/keys

### El bot no responde en Telegram
- Verifica que `python bot.py` esté corriendo en una terminal (no debe estar cerrada)
- Busca que el username del bot en Telegram coincida con el que creó Sofía

### "ModuleNotFoundError: No module named 'telegram'"
- No activaste el entorno virtual o no instalaste las dependencias
- Vuelve a hacer: `venv\Scripts\activate` (Win) o `source venv/bin/activate` (Mac), luego `pip install -r requirements.txt`

---

## ✅ Checklist final antes de grabar

- [ ] Santiago: proyecto en Supabase creado, tablas creadas con el SQL
- [ ] Santiago: SUPABASE_URL y SUPABASE_KEY compartidos
- [ ] Sofía: bot creado con BotFather, TOKEN compartido
- [ ] David: cuenta de Groq creada, API KEY compartida
- [ ] Sofía (o quien corra el bot): proyecto descargado, `.env` creado, dependencias instaladas
- [ ] Sofía: `python database.py` funciona
- [ ] Sofía: `python bot.py` corre sin errores
- [ ] Probado en Telegram: `/start`, registro, `/stock`, `/alertas`, `/vencidos`, `/stats`
- [ ] Datos visibles en el dashboard de Supabase
- [ ] Los 3 ensayaron el guion del demo
- [ ] OBS Studio o Zoom listo para grabar las pantallas de los 3
- [ ] Las 3 cámaras encendidas

---

## 📦 Archivos del proyecto

| Archivo | Qué hace |
|---|---|
| `bot.py` | Bot principal de Telegram con los 6 comandos |
| `ai_parser.py` | Llama a Groq para entender mensajes naturales |
| `database.py` | Conexión y operaciones en Supabase |
| `scheduler.py` | Envía alertas automáticas a las 8 AM (opcional) |
| `requirements.txt` | Dependencias Python |
| `.env.example` | Plantilla de credenciales (renombrar a `.env` y llenar) |
| `README.md` | Documentación técnica |
| `GUIA_EQUIPO.md` | Esta guía |

---

## 🎯 Próximos pasos después del bot

1. **Elevator Pitch** — discurso 45s-2min para abrir el video
2. **Modelo de Negocio Canvas** — diagrama del negocio
3. **Guion de la Demo** — ya está en este documento
4. **Conclusión y reflexión personal** — cada uno habla 30-60s sobre lo aprendido en el curso

---

**¡Vamos por esa nota!** 💪🥬
