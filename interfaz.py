import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw
import sounddevice as sd
import numpy as np
import pygame
import json
from vosk import Model, KaldiRecognizer
from elevenlabs.client import ElevenLabs
import os
import threading
from dotenv import load_dotenv
from demo_mdi_ia import AsistenteImpostor
import re

load_dotenv()

class InterfazImpostor:
    def __init__(self, root):
        self.root = root
        self.root.title("Jarvis - El Impostor Ecuatoriano")
        self.root.geometry("1000x750")
        self.root.configure(bg="#FFFFFF")
        
        # Asistente
        self.asistente = AsistenteImpostor()
        
        # Audio config
        self.fs = 44100
        self.grabando = False
        self.buffer = []
        self.stream = None
        self.procesando = False 
        
        # VOSK
        print("Cargando VOSK...")
        try:
            if not os.path.exists("model"):
                print("ERROR: No se encuentra la carpeta 'model'.")
                print("Descarga el modelo de: https://alphacephei.com/vosk/models")
            self.vosk_model = Model("model")
            self.rec_vosk = KaldiRecognizer(self.vosk_model, self.fs)
        except Exception as e:
            print(f"Error VOSK: {e}")
        
        # ElevenLabs Init
        api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key_eleven:
            print("ADVERTENCIA: No se encontro ELEVENLABS_API_KEY en .env")
        
        try:
            self.client_eleven = ElevenLabs(api_key=api_key_eleven)
        except Exception as e:
            print(f"Error al iniciar ElevenLabs: {e}")

        # Pygame Mixer
        pygame.mixer.init()
        
        # Cargar imagen IA
        self.cargar_imagen_ia()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Saludo inicial (con retraso)
        self.root.after(1000, self.saludo_inicial)
    
    def cargar_imagen_ia(self):
        """Carga imagen ia.png o crea un fallback"""
        try:
            img = Image.open("images/ia.png").resize((180, 180), Image.Resampling.LANCZOS)
            self.img_ia = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Aviso: Usando imagen generada (Error: {e})")
            size = 180
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([0, 0, size, size], fill=(77, 144, 254, 255)) # Azul Google
            self.img_ia = ImageTk.PhotoImage(img)
    
    def crear_interfaz(self):
        """Crea UI limpia y moderna sin emojis"""
        # Fuentes
        self.font_texto = tkfont.Font(family="Segoe UI", size=14)
        self.font_texto_app = tkfont.Font(family="Segoe UI", size=14)
        self.font_btn = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        
        # FUENTE GIGANTE PARA LA PALABRA OCULTA
        self.font_palabra_gigante = tkfont.Font(family="Segoe UI", size=40, weight="bold")
        
        self.font_estado = tkfont.Font(family="Segoe UI", size=11, slant="italic")
        
        # Espacio superior
        tk.Frame(self.root, bg="#FFFFFF", height=20).pack()
        
        # --- ÁREA CENTRAL (IMAGEN O PALABRA) ---
        # Usamos un Label que cambiará entre Imagen y Texto
        self.label_central = tk.Label(
            self.root, 
            bg="#FFFFFF", 
            image=self.img_ia,
            compound="center" # Permite centrar texto si no hay imagen
        )
        self.label_central.pack(pady=10)
        
        # Conversacion
        frame_conv = tk.Frame(self.root, bg="#FFFFFF")
        frame_conv.pack(pady=10, padx=60, fill="both", expand=True)
        
        self.texto_conv = tk.Text(
            frame_conv,
            font=self.font_texto,
            bg="#F8F9FA",
            fg="#333333",
            wrap="word",
            height=10,
            relief="flat",
            bd=10,
            highlightthickness=0,
            insertbackground="#0064FF"
        )
        self.texto_conv.pack(fill="both", expand=True)
        self.texto_conv.config(state="disabled")
        
        self.texto_conv.tag_config("app", foreground="#0064FF", font=self.font_texto_app)
        self.texto_conv.tag_config("user", foreground="#333333", font=self.font_texto)
        
        # Frame mostrar palabra (oculto inicialmente)
        self.frame_palabra = tk.Frame(self.root, bg="#FFFFFF")
        
        self.label_info_palabra = tk.Label(
            self.frame_palabra,
            text="",
            font=tkfont.Font(family="Segoe UI", size=13),
            fg="#666666",
            bg="#FFFFFF"
        )
        self.label_info_palabra.pack(pady=5)
        
        self.btn_ver_palabra = tk.Button(
            self.frame_palabra,
            text="Ver mi palabra",
            font=self.font_btn,
            bg="#FFFFFF",
            fg="#0064FF",
            activebackground="#F0F0F0",
            command=self.revelar_palabra_animada, # Nueva función
            relief="flat",
            bd=1,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.btn_ver_palabra.pack(pady=5)
        
        # Controles inferiores
        frame_ctrl = tk.Frame(self.root, bg="#FFFFFF")
        frame_ctrl.pack(pady=20, fill="x")
        
        # Contenedor para centrar botones
        frame_botones = tk.Frame(frame_ctrl, bg="#FFFFFF")
        frame_botones.pack()
        
        self.btn_grabar = tk.Button(
            frame_botones,
            text="MANTEN PARA HABLAR",
            font=self.font_btn,
            bg="#FFFFFF",
            fg="#D93025", # Rojo Google
            activebackground="#FCE8E6",
            activeforeground="#D93025",
            relief="solid",
            bd=1,
            padx=30,
            pady=15,
            cursor="hand2"
        )
        self.btn_grabar.pack(side="left", padx=20)
        
        # Bindings
        self.btn_grabar.bind("<ButtonPress-1>", self.iniciar_grabacion)
        self.btn_grabar.bind("<ButtonRelease-1>", self.detener_grabacion)
        
        self.btn_listo = tk.Button(
            frame_botones,
            text="LISTO",
            font=self.font_btn,
            bg="#FFFFFF",
            fg="#1E8E3E", # Verde Google
            activebackground="#E6F4EA",
            activeforeground="#1E8E3E",
            command=self.marcar_listo,
            relief="solid",
            bd=1,
            padx=30,
            pady=15,
            state="disabled",
            cursor="arrow"
        )
        self.btn_listo.pack(side="left", padx=20)
        
        # Estado
        self.label_estado = tk.Label(
            self.root,
            text="Inicializando sistema...",
            font=self.font_estado,
            fg="#999999",
            bg="#FFFFFF"
        )
        self.label_estado.pack(pady=10)
    
    def saludo_inicial(self):
        """Saludo en un hilo separado"""
        threading.Thread(target=self._saludo_thread).start()

    def _saludo_thread(self):
        msg = "Hola! Soy Jarvis. Presiona el boton rojo y di 'Hola' para comenzar."
        self.root.after(0, lambda: self.agregar_mensaje_app(msg))
        self.root.after(0, lambda: self.label_estado.config(text="Esperando voz..."))
        self.texto_a_voz(msg)
    
    # --- GUI UPDATES (Thread Safe) ---
    def agregar_mensaje_app(self, texto):
        self.texto_conv.config(state="normal")
        self.texto_conv.insert("end", "> ", "app")
        self.texto_conv.insert("end", texto + "\n\n", "app")
        self.texto_conv.see("end")
        self.texto_conv.config(state="disabled")
    
    def agregar_mensaje_usuario(self, nombre, texto):
        self.texto_conv.config(state="normal")
        self.texto_conv.insert("end", f"> {nombre}: ", "user")
        self.texto_conv.insert("end", texto + "\n\n", "user")
        self.texto_conv.see("end")
        self.texto_conv.config(state="disabled")
    
    # --- AUDIO LOGIC ---
    def iniciar_grabacion(self, event):
        if not self.grabando and not self.procesando:
            try:
                self.grabando = True
                self.buffer = []
                self.btn_grabar.config(text="ESCUCHANDO...", bg="#FCE8E6", fg="#D93025")
                self.label_estado.config(text="Escuchando...")
                
                # Iniciar stream
                self.stream = sd.InputStream(
                    callback=self.audio_callback,
                    channels=1,
                    samplerate=self.fs,
                    blocksize=4000
                )
                self.stream.start()
            except Exception as e:
                print(f"Error Mic: {e}")
                self.grabando = False
                self.label_estado.config(text="Error de microfono")
    
    def detener_grabacion(self, event):
        if self.grabando:
            self.grabando = False
            self.btn_grabar.config(text="MANTEN PARA HABLAR", bg="#FFFFFF", fg="#D93025")
            self.label_estado.config(text="Procesando...")
            
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
            
            # Usar Threading para no congelar
            if len(self.buffer) > 0:
                self.procesando = True
                threading.Thread(target=self._procesar_audio_thread).start()
            else:
                self.label_estado.config(text="Audio muy corto")
    
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.buffer.append(indata.copy())
    
    def _procesar_audio_thread(self):
        """Lógica pesada en hilo secundario"""
        try:
            # Transcribir VOSK
            datos = np.concatenate(self.buffer, axis=0)
            audio_int16 = (datos * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            texto = ""
            if self.rec_vosk.AcceptWaveform(audio_bytes):
                resultado = json.loads(self.rec_vosk.Result())
                texto = resultado.get("text", "")
            else:
                resultado = json.loads(self.rec_vosk.FinalResult())
                texto = resultado.get("text", "")
            
            if texto and len(texto) > 2:
                # 1. Mostrar usuario
                info = self.asistente.obtener_info_ui()
                nombre = info.get("jugador_actual") or info.get("mostrando_a") or "Usuario"
                self.root.after(0, lambda: self.agregar_mensaje_usuario(nombre, texto))
                self.root.after(0, lambda: self.label_estado.config(text="Pensando..."))
                
                # 2. Llamar IA
                respuesta = self.asistente.procesar_entrada(texto)
                respuesta_limpia = self.limpiar_comandos(respuesta)
                
                # 3. Mostrar respuesta IA
                self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
                self.root.after(0, lambda: self.label_estado.config(text="Hablando..."))
                
                # 4. Hablar (ElevenLabs)
                self.texto_a_voz(respuesta_limpia)
                
                # 5. Actualizar UI final
                self.root.after(0, self.actualizar_ui)
                
            else:
                self.root.after(0, lambda: self.label_estado.config(text="No entendi, intenta de nuevo"))
                
        except Exception as e:
            print(f"Error Processing: {e}")
            self.root.after(0, lambda: self.label_estado.config(text="Error interno"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.label_estado.config(text="Esperando..."))

    def limpiar_comandos(self, texto):
        return re.sub(r'\[.*?\]', '', texto).strip()
    
    def actualizar_ui(self):
        """Actualiza estado de botones"""
        info = self.asistente.obtener_info_ui()
        fase = info["fase"]
        
        # Resetear visuales comunes
        self.frame_palabra.pack_forget()
        self.btn_listo.config(state="disabled", cursor="arrow")
        
        # Asegurarse que la imagen esté visible si no estamos revelando nada
        if self.label_central.cget("text") == "":
             self.label_central.config(image=self.img_ia)

        if fase == "inicio":
            self.label_estado.config(text="Presiona Grabar y di 'Comenzar'")
        
        elif fase == "registro":
            n = len(info['jugadores'])
            self.label_estado.config(text=f"Registro: {n}/5 jugadores (Di tu nombre)")
        
        elif fase == "mostrando_palabras":
            mostrando = info.get("mostrando_a")
            if mostrando:
                self.label_estado.config(text=f"Turno de {mostrando}")
                self.label_info_palabra.config(text=f"{mostrando}, mira tu rol:")
                self.frame_palabra.pack(pady=10)
                
                self.btn_ver_palabra.config(state="normal")
                # El botón listo se habilita solo despues de ver la palabra
                self.btn_listo.config(state="disabled", cursor="arrow")
        
        elif fase == "jugando":
            jugador = info.get("jugador_actual", "")
            self.label_estado.config(text=f"Turno de {jugador} - Di tu pista")
        
        elif fase == "decision_ronda":
            self.label_estado.config(text="Otra ronda o votar?")
        
        elif fase == "votacion":
            self.label_estado.config(text="VOTACION - Di un nombre")
            
        elif fase == "resultado":
            self.label_estado.config(text="Juego terminado!")
    
    def revelar_palabra_animada(self):
        """Muestra la palabra reemplazando la imagen por 3 segundos"""
        info = self.asistente.obtener_info_ui()
        es_impostor = info.get("es_impostor", False)
        palabra = info.get("palabra")
        
        # 1. Definir texto y color
        if es_impostor:
            texto_mostrar = "¡ERES EL\nIMPOSTOR!"
            color_mostrar = "#D93025" # Rojo
        elif palabra:
            texto_mostrar = palabra.upper()
            color_mostrar = "#1E8E3E" # Verde
        else:
            texto_mostrar = "ERROR"
            color_mostrar = "orange"

        # 2. Ocultar Imagen y Mostrar Texto en el Label Central
        self.label_central.config(
            image="", 
            text=texto_mostrar, 
            font=self.font_palabra_gigante, 
            fg=color_mostrar
        )
        
        # 3. Deshabilitar boton "Ver palabra"
        self.btn_ver_palabra.config(state="disabled")
        self.label_estado.config(text="Memoriza tu palabra...")

        # 4. Programar restauración en 3 segundos
        self.root.after(3000, self.restaurar_imagen_y_habilitar_listo)

    def restaurar_imagen_y_habilitar_listo(self):
        """Restaura la imagen y permite continuar"""
        # Volver a poner la imagen
        self.label_central.config(image=self.img_ia, text="")
        
        # Habilitar botón LISTO
        self.btn_listo.config(state="normal", cursor="hand2")
        self.label_estado.config(text="Presiona LISTO para continuar")

    def marcar_listo(self):
        """Acción del botón Listo"""
        self.btn_listo.config(state="disabled")
        threading.Thread(target=self._marcar_listo_thread).start()

    def _marcar_listo_thread(self):
        respuesta = self.asistente.procesar_entrada("listo ya vi")
        respuesta_limpia = self.limpiar_comandos(respuesta)
        
        self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
        self.texto_a_voz(respuesta_limpia)
        self.root.after(0, self.actualizar_ui)
    
    def texto_a_voz(self, text):
        """TTS ElevenLabs (Sincrono, ejecutado en hilo separado)"""
        try:
            self.root.after(0, lambda: self.label_estado.config(text="Jarvis hablando..."))
            
            audio_gen = self.client_eleven.text_to_speech.convert(
                voice_id="pNInz6obpgDQGcFmaJgB",
                model_id="eleven_multilingual_v2",
                text=text
            )
            
            audio_bytes = b"".join(audio_gen)
            
            archivo_audio = "temp_jarvis.mp3"
            with open(archivo_audio, "wb") as f:
                f.write(audio_bytes)
            
            pygame.mixer.music.load(archivo_audio)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            pygame.mixer.music.unload()
            
            self.root.after(0, lambda: self.label_estado.config(text="Listo para continuar"))
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error TTS ElevenLabs: {e}")
            msg_error = "Error en audio"
            if "401" in error_msg or "quota" in error_msg.lower():
                msg_error = "Sin creditos ElevenLabs"
            self.root.after(0, lambda: self.label_estado.config(text=msg_error))

def main():
    root = tk.Tk()
    app = InterfazImpostor(root)
    root.mainloop()

if __name__ == "__main__":
    main()