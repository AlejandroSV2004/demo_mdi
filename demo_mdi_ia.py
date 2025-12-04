import sounddevice as sd
from scipy.io.wavfile import write
import keyboard
import numpy as np
import os
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play # CORRECCION: Importamos desde el submodulo especifico
from dotenv import load_dotenv
import time

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACION GOOGLE GEMINI ---
api_key_google = os.environ.get("GOOGLE_API_KEY")
api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")

if not api_key_google or not api_key_eleven:
    print("Error: Faltan las claves en el archivo .env")
    exit()

genai.configure(api_key=api_key_google)

# Configuracion del modelo y personalidad
prompt_sistema = """
Eres Jarvis, un asistente personal de inteligencia artificial al estilo de Iron Man.
Responde de manera concisa, elegante y con un toque de humor sutil.
No uses emojis. Maximo 2 oraciones por respuesta.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",
    system_instruction=prompt_sistema
)

chat_session = model.start_chat(history=[])

# Configuracion ElevenLabs
client_eleven = ElevenLabs(api_key=api_key_eleven)

# Configuracion de audio
fs = 44100
record_key = "r"

print(f"Sistema Jarvis (Version Gemini + ElevenLabs v1.0).")
print(f"Presiona '{record_key}' para grabar. 'q' para salir.")
print("-" * 50)

def callback(indata, frames, time, status):
    if status:
        print(status)
    buffer.append(indata.copy())

def transcribir_y_responder_gemini(filename):
    try:
        print("Subiendo audio a Gemini...")
        archivo_audio = genai.upload_file(path=filename)
        
        while archivo_audio.state.name == "PROCESSING":
            time.sleep(1)
            archivo_audio = genai.get_file(archivo_audio.name)

        if archivo_audio.state.name == "FAILED":
            print("Fallo el procesamiento del audio")
            return None, None

        # Paso 1: Transcripcion
        prompt_transcripcion = "Transcribe exactamente lo que dice el usuario en este audio."
        respuesta_transcripcion = model.generate_content([prompt_transcripcion, archivo_audio])
        texto_usuario = respuesta_transcripcion.text.strip()
        
        # Paso 2: Respuesta del chat
        respuesta_chat = chat_session.send_message(texto_usuario)
        texto_respuesta = respuesta_chat.text.strip()
        
        # Limpieza
        genai.delete_file(archivo_audio.name)
        
        return texto_usuario, texto_respuesta

    except Exception as e:
        print(f"Error en Gemini: {e}")
        return None, None

def texto_a_voz(text, output_file="respuesta_audio.mp3"):
    try:
        # Generamos el audio usando el cliente y el ID de Rachel
        audio_generator = client_eleven.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM", 
            model_id="eleven_multilingual_v2",
            text=text
        )
        
        # Convertimos a bytes
        audio_bytes = b"".join(audio_generator)
        
        # Guardamos el archivo
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        
        # Reproducimos
        play(audio_bytes)
        return True
    except Exception as e:
        print(f"Error generando voz: {e}")
        return False

# Variables de control
grabando = False
buffer = []
stream = None

while True:
    try:
        if keyboard.is_pressed(record_key):
            if not grabando:
                print("Grabando...")
                grabando = True
                buffer = []
                stream = sd.InputStream(
                    callback=callback,
                    channels=1,
                    samplerate=fs
                )
                stream.start()
                while keyboard.is_pressed(record_key):
                    pass
            else:
                print("Procesando...")
                grabando = False
                stream.stop()
                stream.close()
                
                if len(buffer) > 0:
                    datos_grabacion = np.concatenate(buffer, axis=0)
                    write("temp_input.wav", fs, datos_grabacion)
                    
                    texto_us, respuesta_ai = transcribir_y_responder_gemini("temp_input.wav")
                    
                    if texto_us and respuesta_ai:
                        print(f"Usuario: {texto_us}")
                        print(f"Jarvis: {respuesta_ai}")
                        
                        texto_a_voz(respuesta_ai)
                        print("-" * 50)
                    else:
                        print("No se pudo procesar la respuesta.")
                
                while keyboard.is_pressed(record_key):
                    pass
        
        if keyboard.is_pressed('q'):
            print("Apagando sistemas...")
            if stream:
                stream.stop()
                stream.close()
            break
            
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error critico: {e}")
        if stream:
            stream.stop()
            stream.close()
        break