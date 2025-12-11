import os
import json
import random
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()

api_key_google = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key_google)

class AsistenteImpostor:
    def __init__(self):
        self.jugadores = []
        self.generos = {}
        self.fase = "inicio"
      
        # Palabras ecuatorianas
        self.palabras_ecuador = [
            "encebollado", "ceviche", "hornado", "guatita", "cuy", "bolon", 
            "corvina", "empanada", "humita", "bollo", "fritada", "salchipapa",
            "Galapagos", "Quito", "Montanita", "Cuenca", "Guayaquil",
            "guambra", "fuego", "morocho", "sabido", "chuchaqui"
        ]
        
        self.palabra_secreta = None
        self.impostor_index = None
        self.jugadores_listos = set()
        self.ronda_actual = 0
        self.pistas_ronda = []
        self.votos_impostor = {}
        self.historial_completo = []
        self.turno_actual = 0
        self.orden_turnos = []
        
        # Rate limiting
        self.ultimo_request_ia = 0
        self.min_intervalo = 2.0
        
        self.inicializar_ia()
    
    def inicializar_ia(self):
        """IA con personalidad ajustada: Formal, Amable y Neutra"""
        prompt_sistema = """
Eres Jarvis, un asistente IA inteligente y muy amable encargado de moderar el juego "El Impostor".

PERSONALIDAD:
- Tono: Formal pero cálido, educado y servicial.
- Estilo: Neutro y profesional. Evita el exceso de jerga.
- Objetivo: Que el juego sea claro y organizado.

FLUJO DEL JUEGO:
1. SALUDO: Al inicio, saluda cordialmente y explica brevemente las reglas.
2. REGISTRO: Solo cuando digan "Comenzar", pide los nombres de los participantes.
3. JUEGO: Un jugador es el impostor (no conoce la palabra secreta).
4. VOTACIÓN: Al final, coordinas la votación para descubrir al impostor.

REGLAS DE INTERACCIÓN:
- Sé conciso (máximo 2 frases por turno).
- NO uses emojis.
"""
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=prompt_sistema
        )
        self.chat = self.model.start_chat(history=[])
    
    def detectar_genero(self, nombre):
        """Detección simple de género sin IA"""
        nombres_femeninos = ['ana', 'maria', 'carmen', 'lucia', 'sofia', 'elena', 'rosa', 'paula']
        nombres_masculinos = ['david', 'luis', 'diego', 'daniel', 'carlos', 'juan', 'pedro', 'jose']
        
        nombre_lower = nombre.lower()
        
        if nombre_lower in nombres_femeninos:
            return "mujer"
        elif nombre_lower in nombres_masculinos:
            return "hombre"
        elif nombre_lower.endswith(('a', 'ela', 'ita', 'ina')):
            return "mujer"
        else:
            return "hombre"
    
    def _esperar_rate_limit(self):
        """Espera si es necesario para respetar rate limit"""
        tiempo_transcurrido = time.time() - self.ultimo_request_ia
        if tiempo_transcurrido < self.min_intervalo:
            time.sleep(self.min_intervalo - tiempo_transcurrido)
        self.ultimo_request_ia = time.time()
    
    def procesar_entrada(self, texto_usuario):
        """IA interpreta y decide"""
        print(f"\n[PROCESANDO] Entrada: '{texto_usuario}' | Fase: {self.fase} | Turno: {self.turno_actual}")
        
        self.historial_completo.append(f"Usuario: {texto_usuario}")
        
        # SIEMPRE intentar fallback primero
        respuesta_fallback = self._respuesta_fallback(texto_usuario)
        
        # Si el fallback dio una respuesta válida, usarla
        if respuesta_fallback and "[" in respuesta_fallback:
            print(f"[FALLBACK] Respuesta: {respuesta_fallback}")
            self.historial_completo.append(f"Jarvis: {respuesta_fallback}")
            return respuesta_fallback
        
        # Solo usar IA para casos complejos
        contexto = self._construir_contexto()
        prompt = self._generar_prompt(texto_usuario, contexto)
        
        try:
            self._esperar_rate_limit()
            response = self.chat.send_message(prompt)
            respuesta_ia = response.text.strip()
        
            self._procesar_comandos_ia(respuesta_ia, texto_usuario)
            
            self.historial_completo.append(f"Jarvis: {respuesta_ia}")
            return respuesta_ia
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error IA: {error_msg}")
            
            if "429" in error_msg or "quota" in error_msg.lower():
                # Si hay error de cuota, usar fallback genérico
                fallback_generico = self._respuesta_fallback_generica(texto_usuario)
                return fallback_generico
            
            return "Disculpa, no he podido procesar eso. ¿Podrías repetirlo?"
    
    def _respuesta_fallback_generica(self, texto):
        """Fallback ultra simple cuando todo falla"""
        texto_lower = texto.lower()
        
        if self.fase == "mostrando_palabras":
            return "[JUGADOR_LISTO] Perfecto, siguiente jugador por favor."
        elif self.fase == "jugando":
            return "[GUARDAR_PISTA] Entendido. Siguiente jugador."
        elif self.fase == "votacion":
            for jugador in self.jugadores:
                if jugador.lower() in texto_lower:
                    return f"[VOTAR:{jugador}] Voto registrado."
        
        return "Continúa."
    
    def _respuesta_fallback(self, texto):
        """Respuestas básicas sin IA - MEJORADO"""
        texto_lower = texto.lower()
        
        print(f"[FALLBACK CHECK] Fase: {self.fase}, Texto: '{texto_lower}'")
        
        # === INICIO ===
        if self.fase == "inicio":
            if "comenzar" in texto_lower or "empezar" in texto_lower or "dale" in texto_lower:
                self.fase = "registro"
                print("[FALLBACK] -> REGISTRO")
                return "[INICIAR] Excelente. Por favor, indíqueme el nombre del primer participante."
            return None
        
        # === REGISTRO ===
        if self.fase == "registro":
            # Detectar fin de registro
            if any(palabra in texto_lower for palabra in ["último", "ultima", "listo", "ya estamos", "ya somos", "todos"]):
                if len(self.jugadores) >= 3:
                    self._iniciar_juego()
                    return f"[INICIAR_JUEGO] Perfecto, {len(self.jugadores)} jugadores registrados. Ahora cada uno verá su palabra. {self.jugadores[0]}, presiona 'Ver mi palabra'."
                else:
                    return f"Necesitamos al menos 3 jugadores. Tenemos {len(self.jugadores)}."
            
            # Extraer nombre
            palabras = texto.split()
            nombre = None
            palabras_ignorar = ["soy", "me", "llamo", "es", "el", "ella", "yo", "mi", "nombre", "y"]
            
            for p in palabras:
                p_clean = p.strip(".,;:!¿?").lower()
                if p_clean not in palabras_ignorar and len(p_clean) > 2 and p_clean.isalpha():
                    nombre = p.strip(".,;:!¿?").capitalize()
                    break
            
            if nombre:
                if nombre not in self.jugadores:
                    self.jugadores.append(nombre)
                    self.generos[nombre] = self.detectar_genero(nombre)
                    print(f"[FALLBACK] Registrado: {nombre}")
                    
                    if len(self.jugadores) >= 5:
                         self._iniciar_juego()
                         return f"[REGISTRAR:{nombre}] [INICIAR_JUEGO] Tenemos 5 jugadores. Iniciando juego. {self.jugadores[0]}, presiona 'Ver mi palabra'."
                    
                    return f"[REGISTRAR:{nombre}] Perfecto, {nombre} registrado. ¿Quién más va a jugar?"
                else:
                    return f"{nombre} ya está registrado. ¿Siguiente jugador?"
            
            return None
        
        # === MOSTRANDO PALABRAS === ¡CRÍTICO!
        if self.fase == "mostrando_palabras":
            # Detectar CUALQUIER confirmación
            confirmaciones = ["listo", "ok", "ya", "entendido", "siguiente", "vi", "ví", "bien", "dale", "continuar"]
            if any(palabra in texto_lower for palabra in confirmaciones):
                print(f"[FALLBACK] Confirmación detectada. Turno actual antes: {self.turno_actual}")
                
                if self.turno_actual < len(self.jugadores):
                    jugador_actual = self.jugadores[self.turno_actual]
                    self.jugadores_listos.add(jugador_actual)
                    self.turno_actual += 1
                    
                    print(f"[FALLBACK] Jugador {jugador_actual} listo. Turno ahora: {self.turno_actual}/{len(self.jugadores)}")
                    print(f"[FALLBACK] Listos: {len(self.jugadores_listos)}/{len(self.jugadores)}")
                    
                    # Verificar si todos terminaron
                    if self.turno_actual >= len(self.jugadores):
                        print("[FALLBACK] ¡TODOS LISTOS! Iniciando fase de juego")
                        self.fase = "jugando"
                        self.turno_actual = 0
                        self.orden_turnos = list(range(len(self.jugadores)))
                        random.shuffle(self.orden_turnos)
                        primer_jugador = self.jugadores[self.orden_turnos[0]]
                        return f"[JUGADOR_LISTO] Excelente. Todos han visto sus palabras. Comenzamos con las pistas. {primer_jugador}, da tu primera pista."
                    
                    # Hay más jugadores
                    siguiente = self.jugadores[self.turno_actual]
                    return f"[JUGADOR_LISTO] Perfecto. {siguiente}, ahora es tu turno. Presiona 'Ver mi palabra'."
                
            return None
        
        # === JUGANDO ===
        if self.fase == "jugando":
            if len(texto.strip()) > 2:
                if self.turno_actual < len(self.orden_turnos):
                    idx = self.orden_turnos[self.turno_actual]
                    self.pistas_ronda.append(f"{self.jugadores[idx]}: {texto}")
                    self.turno_actual += 1
                    
                    print(f"[FALLBACK] Pista guardada. Turno: {self.turno_actual}/{len(self.jugadores)}")
                    
                    if self.turno_actual >= len(self.jugadores):
                        self.fase = "decision_ronda"
                        return "[GUARDAR_PISTA] Interesante. Todos han dado sus pistas. ¿Desean otra ronda o votar?"
                    
                    siguiente_idx = self.orden_turnos[self.turno_actual]
                    siguiente = self.jugadores[siguiente_idx]
                    return f"[GUARDAR_PISTA] Bien. {siguiente}, tu turno para dar una pista."
            return None
        
        # === DECISIÓN RONDA ===
        if self.fase == "decision_ronda":
            if any(palabra in texto_lower for palabra in ["otra", "más", "si", "sí", "continuar", "nueva"]):
                self.ronda_actual += 1
                self.turno_actual = 0
                self.pistas_ronda = []
                self.fase = "jugando"
                random.shuffle(self.orden_turnos)
                primer_idx = self.orden_turnos[0]
                primer_jugador = self.jugadores[primer_idx]
                return f"[NUEVA_RONDA] De acuerdo, nueva ronda de pistas. {primer_jugador}, comienza."
            elif any(palabra in texto_lower for palabra in ["votar", "votación", "votacion", "ya", "no", "terminar"]):
                self.fase = "votacion"
                return f"[INICIAR_VOTACION] Perfecto, iniciemos la votación. {self.jugadores[0]}, ¿a quién votas como impostor?"
            return None
        
        # === VOTACIÓN ===
        if self.fase == "votacion":
            for jugador in self.jugadores:
                if jugador.lower() in texto_lower:
                    votante_idx = len(self.votos_impostor)
                    if votante_idx < len(self.jugadores):
                        votante = self.jugadores[votante_idx]
                        self.votos_impostor[votante] = jugador
                        
                        print(f"[FALLBACK] Voto: {votante} -> {jugador}")
                        
                        if len(self.votos_impostor) >= len(self.jugadores):
                            self._determinar_ganador()
                            impostor_real = self.jugadores[self.impostor_index]
                            return f"[VOTAR:{jugador}] Votación completa. El impostor era... ¡{impostor_real}!"
                        
                        siguiente_idx = len(self.votos_impostor)
                        siguiente_votante = self.jugadores[siguiente_idx]
                        return f"[VOTAR:{jugador}] Voto registrado. {siguiente_votante}, ¿a quién votas?"
            return None
        
        return None
    
    def _construir_contexto(self):
        """Contexto del juego actualizado"""
        ctx = f"FASE: {self.fase}\n"
        ctx += f"JUGADORES: {', '.join(self.jugadores)}\n"
        ctx += f"TURNO: {self.turno_actual}\n"
        return ctx
    
    def _generar_prompt(self, texto, contexto):
        """Prompt dinámico según fase"""
        return f"{contexto}\nUsuario: {texto}\nResponde brevemente y usa comandos [ACCION] cuando corresponda."
    
    def _procesar_comandos_ia(self, respuesta, texto):
        """Ejecuta comandos - SIMPLIFICADO porque ahora el fallback hace todo"""
        # Esta función ahora es principalmente para cuando la IA responde
        # pero el fallback ya maneja la mayoría de comandos
        
        if "[INICIAR]" in respuesta:
            self.fase = "registro"
        
        elif "[REGISTRAR:" in respuesta:
            try:
                nombre = respuesta.split("[REGISTRAR:")[1].split("]")[0].strip()
                nombre = nombre.replace(".", "").replace(",", "")
                
                if nombre and nombre not in self.jugadores:
                    self.jugadores.append(nombre)
                    self.generos[nombre] = self.detectar_genero(nombre)
            except Exception as e:
                print(f"Error registrando: {e}")
        
        elif "[INICIAR_JUEGO]" in respuesta:
            if len(self.jugadores) >= 3 and self.fase != "mostrando_palabras":
                self._iniciar_juego()
    
    def _iniciar_juego(self):
        """Configuración inicial del juego"""
        if self.fase == "mostrando_palabras":
            return  # Ya está iniciado
            
        self.fase = "mostrando_palabras"
        self.palabra_secreta = random.choice(self.palabras_ecuador)
        self.impostor_index = random.randint(0, len(self.jugadores) - 1)
        self.jugadores_listos = set()
        self.turno_actual = 0
        
        print(f"\n{'='*40}")
        print(f" INICIO DE PARTIDA")
        print(f" Jugadores: {', '.join(self.jugadores)}")
        print(f" Palabra secreta: {self.palabra_secreta}")
        print(f" Impostor: {self.jugadores[self.impostor_index]} (índice {self.impostor_index})")
        print(f"{'='*40}\n")
    
    def _determinar_ganador(self):
        """Cálculo de resultados"""
        self.fase = "resultado"
        
        conteo = {}
        for votado in self.votos_impostor.values():
            conteo[votado] = conteo.get(votado, 0) + 1
        
        if not conteo:
            return

        mas_votado = max(conteo, key=conteo.get)
        impostor = self.jugadores[self.impostor_index]
        
        resultado = "Ganan los CIUDADANOS" if mas_votado == impostor else "Gana el IMPOSTOR"
        print(f"\n[RESULTADO] {resultado}")
        print(f"Más votado: {mas_votado} ({conteo[mas_votado]} votos)")
        print(f"Impostor real: {impostor}\n")
        
        self.historial_completo.append(f"RESULTADO: {resultado}. Impostor era {impostor}.")
    
    def obtener_info_ui(self):
        """Retorna estado para la interfaz"""
        info = {
            "fase": self.fase,
            "jugadores": self.jugadores,
            "generos": self.generos,
            "turno": self.turno_actual,
            "jugador_actual": None,
            "mostrando_a": None,
            "es_impostor": False,
            "palabra": None,
            "listos": len(self.jugadores_listos),
            "total_jugadores": len(self.jugadores)
        }
        
        if self.fase == "mostrando_palabras" and self.turno_actual < len(self.jugadores):
            info["mostrando_a"] = self.jugadores[self.turno_actual]
            info["es_impostor"] = (self.turno_actual == self.impostor_index)
            info["palabra"] = None if info["es_impostor"] else self.palabra_secreta
            
            print(f"\n[INFO UI] ============================")
            print(f"  Mostrando a: {info['mostrando_a']} (turno {self.turno_actual})")
            print(f"  Es impostor: {info['es_impostor']} (impostor_index={self.impostor_index})")
            print(f"  Palabra: {info['palabra']}")
            print(f"  Listos: {info['listos']}/{info['total_jugadores']}")
            print(f"=============================\n")
        
        if self.fase == "jugando" and self.turno_actual < len(self.orden_turnos):
            idx = self.orden_turnos[self.turno_actual]
            info["jugador_actual"] = self.jugadores[idx]
            
        if self.fase == "votacion":
            votante_idx = len(self.votos_impostor)
            if votante_idx < len(self.jugadores):
                info["jugador_actual"] = self.jugadores[votante_idx]
                
        return info

if __name__ == "__main__":
    juego = AsistenteImpostor()
    print("--- CONSOLA DE PRUEBA ---")
    while True:
        txt = input("> ")
        print(juego.procesar_entrada(txt))