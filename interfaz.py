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
            self.vosk_model = Model("model")
            self.rec_vosk = KaldiRecognizer(self.vosk_model, self.fs)
        except Exception as e:
            print(f"Error VOSK: {e}")
        
        # ElevenLabs
        api_key_eleven = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key_eleven:
            print("ADVERTENCIA: No se encontró ELEVENLABS_API_KEY")
        
        try:
            self.client_eleven = ElevenLabs(api_key=api_key_eleven)
        except Exception as e:
            print(f"Error ElevenLabs: {e}")

        # Pygame
        pygame.mixer.init()
        
        # Cargar imagen
        self.cargar_imagen_ia()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Saludo inicial
        self.root.after(1000, self.saludo_inicial)
    
    def cargar_imagen_ia(self):
        """Carga imagen ia.png o crea fallback"""
        try:
            img = Image.open("images/ia.png").resize((180, 180), Image.Resampling.LANCZOS)
            self.img_ia = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Usando imagen generada")
            size = 180
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([0, 0, size, size], fill=(77, 144, 254, 255))
            self.img_ia = ImageTk.PhotoImage(img)
    
    def crear_interfaz(self):
        """Crea UI moderna"""
        # Fuentes
        self.font_texto = tkfont.Font(family="Segoe UI", size=14)
        self.font_texto_app = tkfont.Font(family="Segoe UI", size=14)
        self.font_btn = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_palabra_gigante = tkfont.Font(family="Segoe UI", size=40, weight="bold")
        self.font_estado = tkfont.Font(family="Segoe UI", size=11, slant="italic")
        
        # Espacio superior
        tk.Frame(self.root, bg="#FFFFFF", height=20).pack()
        
        # Label central (imagen o palabra)
        self.label_central = tk.Label(
            self.root, 
            bg="#FFFFFF", 
            image=self.img_ia,
            compound="center"
        )
        self.label_central.pack(pady=10)
        
        # Conversación
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
        
        # Frame palabra (oculto inicialmente)
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
            command=self.revelar_palabra_animada,
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
        
        frame_botones = tk.Frame(frame_ctrl, bg="#FFFFFF")
        frame_botones.pack()
        
        self.btn_grabar = tk.Button(
            frame_botones,
            text="MANTÉN PARA HABLAR",
            font=self.font_btn,
            bg="#FFFFFF",
            fg="#D93025",
            activebackground="#FCE8E6",
            activeforeground="#D93025",
            relief="solid",
            bd=1,
            padx=30,
            pady=15,
            cursor="hand2"
        )
        self.btn_grabar.pack(side="left", padx=20)
        
        self.btn_grabar.bind("<ButtonPress-1>", self.iniciar_grabacion)
        self.btn_grabar.bind("<ButtonRelease-1>", self.detener_grabacion)
        
        self.btn_listo = tk.Button(
            frame_botones,
            text="LISTO",
            font=self.font_btn,
            bg="#FFFFFF",
            fg="#1E8E3E",
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
        """Saludo en hilo separado"""
        threading.Thread(target=self._saludo_thread, daemon=True).start()

    def _saludo_thread(self):
        msg = "Hola! Soy Jarvis. Presiona el botón rojo y di 'Hola' para comenzar."
        self.root.after(0, lambda: self.agregar_mensaje_app(msg))
        self.root.after(0, lambda: self.label_estado.config(text="Esperando voz..."))
        self.texto_a_voz(msg)
    
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
    
    def iniciar_grabacion(self, event):
        if not self.grabando and not self.procesando:
            try:
                self.grabando = True
                self.buffer = []
                self.btn_grabar.config(text="ESCUCHANDO...", bg="#FCE8E6", fg="#D93025")
                self.label_estado.config(text="Escuchando...")
                
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
                self.label_estado.config(text="Error de micrófono")
    
    def detener_grabacion(self, event):
        if self.grabando:
            self.grabando = False
            self.btn_grabar.config(text="MANTÉN PARA HABLAR", bg="#FFFFFF", fg="#D93025")
            self.label_estado.config(text="Procesando...")
            
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass
            
            if len(self.buffer) > 0:
                self.procesando = True
                threading.Thread(target=self._procesar_audio_thread, daemon=True).start()
            else:
                self.label_estado.config(text="Audio muy corto")
    
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.buffer.append(indata.copy())
    
    def _procesar_audio_thread(self):
        """Procesamiento de audio en hilo secundario"""
        try:
            # Transcribir
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
                # Mostrar usuario
                info = self.asistente.obtener_info_ui()
                nombre = info.get("jugador_actual") or info.get("mostrando_a") or "Usuario"
                self.root.after(0, lambda: self.agregar_mensaje_usuario(nombre, texto))
                self.root.after(0, lambda: self.label_estado.config(text="Pensando..."))
                
                # Llamar IA
                respuesta = self.asistente.procesar_entrada(texto)
                respuesta_limpia = self.limpiar_comandos(respuesta)
                
                # Mostrar respuesta
                self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
                self.root.after(0, lambda: self.label_estado.config(text="Hablando..."))
                
                # Hablar
                self.texto_a_voz(respuesta_limpia)
                
                # Actualizar UI
                self.root.after(0, self.actualizar_ui)
                
            else:
                self.root.after(0, lambda: self.label_estado.config(text="No entendí, intenta de nuevo"))
                
        except Exception as e:
            print(f"Error Processing: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.label_estado.config(text="Error interno"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.label_estado.config(text="Esperando..."))

    def limpiar_comandos(self, texto):
        return re.sub(r'\[.*?\]', '', texto).strip()
    
    def actualizar_ui(self):
        """Actualiza estado de botones - MEJORADO"""
        info = self.asistente.obtener_info_ui()
        fase = info["fase"]
        
        print(f"\n[UI UPDATE] Fase: {fase}, Turno: {info['turno']}")
        
        # Reset
        self.frame_palabra.pack_forget()
        self.btn_listo.config(state="disabled", cursor="arrow")
        self.btn_ver_palabra.config(state="normal")
        
        # Restaurar imagen si no hay texto
        if self.label_central.cget("text") == "":
             self.label_central.config(image=self.img_ia)

        if fase == "inicio":
            self.label_estado.config(text="Presiona Grabar y di 'Comenzar'")
        
        elif fase == "registro":
            n = len(info['jugadores'])
            self.label_estado.config(text=f"Registro: {n} jugadores (Di tu nombre)")
        
        elif fase == "mostrando_palabras":
            mostrando = info.get("mostrando_a")
            if mostrando:
                self.label_estado.config(text=f"Turno de {mostrando} - Ver palabra")
                self.label_info_palabra.config(text=f"{mostrando}, presiona el botón:")
                self.frame_palabra.pack(pady=10)
                self.btn_ver_palabra.config(state="normal")
                self.btn_listo.config(state="disabled", cursor="arrow")
                
                print(f"[UI] Mostrando panel para: {mostrando}")
        
        elif fase == "jugando":
            jugador = info.get("jugador_actual", "")
            self.label_estado.config(text=f"Turno de {jugador} - Da tu pista")
        
        elif fase == "decision_ronda":
            self.label_estado.config(text="¿Otra ronda o votar?")
        
        elif fase == "votacion":
            votante = info.get("jugador_actual", "")
            self.label_estado.config(text=f"VOTACIÓN - {votante}, ¿a quién votas?")
            
        elif fase == "resultado":
            self.label_estado.config(text="¡Juego terminado!")
    
    def revelar_palabra_animada(self):
        """Muestra la palabra reemplazando la imagen"""
        info = self.asistente.obtener_info_ui()
        es_impostor = info.get("es_impostor", False)
        palabra = info.get("palabra")
        
        print(f"\n[REVELAR] Es impostor: {es_impostor}, Palabra: {palabra}")
        
        # Definir texto y color
        if es_impostor:
            texto_mostrar = "¡ERES EL\nIMPOSTOR!"
            color_mostrar = "#D93025"
        elif palabra:
            texto_mostrar = palabra.upper()
            color_mostrar = "#1E8E3E"
        else:
            texto_mostrar = "ERROR"
            color_mostrar = "orange"

        # Ocultar imagen y mostrar texto
        self.label_central.config(
            image="", 
            text=texto_mostrar, 
            font=self.font_palabra_gigante, 
            fg=color_mostrar
        )
        
        # Deshabilitar botón "Ver palabra"
        self.btn_ver_palabra.config(state="disabled")
        self.label_estado.config(text="Memoriza tu palabra...")

        # Restaurar en 3 segundos
        self.root.after(3000, self.restaurar_imagen_y_habilitar_listo)

    def restaurar_imagen_y_habilitar_listo(self):
        """Restaura la imagen y habilita botón Listo"""
        print("[UI] Restaurando imagen y habilitando LISTO")
        
        # Restaurar imagen
        self.label_central.config(image=self.img_ia, text="")
        
        # Habilitar LISTO
        self.btn_listo.config(state="normal", cursor="hand2")
        self.label_estado.config(text="Presiona LISTO cuando estés listo")

    def marcar_listo(self):
        """Acción del botón Listo - CRÍTICO"""
        print("\n[MARCAR LISTO] Botón presionado")
        
        # Deshabilitar inmediatamente para evitar doble click
        self.btn_listo.config(state="disabled", cursor="arrow")
        self.label_estado.config(text="Procesando...")
        
        # Procesar en hilo separado
        threading.Thread(target=self._marcar_listo_thread, daemon=True).start()

    def _marcar_listo_thread(self):
        """Procesa el comando Listo"""
        try:
            print("[LISTO THREAD] Enviando 'listo' al asistente")
            
            # Enviar comando al asistente
            respuesta = self.asistente.procesar_entrada("listo")
            respuesta_limpia = self.limpiar_comandos(respuesta)
            
            print(f"[LISTO THREAD] Respuesta: {respuesta_limpia}")
            
            # Mostrar en UI
            self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
            
            # Hablar
            self.texto_a_voz(respuesta_limpia)
            
            # Actualizar UI
            self.root.after(0, self.actualizar_ui)
            
        except Exception as e:
            print(f"[ERROR LISTO] {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.label_estado.config(text="Error al procesar"))
    
    def texto_a_voz(self, text):
        """TTS ElevenLabs"""
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
            print(f"Error TTS: {e}")
            msg_error = "Error en audio"
            if "401" in error_msg or "quota" in error_msg.lower():
                msg_error = "Sin créditos ElevenLabs"
            self.root.after(0, lambda: self.label_estado.config(text=msg_error))

def main():
    root = tk.Tk()
    app = InterfazImpostor(root)
    root.mainloop()

if __name__ == "__main__":
    main()