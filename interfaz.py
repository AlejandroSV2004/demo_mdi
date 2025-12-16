import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw
import sounddevice as sd
import numpy as np
import pygame
import json
from vosk import Model, KaldiRecognizer
import edge_tts
import asyncio
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
        self.root.geometry("1000x1015")
        
        # --- PALETA DE COLORES MODO OSCURO ---
        self.C_FONDO_MAIN = "#000000"      # Negro puro para fusionarse con el GIF
        self.C_FONDO_CAJA = "#1E1E1E"      # Gris oscuro para la caja de chat
        self.C_TEXTO_PRIM = "#E0E0E0"      # Texto principal claro (casi blanco)
        self.C_TEXTO_SEC = "#A0A0A0"       # Texto secundario (estado, instrucciones)
        
        self.C_AZUL_IA = "#4D90FE"         # Azul brillante para la IA
        self.C_ROJO_BTN = "#FF4D4D"        # Rojo brillante para botón grabar
        self.C_ROJO_BG_ACT = "#4A1515"     # Fondo rojo oscuro al grabar
        self.C_VERDE_BTN = "#00C853"       # Verde brillante para botón listo
        self.C_VERDE_BG_ACT = "#0A2E0A"    # Fondo verde oscuro activo
        
        self.C_BOTON_BG = "#2D2D30"        # Fondo de botón oscuro estándar
        self.C_BOTON_ACTIVE = "#3E3E42"    # Fondo de botón al pasar el mouse
        # -------------------------------------

        self.root.configure(bg=self.C_FONDO_MAIN)
        
        # Asistente
        self.asistente = AsistenteImpostor()
        
        # Audio config
        self.fs = 44100
        self.grabando = False
        self.buffer = []
        self.stream = None
        self.procesando = False 
        
        # Variables de Animación GIF
        self.frames_gif = []
        self.frame_index = 0
        self.animando = False
        self.gif_delay = 50 # Velocidad del GIF (menor número = más rápido)
        
        # VOSK
        print("Cargando VOSK...")
        try:
            if not os.path.exists("model"):
                print("ERROR: No se encuentra la carpeta 'model'.")
                self.rec_vosk = None
            else:
                self.vosk_model = Model("model")
                self.rec_vosk = KaldiRecognizer(self.vosk_model, self.fs)
        except Exception as e:
            print(f"Error VOSK: {e}")
            self.rec_vosk = None
        
        # Pygame
        pygame.mixer.init()
        
        # Cargar imagen/GIF
        self.cargar_imagen_ia()
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Saludo inicial
        self.root.after(1000, self.saludo_inicial)
    
    def cargar_imagen_ia(self):
        """Carga ia.gif y lo descompone en frames para animación"""
        try:
            img_path = "images/ia.gif" 
            
            if not os.path.exists(img_path) and os.path.exists("ia.gif"):
                 img_path = "ia.gif"

            gif_org = Image.open(img_path)
            
            self.frames_gif = []
            self.gif_delay = gif_org.info.get('duration', 50)
            
            try:
                while True:
                    frame_re = gif_org.copy().convert('RGBA').resize((220, 220), Image.Resampling.LANCZOS)
                    bg_image = Image.new("RGB", frame_re.size, self.C_FONDO_MAIN)
                    bg_image.paste(frame_re, (0, 0), frame_re)
                    self.frames_gif.append(ImageTk.PhotoImage(bg_image))
                    gif_org.seek(gif_org.tell() + 1)
            except EOFError:
                pass
                
            if self.frames_gif:
                self.img_ia = self.frames_gif[0]
                self.animando = True
                self.animar_ia()
            else:
                raise Exception("GIF sin frames")

        except Exception as e:
            print(f"Advertencia de imagen: {e}")
            print(f"Usando imagen generada (Fallback modo oscuro)")
            
            self.animando = False
            size = 180
            img = Image.new('RGB', (size, size), self.C_FONDO_MAIN)
            draw = ImageDraw.Draw(img)
            draw.ellipse([10, 10, size-10, size-10], outline=self.C_AZUL_IA, width=5)
            self.img_ia = ImageTk.PhotoImage(img)

    def animar_ia(self):
        """Loop de animación"""
        if self.animando and self.frames_gif:
            self.frame_index = (self.frame_index + 1) % len(self.frames_gif)
            next_frame = self.frames_gif[self.frame_index]
            
            if hasattr(self, 'label_central'):
                self.label_central.config(image=next_frame)
                self.label_central.image = next_frame
            
            self.root.after(self.gif_delay, self.animar_ia)
    
    def crear_interfaz(self):
        """Crea UI moderna en Modo Oscuro"""
        # Fuentes
        self.font_texto = tkfont.Font(family="Segoe UI", size=11)
        self.font_texto_app = tkfont.Font(family="Segoe UI", size=11)
        self.font_btn = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.font_palabra_gigante = tkfont.Font(family="Segoe UI", size=40, weight="bold")
        self.font_estado = tkfont.Font(family="Segoe UI", size=11)
        self.font_contador_parejas = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        
        # Espacio superior
        tk.Frame(self.root, bg=self.C_FONDO_MAIN, height=20).pack()
        
        # Label para contador de parejas (solo visible en dinámica final)
        self.label_contador_parejas = tk.Label(
            self.root,
            text="",
            font=self.font_contador_parejas,
            fg=self.C_AZUL_IA,
            bg=self.C_FONDO_MAIN
        )
        
        # Label central (imagen o palabra)
        self.label_central = tk.Label(
            self.root, 
            bg=self.C_FONDO_MAIN, 
            image=self.img_ia,
            compound="center",
            bd=0,
            highlightthickness=0
        )
        self.label_central.pack(pady=10)
        
        # Frame para preguntas (oculto inicialmente)
        self.frame_preguntas = tk.Frame(self.root, bg=self.C_FONDO_MAIN)
        
        # Conversación
        frame_conv = tk.Frame(self.root, bg=self.C_FONDO_MAIN)
        frame_conv.pack(pady=10, padx=50, fill="both", expand=True)
        
        self.texto_conv = tk.Text(
            frame_conv,
            font=self.font_texto,
            bg=self.C_FONDO_CAJA,
            fg=self.C_TEXTO_PRIM,
            wrap="word",
            height=10,
            relief="flat",
            bd=15,
            highlightthickness=0,
            insertbackground=self.C_AZUL_IA,
            selectbackground=self.C_AZUL_IA,
            selectforeground=self.C_FONDO_MAIN
        )
        self.texto_conv.pack(fill="both", expand=True)
        self.texto_conv.config(state="disabled")
        
        self.texto_conv.tag_config("app", foreground=self.C_AZUL_IA, font=self.font_texto_app)
        self.texto_conv.tag_config("user", foreground=self.C_TEXTO_PRIM, font=self.font_texto)
        
        # Frame palabra (oculto inicialmente)
        self.frame_palabra = tk.Frame(self.root, bg=self.C_FONDO_MAIN)
        
        self.label_info_palabra = tk.Label(
            self.frame_palabra,
            text="",
            font=tkfont.Font(family="Segoe UI", size=13),
            fg=self.C_TEXTO_SEC,
            bg=self.C_FONDO_MAIN
        )
        self.label_info_palabra.pack(pady=5)
        
        self.btn_ver_palabra = tk.Button(
            self.frame_palabra,
            text="Ver mi palabra",
            font=self.font_btn,
            bg=self.C_BOTON_BG,
            fg=self.C_AZUL_IA,
            activebackground=self.C_BOTON_ACTIVE,
            activeforeground=self.C_AZUL_IA,
            command=self.revelar_palabra_animada,
            relief="flat",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        self.btn_ver_palabra.pack(pady=5)
        
        # Controles inferiores
        frame_ctrl = tk.Frame(self.root, bg=self.C_FONDO_MAIN)
        frame_ctrl.pack(pady=20, fill="x")
        
        frame_botones = tk.Frame(frame_ctrl, bg=self.C_FONDO_MAIN)
        frame_botones.pack()
        
        self.btn_grabar = tk.Button(
            frame_botones,
            text="MANTÉN PARA HABLAR",
            font=self.font_btn,
            bg=self.C_BOTON_BG,
            fg=self.C_ROJO_BTN,
            activebackground=self.C_ROJO_BG_ACT,
            activeforeground=self.C_ROJO_BTN,
            relief="flat",
            bd=0,
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
            bg=self.C_BOTON_BG,
            fg=self.C_VERDE_BTN,
            activebackground=self.C_VERDE_BG_ACT,
            activeforeground=self.C_VERDE_BTN,
            command=self.marcar_listo,
            relief="flat",
            bd=0,
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
            fg=self.C_TEXTO_SEC,
            bg=self.C_FONDO_MAIN
        )
        self.label_estado.pack(pady=10)
    
    def saludo_inicial(self):
        """Saludo en hilo separado"""
        threading.Thread(target=self._saludo_thread, daemon=True).start()

    def _saludo_thread(self):
        msg = "Hola! Soy Jarvis, seré el mediador de este juego. Presiona el botón rojo cuando haya terminado de hablar para poder conversar, si el boton rojo no cambia el enunciado a 'ESCUCHANDO...' entonces presiona el botón de nuevo. Ahora necesito que una persona diga literalmente sólo la palabra 'Hola' para comenzar la interacción."
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
                self.btn_grabar.config(text="ESCUCHANDO...", bg=self.C_ROJO_BG_ACT, fg=self.C_ROJO_BTN)
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
            self.btn_grabar.config(text="MANTÉN PARA HABLAR", bg=self.C_BOTON_BG, fg=self.C_ROJO_BTN)
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
        if self.rec_vosk is None:
             self.root.after(0, lambda: self.agregar_mensaje_app("[ERROR: VOSK no cargado]"))
             self.procesando = False
             self.root.after(0, lambda: self.label_estado.config(text="Error VOSK"))
             return

        try:
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
                info = self.asistente.obtener_info_ui()
                nombre = info.get("jugador_actual") or info.get("mostrando_a") or "Usuario"
                self.root.after(0, lambda: self.agregar_mensaje_usuario(nombre, texto))
                self.root.after(0, lambda: self.label_estado.config(text="Pensando..."))
                
                respuesta = self.asistente.procesar_entrada(texto)
                respuesta_limpia = self.limpiar_comandos(respuesta)
                
                self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
                self.root.after(0, lambda: self.label_estado.config(text="Hablando..."))
                
                self.texto_a_voz(respuesta_limpia)
                self.root.after(0, self.actualizar_ui)
                
            else:
                self.root.after(0, lambda: self.label_estado.config(text="No entendí, intenta de nuevo"))
                
        except Exception as e:
            print(f"Error Processing: {e}")
            self.root.after(0, lambda: self.label_estado.config(text="Error interno"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.label_estado.config(text="Esperando..."))

    def limpiar_comandos(self, texto):
        return re.sub(r'\[.*?\]', '', texto).strip()
    
    def mostrar_preguntas(self, preguntas, preguntador, respondedor, pareja_actual, total_parejas):
        """Muestra el contador de parejas, las preguntas se dicen por voz"""
        for widget in self.frame_preguntas.winfo_children():
            widget.destroy()
        
        self.label_contador_parejas.config(text=f"Interacción {pareja_actual} de {total_parejas}")
        self.label_contador_parejas.pack(pady=5)
        
        mensaje_escuchar = tk.Label(
            self.frame_preguntas,
            text=f"{preguntador} a {respondedor}",
            font=tkfont.Font(family="Segoe UI", size=20, weight="bold"),
            fg=self.C_AZUL_IA,
            bg=self.C_FONDO_MAIN,
            pady=30
        )
        mensaje_escuchar.pack(pady=20)
        
        instruccion = tk.Label(
            self.frame_preguntas,
            text=f"{preguntador}, escoge una opción para preguntarle a {respondedor}.\nLuego resume su respuesta por el micrófono.",
            font=tkfont.Font(family="Segoe UI", size=13, slant="italic"),
            fg=self.C_TEXTO_SEC,
            bg=self.C_FONDO_MAIN,
            wraplength=600
        )
        instruccion.pack(pady=10)
        
        self.frame_preguntas.pack(pady=10, fill="x")
    
    def actualizar_ui(self):
        """Actualiza estado de botones"""
        info = self.asistente.obtener_info_ui()
        fase = info["fase"]
        
        self.frame_palabra.pack_forget()
        self.frame_preguntas.pack_forget()
        self.label_contador_parejas.pack_forget()
        self.btn_listo.config(state="disabled", cursor="arrow")
        self.btn_ver_palabra.config(state="normal")
        
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
        
        elif fase == "jugando":
            jugador = info.get("jugador_actual", "")
            self.label_estado.config(text=f"Turno de {jugador} - Da tu pista (Grabar)")
        
        elif fase == "decision_ronda":
            self.label_estado.config(text="Di: 'Otra ronda' o 'Votar'")
        
        elif fase == "votacion":
            votante = info.get("jugador_actual", "")
            if votante:
                self.label_estado.config(text=f"VOTACIÓN - {votante}, di el nombre")
            else:
                self.label_estado.config(text="VOTACIÓN - Di el nombre del impostor")
        
        elif fase == "pregunta_final":
            preguntador = info.get("preguntador")
            respondedor = info.get("respondedor")
            preguntas = info.get("preguntas", [])
            pareja_actual = info.get("pareja_actual", 0)
            total_parejas = info.get("total_parejas", 0)
            
            if preguntador and respondedor and preguntas:
                self.mostrar_preguntas(preguntas, preguntador, respondedor, pareja_actual, total_parejas)
                self.label_estado.config(text=f"Dinámica Final - {preguntador} pregunta a {respondedor}")
            else:
                self.label_estado.config(text="Preparando dinámica final...")
            
        elif fase == "resultado":
            self.label_estado.config(text="¡Juego terminado! Resultado mostrado")
        
        else:
            self.label_estado.config(text=f"Fase: {fase} - Esperando...")
    
    def revelar_palabra_animada(self):
        """Muestra la palabra reemplazando la imagen y pausando animación"""
        self.animando = False
        
        info = self.asistente.obtener_info_ui()
        es_impostor = info.get("es_impostor", False)
        palabra = info.get("palabra")
        
        if es_impostor:
            texto_mostrar = "¡ERES EL\nIMPOSTOR!"
            color_mostrar = self.C_ROJO_BTN
        elif palabra:
            texto_mostrar = palabra.upper()
            color_mostrar = self.C_VERDE_BTN
        else:
            texto_mostrar = "ERROR"
            color_mostrar = "orange"

        self.label_central.config(
            image="", 
            text=texto_mostrar, 
            font=self.font_palabra_gigante, 
            fg=color_mostrar,
            bg=self.C_FONDO_MAIN
        )
        
        self.btn_ver_palabra.config(state="disabled")
        self.label_estado.config(text="Memoriza tu palabra...")

        self.root.after(3000, self.restaurar_imagen_y_habilitar_listo)

    def restaurar_imagen_y_habilitar_listo(self):
        """Restaura la imagen, reanuda animación y habilita botón Listo"""
        self.label_central.config(text="", bg=self.C_FONDO_MAIN)
        
        if self.frames_gif:
            self.animando = True
            self.animar_ia()
        else:
            self.label_central.config(image=self.img_ia)
        
        self.btn_listo.config(state="normal", cursor="hand2")
        self.label_estado.config(text="Presiona LISTO cuando estés listo")

    def marcar_listo(self):
        """Acción del botón Listo"""
        self.btn_listo.config(state="disabled", cursor="arrow")
        self.label_estado.config(text="Procesando...")
        threading.Thread(target=self._marcar_listo_thread, daemon=True).start()

    def _marcar_listo_thread(self):
        """Procesa el comando Listo"""
        try:
            respuesta = self.asistente.procesar_entrada("listo")
            respuesta_limpia = self.limpiar_comandos(respuesta)
            
            self.root.after(0, lambda: self.agregar_mensaje_app(respuesta_limpia))
            self.texto_a_voz(respuesta_limpia)
            self.root.after(0, self.actualizar_ui)
            
        except Exception as e:
            print(f"Error listo: {e}")
            self.root.after(0, lambda: self.label_estado.config(text="Error al procesar"))
    
    async def generar_audio_edge(self, text, output_file):
        """Genera audio con voz ecuatoriana usando Edge-TTS"""
        voice = "es-EC-LuisNeural" 
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)

    def texto_a_voz(self, text):
        """TTS Edge-TTS (ejecutado en hilo separado)"""
        if self.rec_vosk is None:
             print(f"[AUDIO SIMULADO]: {text}")
             return

        try:
            self.root.after(0, lambda: self.label_estado.config(text="Jarvis hablando..."))
            
            archivo_audio = "temp_jarvis.mp3"
            
            if os.path.exists(archivo_audio):
                try:
                    os.remove(archivo_audio)
                except:
                    pass

            asyncio.run(self.generar_audio_edge(text, archivo_audio))
            
            if os.path.exists(archivo_audio):
                pygame.mixer.music.load(archivo_audio)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                pygame.mixer.music.unload()
            else:
                 print("Error: No se generó el archivo de audio.")
            
            self.root.after(0, lambda: self.label_estado.config(text="Listo para continuar"))
            
        except Exception as e:
            print(f"Error TTS: {e}")
            self.root.after(0, lambda: self.label_estado.config(text="Error en audio"))

def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
        
    root = tk.Tk()
    app = InterfazImpostor(root)
    root.mainloop()

if __name__ == "__main__":
    main()