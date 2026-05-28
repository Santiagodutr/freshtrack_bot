# FreshTrack AI — Elevator Pitch + Guion Demo Video
> Sustentación Transformación Digital — Junio 2026

---

## ELEVATOR PITCH (1 min 30 seg)

> Aprenderlo de memoria. Hablar despacio, con pausa después de la pregunta.

---

"Cada mes, las distribuidoras de alimentos pierden entre el 15 y el 20 por ciento de su inventario perecedero.

No por mala calidad. No por fallas en la cadena de frío.

Sino porque nadie supo a tiempo qué producto estaba por vencer.

El operario de bodega lleva el control en un cuaderno, en Excel, o de memoria. Y cuando el salmón vence el martes, se entera el miércoles.

¿Y si pudiera controlar todo eso desde el teléfono que ya tiene en el bolsillo, escribiendo como le escribe a un amigo, sin instalar ninguna aplicación nueva?

Eso es FreshTrack AI.

Un chatbot de Telegram que entiende lenguaje natural, organiza el inventario automáticamente y aplica FEFO: lo que vence primero, sale primero.

El operario escribe 'llegaron 5 kg de lechuga y 8 kg de tomate' — y el sistema registra, alerta y organiza todo en tiempo real.

Sin capacitación. Sin formularios. Sin software nuevo.

FreshTrack AI. Porque perder inventario no es mala suerte. Es falta de información a tiempo."

---
---

## GUION DEL VIDEO DEMO

### Antes de grabar — preparar esto
- Bot corriendo (`python bot.py` en terminal, dejarla abierta)
- Telegram abierto en el chat del bot
- Supabase abierto en el dashboard, tabla `inventario`
- Base de datos limpia (sin datos previos de prueba)
- Ajustar las fechas del mensaje de entrada para que al menos 1-2 productos aparezcan en `/alertas` (vencimiento en ≤ 3 días desde el día de grabación)

---

### PARTE 1 — Presentación del problema (30 seg)

*[Cámara, sin compartir pantalla aún]*

"Hola, somos FreshTrack AI.

Trabajamos con una distribuidora de alimentos perecederos que enfrenta un problema muy común: el control de inventario en bodega se hace de forma manual, con cuadernos o Excel, y los productos vencen antes de que alguien lo note.

Nuestra propuesta es simple: un asistente inteligente en Telegram que el operario ya usa todos los días, que entiende lo que él escribe y lleva el control por él."

---

### PARTE 2 — Demo del bot en acción (3 min)

*[Compartir pantalla: Telegram, chat con el bot]*

"Esto es el bot funcionando en este momento, en tiempo real.

El operario abre Telegram y escribe `/start`."

*[Enviar `/start`, esperar respuesta]*

"El bot lo saluda y le explica qué puede hacer. Pero lo más importante no son los comandos — es esto:"

*[Escribir y enviar el mensaje de entrada, por ejemplo:]*
```
Salmón filete 1.5 kg 30/05, Tomate 8 kg 31/05, Queso fresco 2 kg 05/06, Lechuga 5 kg 10/06, Yogur natural 10 litros 15/06
```

"Sin formularios. Sin menús. El operario escribe exactamente como habla."

*[Esperar respuesta del bot — ~3 segundos]*

"En menos de 3 segundos el bot identificó 5 productos, extrajo cantidades, unidades y fechas de vencimiento, y los guardó en la base de datos en la nube.

Ahora revisamos el inventario."

*[Enviar `/stock`]*

*[Esperar respuesta]*

"El inventario aparece ordenado por fecha de vencimiento — el salmón primero porque vence más pronto. Esto es FEFO: lo que vence antes, sale antes. El operario ya sabe qué producto debe priorizar hoy."

*[Enviar `/alertas`]*

*[Esperar respuesta]*

"Las alertas le muestran los productos críticos — los que vencen en los próximos tres días. El sistema lo avisa antes de que sea un problema.

Ahora hagamos un despacho. Imaginemos que el cliente Carulla pide tomate y queso."

*[Enviar:]*
```
/despachar Carulla: 3 kg tomate, 2 kg queso
```

*[Esperar respuesta del bot]*

"El bot registró el despacho, descontó del inventario y dejó trazabilidad completa: quién pidió qué, cuánto, y a qué hora."

*[Enviar `/reporte`]*

"El reporte del día resume todo lo que pasó: entradas, salidas, despachos y cuántos productos están en riesgo de vencer. Un resumen ejecutivo al instante."

*[Enviar `/vencidos`]*

"Y este comando da de baja automática los productos que ya vencieron. No se borra nada — queda registrado en el historial para auditoría."

---

### PARTE 3 — Lo que hay detrás (1 min)

*[Opcional: mostrar brevemente el dashboard de Supabase]*

"Todo esto queda guardado en una base de datos en la nube, accesible desde cualquier lugar.

Cada movimiento queda registrado: entradas, consumos, despachos y bajas. Nada se pierde.

Y la razón por la que el bot entiende lenguaje natural es que usa inteligencia artificial — un modelo de lenguaje que lee el mensaje del operario y extrae los datos estructurados, sin importar cómo esté escrito: 'llegaron', 'recibí', 'tengo', 'me mandaron' — el bot entiende todo."

---

### PARTE 4 — Cierre (30 seg)

*[Cámara, sin pantalla compartida]*

"FreshTrack AI no reemplaza al operario. Lo potencia.

Le da herramientas de nivel empresarial usando el dispositivo que ya tiene y el lenguaje que ya habla.

Para una distribuidora que pierde el 18% de su inventario cada mes, esto no es solo comodidad — es dinero recuperado.

Gracias. Somos FreshTrack AI."

---

## FLUJO DE PANTALLAS (resumen para edición)

```
Cámara — presentación del problema
        ↓
Telegram — /start
        ↓
Telegram — mensaje de entrada (5 productos)
        ↓
Telegram — /stock (lista FEFO)
        ↓
Telegram — /alertas
        ↓
Telegram — /despachar Carulla
        ↓
Telegram — /reporte
        ↓
Telegram — /vencidos
        ↓
Supabase — tabla inventario (opcional, 10 segundos)
        ↓
Cámara — cierre
```

---

## CHECKLIST ANTES DE GRABAR

- [ ] `python bot.py` corriendo sin errores
- [ ] Telegram abierto en el chat del bot
- [ ] Base de datos limpia (sin datos de prueba anteriores)
- [ ] Fechas ajustadas para que `/alertas` muestre al menos 1 producto
- [ ] Notificaciones del teléfono y PC silenciadas
- [ ] Un ensayo completo en voz alta antes de grabar
