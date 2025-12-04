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
import random

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

# 2. Configurar ElevenLabs
client_eleven = ElevenLabs(api_key=api_key_eleven)

# 3. Configurar VOSK
print("Cargando modelo de voz local (Vosk)...")
if not os.path.exists("model"):
    print("ERROR: No encuentro la carpeta 'model'.")
    print("Descarga 'vosk-model-small-es-0.42', descomprimelo y renombra la carpeta a 'model'.")
    exit()
    
try:
    vosk_model = Model("model")
    rec_vosk = KaldiRecognizer(vosk_model, 44100)
except Exception as e:
    print(f"Error cargando Vosk: {e}")
    exit()

# 4. Inicializar Audio Player
pygame.mixer.init()

# Configuracion de audio
fs = 44100
record_key = "r"

# --- VARIABLES DE JUEGO ---
jugadores = []
fase_juego = "inicio"  # Fases: inicio, registro, descripciones, revelacion, preguntas, analisis
ronda_actual = 0
turno_descripcion_actual = 0  # Controla quien debe describir
turno_adivinanza_actual = 0  # Controla quien debe adivinar
descripciones = {}  # {indice_jugador: descripcion}
adivinanzas = {}  # {ronda: {indice_adivinador: nombre_adivinado}}
revelaciones = {}  # {indice_jugador: nombre_revelado}
turnos_adivinanza = []
historial_completo = []
pregunta_actual = 0
jugadores_seleccionados_preguntas = []
model_gemini = None
chat_session = None
esperando_respuesta = False

print("-" * 60)
print("SISTEMA JARVIS - DINAMICA DE EQUIPO")
print(f"Presiona '{record_key}' para hablar. 'q' para salir.")
print("-" * 60)

def inicializar_chat_con_contexto():
    """Inicializa el chat de Gemini con el contexto del juego"""
    global model_gemini, chat_session
    
    prompt_sistema = f"""
Eres Jarvis, un asistente de inteligencia artificial facilitando una dinamica de equipo.
Los jugadores son: {', '.join(jugadores)}.

Tu rol es guiar la dinamica con elegancia y profesionalismo. Se conciso (maximo 2-3 oraciones).
No uses emojis. Manten un tono formal pero amigable.

IMPORTANTE: Cuando des instrucciones, menciona claramente el nombre del jugador que debe participar.
"""
    
    model_gemini = genai.GenerativeModel(
        model_name="gemini-2.5-pro",
        system_instruction=prompt_sistema
    )
    chat_session = model_gemini.start_chat(history=[])

def callback(indata, frames, time, status):
    if status:
        print(status)
    buffer.append(indata.copy())

