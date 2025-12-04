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
import json
from vosk import Model, KaldiRecognizer
import wave

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACION ---
api_key_google = os.environ.get("GOOGLE_API_KEY")
api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")

if not api_key_google or not api_key_eleven:
    print("Error: Faltan las claves en el archivo .env")
    exit()

genai.configure(api_key=api_key_google)
client_eleven = ElevenLabs(api_key=api_key_eleven)

# Inicializar el sistema de audio de pygame para reproducir MP3
pygame.mixer.init()

# Cargar modelo VOSK
print("Cargando modelo VOSK...")
try:
    vosk_model = Model("model")  # La carpeta 'model' debe estar en el mismo directorio
    print("Modelo VOSK cargado correctamente")
except Exception as e:
    print(f"Error al cargar el modelo VOSK: {e}")
    print("Asegúrate de que la carpeta 'model' existe y contiene el modelo vosk_small_es_042")
    exit()

# Configuracion del modelo Gemini
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

# Configuracion de audio grabacion
fs = 44100
record_key = "r"

print(f"Sistema Jarvis (Versión con VOSK).")
print(f"Presiona '{record_key}' para grabar. 'q' para salir.")
print("-" * 50)

def callback(indata, frames, time, status):
    if status:
        print(status)
    buffer.append(indata.copy())

def transcribir_con_vosk(filename):
    """
    Transcribe el audio usando VOSK (offline y rápido)
    """
    try:
        wf = wave.open(filename, "rb")
        
        # Verificar que el formato sea compatible
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in [8000, 16000, 32000, 44100, 48000]:
            print("El formato de audio debe ser WAV mono PCM.")
            return None
        
        rec = KaldiRecognizer(vosk_model, wf.getframerate())
        rec.SetWords(True)
        
        texto_completo = ""
        
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                resultado = json.loads(rec.Result())
                texto_completo += resultado.get("text", "") + " "
        
        # Obtener el resultado final
        resultado_final = json.loads(rec.FinalResult())
        texto_completo += resultado_final.get("text", "")
        
        wf.close()
        
        return texto_completo.strip()
    
    except Exception as e:
        print(f"Error en la transcripción VOSK: {e}")
        return None

def obtener_respuesta_gemini(texto_usuario):
    """
    Envía el texto transcrito a Gemini para obtener una respuesta
    """
    try:
        respuesta_chat = chat_session.send_message(texto_usuario)
        return respuesta_chat.text.strip()
    except Exception as e:
        print(f"Error en Gemini: {e}")
        return None

def texto_a_voz(text, output_file="respuesta_jarvis.mp3"):
    try:
        # Usamos el formato MP3 estandar (que es gratis)
        audio_generator = client_eleven.text_to_speech.convert(
            voice_id="ErXwobaYiN019PkySvjV",  # ID de Antoni
            model_id="eleven_multilingual_v2",
            text=text
        )
        
        # Guardamos el archivo MP3
        audio_bytes = b"".join(audio_generator)
        with open(output_file, "wb") as f:
            f.write(audio_bytes)
        
        # Reproducimos usando Pygame (que si lee MP3)
        try:
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            
            # Mantenemos el programa ocupado mientras suena el audio
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # Liberamos el archivo para poder sobrescribirlo despues
            pygame.mixer.music.unload()
            return True
            
        except Exception as e:
            print(f"Error reproduciendo audio: {e}")
            return False

    except Exception as e:
        print(f"Error generando voz con ElevenLabs: {e}")
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
                    # Guardar audio en formato WAV mono 16-bit (requerido por VOSK)
                    datos_grabacion = np.concatenate(buffer, axis=0)
                    
                    # Convertir a int16 para el formato WAV correcto
                    datos_int16 = np.int16(datos_grabacion * 32767)
                    write("temp_input.wav", fs, datos_int16)
                    
                    # Transcribir con VOSK (offline y rápido)
                    print("Transcribiendo...")
                    texto_usuario = transcribir_con_vosk("temp_input.wav")
                    
                    if texto_usuario and len(texto_usuario) > 0:
                        print(f"Usuario: {texto_usuario}")
                        
                        # Obtener respuesta de Gemini
                        print("Generando respuesta...")
                        respuesta_ai = obtener_respuesta_gemini(texto_usuario)
                        
                        if respuesta_ai:
                            print(f"Jarvis: {respuesta_ai}")
                            
                            # Generar y reproducir audio
                            print("Sintetizando voz...")
                            texto_a_voz(respuesta_ai)
                            print("-" * 50)
                        else:
                            print("No se pudo obtener respuesta de Gemini.")
                    else:
                        print("No se detecto voz o la transcripcion esta vacia.")
                        print("   Intenta hablar mas claro o mas cerca del microfono.")
                
                while keyboard.is_pressed(record_key):
                    pass
        
        if keyboard.is_pressed('q'):
            print("Apagando sistemas...")
            if stream:
                stream.stop()
                stream.close()
            # Limpieza final de pygame
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