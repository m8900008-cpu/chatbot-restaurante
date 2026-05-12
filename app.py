from flask import Flask, request
import anthropic
import os
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Memoria por número de teléfono (se reinicia si el servidor se reinicia)
conversaciones = {}

SYSTEM_PROMPT = """Eres el asistente de El Rincón, un restaurante mediterráneo en Barcelona. 
Responde en español, breve y amable como en WhatsApp. 

Horario: lunes a viernes 13:00-16:00 y 20:00-23:30, sábados 13:00-23:30, domingos cerrado.
Dirección: Carrer de Provença 142. Teléfono: 93 412 55 88.
Menú del día 14,50€: primero, segundo, postre y bebida.
Opciones veganas disponibles.

REGLA CANCELACION: cuando el cliente quiera cancelar una reserva y te dé su nombre, 
responde confirmando y añade en línea separada: CANCELAR: nombre=X

REGLA RESERVA: cuando el cliente quiera reservar y te haya dado nombre, fecha, hora Y 
número de personas, responde amablemente y añade en línea separada exactamente así:
RESERVA: nombre=X | fecha=YYYY-MM-DD | hora=HH:mm | personas=X

IMPORTANTE: en fecha usa siempre formato YYYY-MM-DD, nunca palabras como viernes o mañana.
En hora usa siempre formato HH:mm."""

claude_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    mensaje_cliente = request.form.get("Body", "")
    numero_cliente = request.form.get("From", "")

    # Recuperar historial de conversación
    if numero_cliente not in conversaciones:
        conversaciones[numero_cliente] = []

    historial = conversaciones[numero_cliente]

    # Añadir mensaje del cliente al historial
    historial.append({"role": "user", "content": mensaje_cliente})

    # Limitar historial a últimos 10 mensajes para no exceder tokens
    if len(historial) > 10:
        historial = historial[-10:]

    # Llamar a Claude con el historial completo
    respuesta = claude_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=historial
    )

    texto_respuesta = respuesta.content[0].text

    # Añadir respuesta de Claude al historial
    historial.append({"role": "assistant", "content": texto_respuesta})
    conversaciones[numero_cliente] = historial

    # Limpiar texto para el cliente (quitar línea RESERVA: o CANCELAR:)
    import re
    texto_cliente = re.sub(r'\s*(RESERVA|CANCELAR):.*$', '', texto_respuesta, flags=re.MULTILINE).strip()

    # Responder por WhatsApp
    resp = MessagingResponse()
    resp.message(texto_cliente)
    return str(resp)

@app.route("/", methods=["GET"])
def home():
    return "Chatbot Restaurante funcionando ✓"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
