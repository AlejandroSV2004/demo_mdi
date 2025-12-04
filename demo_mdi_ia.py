import sounddevice as sd
from scipy.io.wavfile import write
import keyboard
import numpy as np
import os
import google.generativeai as genai
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import time
import pygame
import json # Necesario para leer la respuesta de Vosk
from vosk import Model, KaldiRecognizer # Importamos Vosk

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACION ---
api_key_google = os.environ.get("GOOGLE_API_KEY")
api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")

if not api_key_google or not api_key_eleven:
    print("Error: Faltan las claves en el archivo .env")
    exit()

# 1. Configurar Gemini
genai.configure(api_key=api_key_google)
prompt_sistema = """
Eres Jarvis, un asistente personal de inteligencia artificial al estilo de Iron Man.
Responde de manera concisa, elegante, formal y con un toque de humor sutil.
No uses emojis. Maximo 2 oraciones por respuesta.
"""
model_gemini = genai.GenerativeModel(
    model_name="gemini-2.5-pro", # El modelo Flash es mas rapido
    system_instruction=prompt_sistema
)
chat_session = model_gemini.start_chat(history=[])

# 2. Configurar ElevenLabs
client_eleven = ElevenLabs(api_key=api_key_eleven)

# 3. Configurar VOSK (Reconocimiento de voz local)
print("Cargando modelo de voz local (Vosk)...")
if not os.path.exists("model"):
    print("ERROR: No encuentro la carpeta 'model'.")
    print("Descarga 'vosk-model-small-es-0.42', descomprimelo y renombra la carpeta a 'model'.")
    exit()
    
try:
    # Cargamos el modelo en memoria (esto pasa solo una vez al inicio)
    vosk_model = Model("model")
    # Creamos el reconocedor
    rec_vosk = KaldiRecognizer(vosk_model, 44100)
except Exception as e:
    print(f"Error cargando Vosk: {e}")
    exit()

# 4. Inicializar Audio Player
pygame.mixer.init()

# Configuracion de audio
fs = 44100
record_key = "r"

print("-" * 50)
print(f"SISTEMA JARVIS ONLINE (Modo Turbo: Vosk Local).")
print(f"Presiona '{record_key}' para grabar. 'q' para salir.")
print("-" * 50)

def callback(indata, frames, time, status):
    if status:
        print(status)
    buffer.append(indata.copy())

def transcribir_con_vosk(audio_data):
    """
    Convierte el audio raw a texto usando Vosk (Localmente)
    """
    print("Transcribiendo localmente...")
    
    # Vosk necesita audio en formato int16 (bytes), no float32
    # Convertimos el audio de numpy (float) a int16 pcm
    audio_int16 = (audio_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    
    if rec_vosk.AcceptWaveform(audio_bytes):
        resultado = json.loads(rec_vosk.Result())
        return resultado.get("text", "")
    else:
        # Recuperar lo ultimo que quedo en el buffer
        resultado = json.loads(rec_vosk.FinalResult())
        return resultado.get("text", "")

def obtener_respuesta_gemini(texto_usuario):
    """
    Envia solo el texto a Gemini (Mucho mas rapido que enviar audio)
    """
    try:
        if not texto_usuario or len(texto_usuario) < 2:
            return None
            
        print("Pensando respuesta...")
        response = chat_session.send_message(texto_usuario)
        return response.text.strip()
    except Exception as e:
        print(f"Error Gemini: {e}")
        return None

def texto_a_voz(text, output_file="respuesta_jarvis.mp3"):
    try:
        # Usamos la voz de Adam (Español profundo/neutro)
        audio_generator = client_eleven.text_to_speech.convert(
            voice_id="pNInz6obpgDQGcFmaJgB", 
            model_id="eleven_multilingual_v2",
            text=text
        )
        
        audio_bytes = b"".join(audio_generator)
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        
        try:
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            return True
        except Exception as e:
            print(f"Error player: {e}")
            return False

    except Exception as e:
        print(f"Error ElevenLabs: {e}")
        return False

# Variables de control
grabando = False
buffer = []
stream = None

while True:
    try:
        if keyboard.is_pressed(record_key):
            if not grabando:
                print(">> Escuchando...")
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
                print("procesando...")
                grabando = False
                stream.stop()
                stream.close()
                
                if len(buffer) > 0:
                    # Unimos todo el audio grabado
                    datos_grabacion = np.concatenate(buffer, axis=0)
                    
                    # PASO 1: Transcripcion Local (VOSK) - Instantanea
                    texto_usuario = transcribir_con_vosk(datos_grabacion)
                    
                    if texto_usuario:
                        print(f"Tú: {texto_usuario}")
                        
                        # PASO 2: Cerebro (Gemini) - Texto a Texto
                        respuesta_jarvis = obtener_respuesta_gemini(texto_usuario)
                        
                        if respuesta_jarvis:
                            print(f"Jarvis: {respuesta_jarvis}")
                            
                            # PASO 3: Voz (ElevenLabs)
                            texto_a_voz(respuesta_jarvis)
                            print("-" * 50)
                    else:
                        print("No escuché nada claro.")
                
                while keyboard.is_pressed(record_key):
                    pass
        
        if keyboard.is_pressed('q'):
            print("Apagando sistemas...")
            if stream:
                stream.stop()
                stream.close()
            pygame.mixer.quit()
            break
            
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error critico: {e}")
        if stream:
            stream.stop()
            stream.close()
        break