def transcribir_con_vosk(audio_data):
    """Convierte el audio a texto usando Vosk"""
    audio_int16 = (audio_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    
    if rec_vosk.AcceptWaveform(audio_bytes):
        resultado = json.loads(rec_vosk.Result())
        return resultado.get("text", "")
    else:
        resultado = json.loads(rec_vosk.FinalResult())
        return resultado.get("text", "")

def obtener_respuesta_gemini(texto_usuario, contexto_adicional=""):
    """Envia texto a Gemini con contexto del juego"""
    try:
        if not texto_usuario or len(texto_usuario) < 2:
            return None
        
        prompt_completo = f"{contexto_adicional}\n\nUsuario: {texto_usuario}" if contexto_adicional else texto_usuario
        response = chat_session.send_message(prompt_completo)
        return response.text.strip()
    except Exception as e:
        print(f"Error Gemini: {e}")
        return None

def texto_a_voz(text, output_file="respuesta_jarvis.mp3"):
    try:
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

def procesar_inicio(texto):
    """Detecta si el usuario quiere iniciar el juego"""
    global fase_juego
    
    palabras_inicio = ["comenzar", "empezar", "iniciar", "jugar", "vamos", "hola", "empecemos", "inicio", "si", "dale"]
    
    if any(palabra in texto.lower() for palabra in palabras_inicio):
        fase_juego = "registro"
        return "Excelente. Comenzaremos registrando a los participantes. Por favor, digan su nombre uno por uno. El ultimo participante debe decir su nombre seguido de la palabra ultimo o final."
    else:
        return "Hola, soy Jarvis. Estoy listo para facilitar una dinamica de equipo. Dime cuando quieras comenzar."

def procesar_registro(texto):
    """Procesa el registro de jugadores"""
    global fase_juego, jugadores
    
    # Detectar si es el ultimo jugador
    es_ultimo = any(palabra in texto.lower() for palabra in ["ultimo", "ultima", "final", "listo", "ya esta", "terminamos"])
    
    # Extraer el nombre - tomamos la primera palabra que no sea una palabra de control
    palabras_control = ["soy", "me", "llamo", "mi", "nombre", "es", "ultimo", "ultima", "final"]
    palabras = texto.lower().split()
    nombre = None
    
    for palabra in palabras:
        if palabra not in palabras_control and len(palabra) > 2:
            nombre = palabra.capitalize()
            break
    
    if nombre and nombre not in jugadores:
        jugadores.append(nombre)
        print(f"   Registrado: {nombre} ({len(jugadores)}/4)")
        historial_completo.append(f"Jugador registrado: {nombre}")
    
    if es_ultimo and len(jugadores) >= 3:
        inicializar_chat_con_contexto()
        fase_juego = "descripciones"
        ronda_actual = 0
        return f"Perfecto. Tenemos {len(jugadores)} participantes: {', '.join(jugadores)}. Comenzaremos con la fase de descripciones. {jugadores[0]}, inicia tu dando una descripcion breve de alguno de tus companeros, sin decir su nombre."
    elif es_ultimo and len(jugadores) < 3:
        return f"Necesitamos al menos 3 jugadores. Actualmente tenemos {len(jugadores)}. Por favor, que se registre al menos un participante mas."
    elif len(jugadores) >= 4:
        inicializar_chat_con_contexto()
        fase_juego = "descripciones"
        return f"Tenemos el maximo de 4 jugadores: {', '.join(jugadores)}. Comenzaremos la dinamica. {jugadores[0]}, inicia tu dando una descripcion breve de alguno de tus companeros, sin decir su nombre."
    else:
        return f"Registrado. Tenemos {len(jugadores)} jugador{'es' if len(jugadores) > 1 else ''}. Siguiente participante, por favor."

def procesar_descripciones(texto):
    """Procesa la fase de descripciones - TODOS describen, uno por ronda"""
    global fase_juego, descripciones, ronda_actual, turnos_adivinanza, turno_adivinanza_actual
    
    jugador_actual = jugadores[ronda_actual]
    
    # Si este jugador aun no ha dado su descripcion
    if ronda_actual not in descripciones:
        descripciones[ronda_actual] = texto
        historial_completo.append(f"{jugador_actual} describio: {texto}")
        print(f"   Descripcion de {jugador_actual} guardada.")
        turnos_adivinanza = []
        turno_adivinanza_actual = 0
        
        # Los demas deben adivinar
        otros_indices = [i for i in range(len(jugadores)) if i != ronda_actual]
        siguiente_adivinador = jugadores[otros_indices[0]]
        return f"Descripcion registrada. {siguiente_adivinador}, a quien crees que {jugador_actual} describio?"
    
    # Si no, es una adivinanza
    else:
        # Extraer el nombre mencionado
        nombre_adivinado = None
        for nombre in jugadores:
            if nombre.lower() in texto.lower():
                nombre_adivinado = nombre
                break
        
        if nombre_adivinado:
            if ronda_actual not in adivinanzas:
                adivinanzas[ronda_actual] = {}
            
            otros_indices = [i for i in range(len(jugadores)) if i != ronda_actual]
            indice_adivinador = otros_indices[turno_adivinanza_actual]
            
            adivinanzas[ronda_actual][indice_adivinador] = nombre_adivinado
            turnos_adivinanza.append(indice_adivinador)
            historial_completo.append(f"{jugadores[indice_adivinador]} adivino: {nombre_adivinado}")
            print(f"   {jugadores[indice_adivinador]} adivino: {nombre_adivinado}")
        
        # Verificar si todos los demas ya adivinaron
        otros_indices = [i for i in range(len(jugadores)) if i != ronda_actual]
        turno_adivinanza_actual += 1
        
        if turno_adivinanza_actual >= len(otros_indices):
            # Pasar a la siguiente ronda
            ronda_actual += 1
            turno_adivinanza_actual = 0
            
            # Si terminamos todas las rondas de descripcion
            if ronda_actual >= len(jugadores):
                fase_juego = "revelacion"
                ronda_actual = 0
                return f"Excelente. Todas las descripciones completadas. Ahora viene la revelacion. {jugadores[0]}, revela a quien describiste tu."
            
            # Siguiente ronda
            siguiente_jugador = jugadores[ronda_actual]
            return f"Ronda completada. {siguiente_jugador}, ahora es tu turno. Da una descripcion de alguno de tus companeros."
        
        # Siguiente adivinador
        siguiente_adivinador = jugadores[otros_indices[turno_adivinanza_actual]]
        return f"{siguiente_adivinador}, tu turno. A quien crees que pertenece esta descripcion?"

def procesar_revelacion(texto):
    """Procesa las revelaciones"""
    global fase_juego, ronda_actual, revelaciones
    
    jugador_actual = jugadores[ronda_actual]
    
    # Extraer el nombre revelado
    nombre_revelado = None
    for nombre in jugadores:
        if nombre.lower() in texto.lower() and nombre != jugador_actual:
            nombre_revelado = nombre
            break
    
    if nombre_revelado:
        revelaciones[ronda_actual] = nombre_revelado
        historial_completo.append(f"{jugador_actual} revelo que describio a {nombre_revelado}")
        print(f"\n   {jugador_actual} describio a: {nombre_revelado}")
        
        # Mostrar aciertos
        if ronda_actual in adivinanzas:
            for idx_adivinador, nombre_adivinado in adivinanzas[ronda_actual].items():
                if nombre_adivinado == nombre_revelado:
                    print(f"   ✓ {jugadores[idx_adivinador]} ACERTO!")
                else:
                    print(f"   ✗ {jugadores[idx_adivinador]} penso que era {nombre_adivinado}")
    
    ronda_actual += 1
    
    # Si terminamos todas las revelaciones
    if ronda_actual >= len(jugadores):
        fase_juego = "preguntas"
        global jugadores_seleccionados_preguntas, pregunta_actual
        jugadores_seleccionados_preguntas = random.sample(range(len(jugadores)), 2)
        pregunta_actual = 0
        
        primer_jugador = jugadores[jugadores_seleccionados_preguntas[0]]
        historial_completo.append(f"Seleccionados para preguntas: {jugadores[jugadores_seleccionados_preguntas[0]]} y {jugadores[jugadores_seleccionados_preguntas[1]]}")
        
        return f"Revelaciones completadas. Ahora viene la fase final. {primer_jugador}, primera pregunta: Como describirias al grupo en una sola palabra?"
    
    # Siguiente revelacion
    siguiente = jugadores[ronda_actual]
    return f"{siguiente}, tu turno de revelar a quien describiste."

def procesar_preguntas(texto):
    """Procesa las respuestas a preguntas finales"""
    global fase_juego, pregunta_actual
    
    jugador_actual = jugadores[jugadores_seleccionados_preguntas[pregunta_actual]]
    historial_completo.append(f"{jugador_actual} respondio: {texto}")
    print(f"   Respuesta registrada: {texto}")
    
    pregunta_actual += 1
    
    # Despues de 2 respuestas, analisis
    if pregunta_actual >= 2:
        fase_juego = "analisis"
        contexto_completo = "\n".join(historial_completo)
        
        prompt_analisis = f"""
Basandote en toda la dinamica realizada:

{contexto_completo}

Genera un analisis de equipo profesional que incluya:
1. Las fortalezas identificadas del grupo
2. Como se complementan los miembros
3. Una sugerencia concreta para mejorar la comunicacion del equipo

Inicia diciendo: "He analizado todo lo que dijeron. Aqui tienen su informe de equipo."
Se conciso pero perspicaz. Maximo 6 oraciones.
"""
        return obtener_respuesta_gemini("Genera el analisis final", prompt_analisis)
    
    # Segunda pregunta
    segundo_jugador = jugadores[jugadores_seleccionados_preguntas[1]]
    return f"{segundo_jugador}, tu turno. Que cualidad como fortaleza identificas en el grupo?"

def procesar_entrada(texto):
    """Router principal segun fase del juego"""
    global fase_juego
    
    if fase_juego == "inicio":
        return procesar_inicio(texto)
    elif fase_juego == "registro":
        return procesar_registro(texto)
    elif fase_juego == "descripciones":
        return procesar_descripciones(texto)
    elif fase_juego == "revelacion":
        return procesar_revelacion(texto)
    elif fase_juego == "preguntas":
        return procesar_preguntas(texto)
    elif fase_juego == "analisis":
        return "La dinamica ha finalizado. Gracias por participar. Presiona 'q' para salir."
    
    return "Procesando..."

# SALUDO INICIAL CON VOZ
print("\n=== JARVIS INICIANDO ===")
saludo_inicial = "Bienvenidos. Soy Jarvis, su asistente para esta dinamica de equipo. Presionen la tecla R y digan cuando esten listos para comenzar."
print(f"Jarvis: {saludo_inicial}")
texto_a_voz(saludo_inicial)
print("-" * 60)

# Variables de control de audio
grabando = False
buffer = []
stream = None

while True:
    try:
        if keyboard.is_pressed(record_key):
            if not grabando:
                print("\n>> Escuchando...")
                grabando = True
                buffer = []
                stream = sd.InputStream(callback=callback, channels=1, samplerate=fs)
                stream.start()
                while keyboard.is_pressed(record_key):
                    pass
            else:
                print("   Procesando...")
                grabando = False
                stream.stop()
                stream.close()
                
                if len(buffer) > 0:
                    datos_grabacion = np.concatenate(buffer, axis=0)
                    texto_usuario = transcribir_con_vosk(datos_grabacion)
                    
                    if texto_usuario and len(texto_usuario) > 2:
                        print(f"\n[Transcrito]: {texto_usuario}")
                        
                        # Procesar segun fase
                        respuesta_jarvis = procesar_entrada(texto_usuario)
                        
                        if respuesta_jarvis:
                            print(f"\nJarvis: {respuesta_jarvis}")
                            texto_a_voz(respuesta_jarvis)
                            print("-" * 60)
                    else:
                        print("No se escucho nada claro. Intenta de nuevo.")
                
                while keyboard.is_pressed(record_key):
                    pass
        
        if keyboard.is_pressed('q'):
            print("\nApagando sistemas...")
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