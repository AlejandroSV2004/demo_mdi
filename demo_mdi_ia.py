import sounddevice as sd
from scipy.io.wavfile import write, read
import keyboard
import numpy as np
import os
import openai
from elevenlabs import generate, play, set_api_key, voices

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Configurar APIs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
set_api_key(ELEVENLABS_API_KEY)
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Configuración de audio
fs = 44100  # Sample rate
record_key = "r"  # Tecla para grabar

# Obtener lista de voces disponibles
voice_list = voices()

print(f"Presiona '{record_key}' para iniciar/detener la grabación")
print("Presiona 'q' para salir del programa\n")

def callback(indata, frames, time, status):
    """Callback para la grabación de audio"""
    if status:
        print(status)
    buffer.append(indata.copy())

def transcribe_audio(filename):
    """Transcribir audio usando Whisper de OpenAI"""
    try:
        with open(filename, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return None

def get_chatgpt_response(user_message, conversation_history):
    """Obtener respuesta de ChatGPT"""
    try:
        conversation_history.append({"role": "user", "content": user_message})
        
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=conversation_history
        )
        
        assistant_message = completion.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    except Exception as e:
        print(f"Error con ChatGPT: {e}")
        return None

def text_to_speech(text, output_file="ai_voice.wav"):
    """Convertir texto a voz usando ElevenLabs"""
    try:
        audio = generate(
            text=text,
            model="eleven_multilingual_v1"
        )
        
        # Guardar y reproducir
        with open(output_file, "wb") as f:
            f.write(audio)
        
        play(audio)
        return True
    except Exception as e:
        print(f"Error en síntesis de voz: {e}")
        return False

# ==================== CONFIGURACIÓN DE PERSONALIDAD ====================
# Aquí defines el contexto, personalidad y comportamiento de tu asistente

SYSTEM_PROMPT = """
Eres Jarvis, un asistente personal de inteligencia artificial al estilo de Iron Man.

PERSONALIDAD:
- Sofisticado, inteligente y con un toque de humor británico sutil
- Eficiente y directo, pero con calidez
- Ocasionalmente haces observaciones ingeniosas
- Te diriges al usuario como "Señor" o "Señora"

CONTEXTO:
- Estás integrado en el sistema del hogar/oficina del usuario
- Tienes acceso a información general pero finges tener más capacidades
- Puedes hacer referencias a tecnología avanzada de manera humorística

ESTILO DE RESPUESTA:
- Respuestas concisas pero completas
- Usa un lenguaje formal pero accesible
- Incluye ocasionalmente comentarios sutilmente sarcásticos o divertidos
- Mantén respuestas cortas (2-3 oraciones máximo para conversación casual)

EJEMPLOS:
Usuario: "¿Qué hora es?"
Tú: "Son las 3:45 PM, Señor. ¿Requiere que ajuste algún sistema o programar alguna actividad?"

Usuario: "Cuéntame un chiste"
Tú: "Mi base de datos de humor indica que usted ya ha escuchado todos mis mejores chistes, Señor. Pero si insiste: ¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae bugs."
"""

# Si prefieres otro escenario, aquí hay ejemplos alternativos:

# Ejemplo 2: Asistente de Fitness
SYSTEM_PROMPT_FITNESS = """
Eres un entrenador personal motivador y enérgico.

PERSONALIDAD:
- Súper entusiasta y positivo
- Motivador constante
- Usas muchas expresiones de ánimo
- Celebras cada pequeño logro

CONTEXTO:
- Ayudas al usuario con su rutina de ejercicio y nutrición
- Conoces sus metas de fitness
- Monitoreas su progreso

ESTILO:
- Energético y directo
- Usa emojis verbales (di cosas como "¡Vamos, tú puedes!")
- Respuestas cortas y punchy
"""

# Ejemplo 3: Mayordomo Británico
SYSTEM_PROMPT_BUTLER = """
Eres Alfred, un mayordomo británico tradicional y extremadamente formal.

PERSONALIDAD:
- Extremadamente cortés y formal
- Discreto y profesional
- Sabio y con consejos sutiles
- Leal y protector

CONTEXTO:
- Has servido a la familia por años
- Conoces las preferencias del usuario
- Ofreces servicio impecable

ESTILO:
- Lenguaje muy formal
- Siempre se dirige como "Su Señoría" o similar
- Respuestas elegantes y bien estructuradas
"""

# Inicializar historial de conversación
# Cambia SYSTEM_PROMPT por SYSTEM_PROMPT_FITNESS o SYSTEM_PROMPT_BUTLER según prefieras
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# Loop principal
recording = False
buffer = []
stream = None

print("Sistema listo. Esperando comandos...\n")

while True:
    try:
        # Verificar si se presionó la tecla de grabación
        if keyboard.is_pressed(record_key):
            if not recording:
                # Iniciar grabación
                print("🔴 Grabando... (presiona 'r' nuevamente para detener)")
                recording = True
                buffer = []
                stream = sd.InputStream(
                    callback=callback,
                    channels=1,
                    samplerate=fs
                )
                stream.start()
                
                # Esperar a que se suelte la tecla
                while keyboard.is_pressed(record_key):
                    pass
                    
            else:
                # Detener grabación
                print("⏹️  Grabación detenida. Procesando...")
                recording = False
                stream.stop()
                stream.close()
                
                # Procesar audio
                recording_data = np.concatenate(buffer, axis=0)
                write("input.wav", fs, recording_data)
                
                # Transcribir
                print("📝 Transcribiendo...")
                transcription = transcribe_audio("input.wav")
                
                if transcription:
                    print(f"Tú: {transcription}\n")
                    
                    # Obtener respuesta de ChatGPT
                    print("🤔 Pensando...")
                    response = get_chatgpt_response(transcription, conversation_history)
                    
                    if response:
                        print(f"Asistente: {response}\n")
                        
                        # Convertir respuesta a voz
                        print("🔊 Generando voz...")
                        text_to_speech(response)
                        print("\n✅ Listo para la siguiente pregunta\n")
                    else:
                        print("❌ Error al obtener respuesta\n")
                else:
                    print("❌ Error en la transcripción\n")
                
                # Esperar a que se suelte la tecla
                while keyboard.is_pressed(record_key):
                    pass
        
        # Verificar si se presionó 'q' para salir
        if keyboard.is_pressed('q'):
            print("\n👋 Saliendo del programa...")
            if stream:
                stream.stop()
                stream.close()
            break
            
    except KeyboardInterrupt:
        print("\n👋 Programa interrumpido")
        if stream:
            stream.stop()
            stream.close()
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        if stream:
            stream.stop()
            stream.close()
        break