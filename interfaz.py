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
        
        # Audio
        self.fs = 44100
        self.grabando = False
        self.buffer = []
        self.stream = None
        
        # VOSK
        print("Cargando VOSK...")
        try:
            self.vosk_model = Model("model")
            self.rec_vosk = KaldiRecognizer(self.vosk_model, self.fs)
        except Exception as e:
            print(f"Error VOSK: {e}")
            exit()
        
        # ElevenLabs
        api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")
        self.client_eleven = ElevenLabs(api_key=api_key_eleven)
        pygame.mixer.init()
        
        # Cargar imagen IA
        self.cargar_imagen_ia()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Saludo inicial
        self.root.after(800, self.saludo_inicial)
    
    def cargar_imagen_ia(self):
        """Carga imagen ia.png"""
        try:
            img = Image.open("images/ia.png").resize((180, 180), Image.Resampling.LANCZOS)
            self.img_ia = ImageTk.PhotoImage(img)
            print("Imagen IA cargada correctamente")
        except Exception as e:
            print(f"Error cargando ia.png: {e}")
            # Crear circulo azul como fallback
            size = 180
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            for i in range(size//2):
                r = int(0 + (100 * i / (size//2)))
                g = int(100 + (150 * i / (size//2)))
                b = int(255)
                draw.ellipse([i, i, size-i, size-i], fill=(r, g, b, 255))
            self.img_ia = ImageTk.PhotoImage(img)
    
    def crear_interfaz(self):
        """Crea UI limpia y moderna"""
        # Fuentes
        font_texto = tkfont.Font(family="Segoe UI", size=14)
        font_texto_app = tkfont.Font(family="Segoe UI", size=14)
        font_btn = tkfont.Font(family="Segoe UI", size=13)
        font_palabra = tkfont.Font(family="Segoe UI", size=24, weight="bold")
        
        # Espacio superior
        tk.Frame(self.root, bg="#FFFFFF", height=40).pack()
        
        # Circulo IA
        self.label_imagen = tk.Label(self.root, bg="#FFFFFF", image=self.img_ia)
        self.label_imagen.pack(pady=20)
        
        # Conversacion
        frame_conv = tk.Frame(self.root, bg="#FFFFFF")
        frame_conv.pack(pady=20, padx=60, fill="both", expand=True)
        
        self.texto_conv = tk.Text(
            frame_conv,
            font=font_texto,
            bg="#FFFFFF",
            fg="#333333",
            wrap="word",
            height=10,
            relief="flat",
            bd=0,
            highlightthickness=0,
            insertbackground="#0064FF"
        )
        self.texto_conv.pack(fill="both", expand=True)
        self.texto_conv.config(state="disabled")
        
        # Configurar tags para colores
        self.texto_conv.tag_config("app", foreground="#4D90FE", font=font_texto_app)
        self.texto_conv.tag_config("user", foreground="#333333", font=font_texto)
        
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
            font=font_btn,
            bg="#FFFFFF",
            fg="#0064FF",
            activebackground="#F0F0F0",
            activeforeground="#0064FF",
            command=self.revelar_palabra,
            relief="flat",
            bd=0,
            padx=25,
            pady=12,
            cursor="hand2",
            highlightthickness=0
        )
        self.btn_ver_palabra.pack(pady=8)
        self._add_button_shadow(self.btn_ver_palabra)
        
        self.label_palabra_revelada = tk.Label(
            self.frame_palabra,
            text="",
            font=font_palabra,
            fg="#0064FF",
            bg="#FFFFFF"
        )
        
        # Controles inferiores
        frame_ctrl = tk.Frame(self.root, bg="#FFFFFF")
        frame_ctrl.pack(pady=30)
        
        self.btn_grabar = tk.Button(
            frame_ctrl,
            text="Grabar",
            font=font_btn,
            bg="#FFFFFF",
            fg="#0064FF",
            activebackground="#F0F0F0",
            activeforeground="#0064FF",
            relief="flat",
            bd=0,
            padx=40,
            pady=15,
            cursor="hand2",
            highlightthickness=0
        )
        self.btn_grabar.pack(side="left", padx=15)
        self.btn_grabar.bind("<ButtonPress-1>", self.iniciar_grabacion)
        self.btn_grabar.bind("<ButtonRelease-1>", self.detener_grabacion)
        self._add_button_shadow(self.btn_grabar)
        
        self.btn_listo = tk.Button(
            frame_ctrl,
            text="Listo",
            font=font_btn,
            bg="#FFFFFF",
            fg="#0064FF",
            activebackground="#F0F0F0",
            activeforeground="#0064FF",
            command=self.marcar_listo,
            relief="flat",
            bd=0,
            padx=40,
            pady=15,
            state="disabled",
            cursor="hand2",
            highlightthickness=0
        )
        self.btn_listo.pack(side="left", padx=15)
        self._add_button_shadow(self.btn_listo)
        
        # Estado
        self.label_estado = tk.Label(
            self.root,
            text="Inicializando sistema...",
            font=tkfont.Font(family="Segoe UI", size=11),
            fg="#999999",
            bg="#FFFFFF"
        )
        self.label_estado.pack(pady=15)
    
    def _add_button_shadow(self, button):
        """Agrega efecto de sombra al boton"""
        def on_enter(e):
            button.config(bg="#F5F8FF")
        
        def on_leave(e):
            if button['state'] != 'disabled':
                button.config(bg="#FFFFFF")
        
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
    
    def saludo_inicial(self):
        """Saludo"""
        msg = "Hola! Soy Jarvis. Vamos a jugar al Impostor ecuatoriano. Cuando esten listos, presionen el boton del microfono y diganme."
        self.agregar_mensaje_app(msg)
        self.texto_a_voz(msg)
        self.label_estado.config(text="Esperando que inicien el juego...")
    
    def agregar_mensaje_app(self, texto):
        """Agrega mensaje de la app con prefijo >"""
        self.texto_conv.config(state="normal")
        self.texto_conv.insert("end", "> ", "app")
        self.texto_conv.insert("end", texto + "\n\n", "app")
        self.texto_conv.see("end")
        self.texto_conv.config(state="disabled")
    
    def agregar_mensaje_usuario(self, nombre, texto):
        """Agrega mensaje del usuario con prefijo >"""
        self.texto_conv.config(state="normal")
        self.texto_conv.insert("end", f"> {nombre}: ", "user")
        self.texto_conv.insert("end", texto + "\n\n", "user")
        self.texto_conv.see("end")
        self.texto_conv.config(state="disabled")
    
    def iniciar_grabacion(self, event):
        """Inicia grabacion"""
        if not self.grabando:
            self.grabando = True
            self.buffer = []
            self.btn_grabar.config(
                text="Grabando...",
                fg="#FF0000"
            )
            self.label_estado.config(text="Escuchando...")
            
            self.stream = sd.InputStream(
                callback=self.audio_callback,
                channels=1,
                samplerate=self.fs
            )
            self.stream.start()
    
    def detener_grabacion(self, event):
        """Detiene y procesa"""
        if self.grabando:
            self.grabando = False
            self.btn_grabar.config(
                text="Grabar",
                fg="#0064FF"
            )
            self.label_estado.config(text="Procesando audio...")
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            if len(self.buffer) > 0:
                self.root.after(100, self.procesar_audio)
    
    def audio_callback(self, indata, frames, time, status):
        """Callback audio"""
        if status:
            print(status)
        self.buffer.append(indata.copy())
    
    def procesar_audio(self):
        """Transcribe y procesa"""
        try:
            # Transcribir VOSK
            datos = np.concatenate(self.buffer, axis=0)
            audio_int16 = (datos * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            if self.rec_vosk.AcceptWaveform(audio_bytes):
                resultado = json.loads(self.rec_vosk.Result())
                texto = resultado.get("text", "")
            else:
                resultado = json.loads(self.rec_vosk.FinalResult())
                texto = resultado.get("text", "")
            
            if texto and len(texto) > 2:
                # Determinar hablante
                info = self.asistente.obtener_info_ui()
                
                if info.get("jugador_actual"):
                    nombre = info["jugador_actual"]
                elif info["fase"] == "mostrando_palabras" and info.get("mostrando_a"):
                    nombre = info["mostrando_a"]
                else:
                    nombre = "Usuario"
                
                # Mostrar lo dicho
                self.agregar_mensaje_usuario(nombre, texto)
                
                # Procesar con IA
                self.label_estado.config(text="Jarvis esta pensando...")
                self.root.update()
                
                respuesta = self.asistente.procesar_entrada(texto)
                respuesta_limpia = self.limpiar_comandos(respuesta)
                
                # Mostrar respuesta
                self.agregar_mensaje_app(respuesta_limpia)
                self.texto_a_voz(respuesta_limpia)
                
                # Actualizar UI
                self.actualizar_ui()
            else:
                self.label_estado.config(text="No se escucho nada claro")
                
        except Exception as e:
            print(f"Error: {e}")
            self.label_estado.config(text="Error al procesar")
    
    def limpiar_comandos(self, texto):
        """Quita [COMANDOS]"""
        return re.sub(r'\[.*?\]', '', texto).strip()
    
    def actualizar_ui(self):
        """Actualiza UI segun fase"""
        info = self.asistente.obtener_info_ui()
        fase = info["fase"]
        
        if fase == "inicio":
            self.label_estado.config(text="Esperando iniciar...")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
            self.frame_palabra.pack_forget()
        
        elif fase == "registro":
            n = len(info['jugadores'])
            self.label_estado.config(text=f"Registro: {n}/5 jugadores")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
            self.frame_palabra.pack_forget()
        
        elif fase == "mostrando_palabras":
            mostrando = info.get("mostrando_a")
            if mostrando:
                self.label_estado.config(text=f"{mostrando} debe ver su palabra/rol")
                self.label_info_palabra.config(text=f"{mostrando}, haz clic para ver:")
                self.frame_palabra.pack(pady=12)
                self.btn_ver_palabra.config(state="normal", fg="#0064FF")
                self.btn_listo.config(state="normal", fg="#0064FF")
                self.label_palabra_revelada.pack_forget()
        
        elif fase == "jugando":
            jugador = info.get("jugador_actual", "")
            self.label_estado.config(text=f"Turno de {jugador} - Da tu pista")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
            self.frame_palabra.pack_forget()
        
        elif fase == "decision_ronda":
            self.label_estado.config(text="Otra ronda o votar al impostor?")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
        
        elif fase == "votacion":
            self.label_estado.config(text="VOTACION - Quien es el impostor?")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
        
        elif fase == "resultado":
            self.label_estado.config(text="Juego terminado!")
            self.btn_listo.config(state="disabled", fg="#CCCCCC")
    
    def revelar_palabra(self):
        """Revela palabra/rol"""
        info = self.asistente.obtener_info_ui()
        
        if info["fase"] == "mostrando_palabras":
            es_impostor = info.get("es_impostor", False)
            palabra = info.get("palabra")
            
            if es_impostor:
                self.label_palabra_revelada.config(
                    text="ERES EL IMPOSTOR",
                    fg="#FF0000"
                )
            else:
                self.label_palabra_revelada.config(
                    text=f"{palabra.upper()}",
                    fg="#00AA00"
                )
            
            self.label_palabra_revelada.pack(pady=15)
            self.btn_ver_palabra.config(state="disabled", fg="#CCCCCC")
    
    def marcar_listo(self):
        """Boton listo"""
        respuesta = self.asistente.procesar_entrada("listo ya vi")
        respuesta_limpia = self.limpiar_comandos(respuesta)
        
        self.agregar_mensaje_app(respuesta_limpia)
        self.texto_a_voz(respuesta_limpia)
        self.actualizar_ui()
    
    def texto_a_voz(self, text):
        """TTS ElevenLabs"""
        try:
            self.label_estado.config(text="Jarvis hablando...")
            self.root.update()
            
            audio_gen = self.client_eleven.text_to_speech.convert(
                voice_id="pNInz6obpgDQGcFmaJgB",
                model_id="eleven_multilingual_v2",
                text=text
            )
            
            audio_bytes = b"".join(audio_gen)
            with open("temp_jarvis.mp3", "wb") as f:
                f.write(audio_bytes)
            
            pygame.mixer.music.load("temp_jarvis.mp3")
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                self.root.update()
            
            pygame.mixer.music.unload()
            self.label_estado.config(text="Listo para continuar")
            
        except Exception as e:
            print(f"Error TTS: {e}")
            self.label_estado.config(text="Error en audio")

def main():
    root = tk.Tk()
    app = InterfazImpostor(root)
    root.mainloop()

if __name__ == "__main__":
    main()