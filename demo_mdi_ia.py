import os
import json
import random
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key_google = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=api_key_google)

class AsistenteImpostor:
    def __init__(self):
        self.jugadores = []
        self.generos = {}
        self.fase = "inicio"
      
        # Palabras ecuatorianas (Se mantienen igual)
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
        
        self.inicializar_ia()
    
    def inicializar_ia(self):
        """IA con personalidad ajustada: Formal, Amable y Neutra"""
        prompt_sistema = """
Eres Jarvis, un asistente IA inteligente y muy amable encargado de moderar el juego "El Impostor".

PERSONALIDAD:
- Tono: Formal pero cálido, educado y servicial.
- Estilo: Neutro y profesional. Evita el exceso de jerga. Puedes usar un "Chévere" o "Listo" muy ocasionalmente para sonar natural, pero mantén la compostura.
- Objetivo: Que el juego sea claro y organizado.

FLUJO DEL JUEGO:
1. SALUDO: Al inicio, saluda cordialmente y explica brevemente las reglas. NO pidas nombres aún. Espera a que digan "Comenzar".
2. REGISTRO: Solo cuando digan "Comenzar", pide los nombres de los participantes uno por uno.
3. JUEGO: 
   - Un jugador es el impostor (no conoce la palabra secreta).
   - Los demás conocen la palabra.
   - Deben dar pistas sutiles.
4. VOTACIÓN: Al final, coordinas la votación para descubrir al impostor.

REGLAS DE INTERACCIÓN:
- Sé conciso (máximo 2 frases por turno, salvo explicaciones).
- NO uses emojis.
- Durante el registro, céntrate estrictamente en capturar los nombres, no te desvíes con charlas.

PALABRAS PARA ADIVINAR:
(Lista interna de palabras ecuatorianas)
"""
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=prompt_sistema
        )
        self.chat = self.model.start_chat(history=[])
    
    def detectar_genero(self, nombre):
        """IA detecta genero"""
        try:
            prompt = f"Nombre '{nombre}' es hombre o mujer en Ecuador? SOLO responde: 'hombre' o 'mujer'"
            resp = self.model.generate_content(prompt)
            genero = resp.text.strip().lower()
            return "hombre" if "hombre" in genero else "mujer"
        except Exception as e:
            print(f"   (Genero por defecto, error: {e})")
            if nombre.lower().endswith(('a', 'ela', 'ita')):
                return "mujer"
            return "hombre"
    
    def procesar_entrada(self, texto_usuario):
        """IA interpreta y decide"""
        self.historial_completo.append(f"Usuario: {texto_usuario}")
        
        contexto = self._construir_contexto()
        prompt = self._generar_prompt(texto_usuario, contexto)
        
        try:
            response = self.chat.send_message(prompt)
            respuesta_ia = response.text.strip()
        
            self._procesar_comandos_ia(respuesta_ia, texto_usuario)
            
            self.historial_completo.append(f"Jarvis: {respuesta_ia}")
            return respuesta_ia
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error IA: {error_msg}")
            
            if "429" in error_msg or "quota" in error_msg.lower():
                return self._respuesta_fallback(texto_usuario)
            
            return "Disculpa, no he podido procesar eso. ¿Podrías repetirlo?"
    
    def _respuesta_fallback(self, texto):
        """Respuestas básicas sin IA cuando hay rate limit"""
        texto_lower = texto.lower()
        
        # Inicio
        if self.fase == "inicio":
            if "comenzar" in texto_lower:
                self.fase = "registro"
                return "[INICIAR] Excelente. Por favor, indíqueme el nombre del primer participante."
            return "Hola, soy Jarvis. El juego consiste en descubrir al impostor entre ustedes. Diga 'Comenzar' cuando estén listos."
        
        # Registro
        if self.fase == "registro":
            palabras = texto_lower.split()
            nombre = None
            for p in palabras:
                if p not in ["soy", "me", "llamo", "es", "el", "ella"] and len(p) > 2:
                    nombre = p.capitalize()
                    break
            
            if nombre:
                if nombre not in self.jugadores:
                    self.jugadores.append(nombre)
                    self.generos[nombre] = self.detectar_genero(nombre)
                    
                    if len(self.jugadores) >= 5:
                         self._iniciar_juego()
                         return f"[REGISTRAR:{nombre}] [INICIAR_JUEGO] Registro completo. Iniciando juego."
                    
                    return f"[REGISTRAR:{nombre}] Anotado {nombre}. ¿Quién es el siguiente?"
                else:
                    return f"{nombre} ya está en la lista. ¿Siguiente nombre?"
        
        return "Entendido. Continuemos."

    def _construir_contexto(self):
        """Contexto del juego actualizado"""
        ctx = f"FASE ACTUAL: {self.fase}\n"
        ctx += f"JUGADORES ({len(self.jugadores)}): {', '.join(self.jugadores) if self.jugadores else 'Ninguno'}\n"
        
        if self.fase == "mostrando_palabras":
            ctx += f"TURNO DE VER: {self.jugadores[self.turno_actual] if self.turno_actual < len(self.jugadores) else 'Fin'}\n"
        
        if self.fase == "jugando" and self.turno_actual < len(self.orden_turnos):
            idx = self.orden_turnos[self.turno_actual]
            ctx += f"TURNO DE PISTA: {self.jugadores[idx]}\n"
            ctx += f"PISTAS RONDA: {len(self.pistas_ronda)}\n"
        
        return ctx
    
    def _generar_prompt(self, texto, contexto):
        """Prompt dinámico según fase"""
        
        # --- FASE 1: INICIO ---
        if self.fase == "inicio":
            return f"""{contexto}
Usuario: "{texto}"

TAREA:
1. Si el usuario saluda o pregunta qué es: Explica amablemente el juego (descubrir al impostor mediante pistas) y diles que digan "Comenzar" para iniciar.
2. Si el usuario dice "Comenzar", "Empezar" o "Dale": Responde con el comando [INICIAR] y pide el primer nombre formalmente.

RESPUESTA:
- Explicación: "Hola, bienvenidos. En este juego..."
- Inicio detectado: "[INICIAR] Perfecto. Por favor, indíqueme el nombre del primer jugador."
NO USES EMOJIS.
"""
        
        # --- FASE 2: REGISTRO ---
        elif self.fase == "registro":
            return f"""{contexto}
Usuario: "{texto}"

TAREA: Registrar nombres.
ESTADO: Tienes {len(self.jugadores)} jugadores registrados.

INSTRUCCIONES:
1. Extrae SOLO el nombre propio del texto. Ignora saludos o palabras extra.
2. Si detectas un nombre nuevo: Responde [REGISTRAR:Nombre] y pide amablemente el siguiente.
3. Si detectas "último", "listo" o "ya estamos" y hay al menos 3 jugadores: Responde [INICIAR_JUEGO].
4. Mantén la formalidad. Ejemplo: "Correcto, [Nombre] registrado. ¿Quién sigue?".

EJEMPLOS:
- "Me llamo Carlos" -> "[REGISTRAR:Carlos] Muy bien, Carlos registrado. ¿Siguiente?"
- "Ana" -> "[REGISTRAR:Ana] Ana anotada. ¿Quién más?"
- "Ya estamos todos" -> "[INICIAR_JUEGO] Excelente, comencemos."

NO USES EMOJIS.
"""
        
        # --- FASE 3: MOSTRANDO PALABRAS ---
        elif self.fase == "mostrando_palabras":
            jugador_actual = self.jugadores[self.turno_actual] if self.turno_actual < len(self.jugadores) else "?"
            return f"""{contexto}
Usuario: "{texto}"
Esperando confirmación de: {jugador_actual}

TAREA: Confirmar que el jugador vio su palabra secreta.
PALABRAS CLAVE: listo, ok, ya, entendido, siguiente.

RESPUESTA:
- Si confirma: [JUGADOR_LISTO] + "Gracias {jugador_actual}. Por favor llame al siguiente jugador."
- Si no es claro: Pregunta cortésmente si ya visualizó la palabra.
NO USES EMOJIS.
"""
        
        # --- FASE 4: JUGANDO ---
        elif self.fase == "jugando":
            if self.turno_actual >= len(self.orden_turnos):
                 return texto # Fallback
            
            idx = self.orden_turnos[self.turno_actual]
            jugador = self.jugadores[idx]
            
            return f"""{contexto}
TURNO DE: {jugador}
PALABRA SECRETA: {self.palabra_secreta}

Usuario ({jugador}): "{texto}"

TAREA: Analizar la pista dada.
1. ¿Es válida? (No dice la palabra prohibida).
2. Responde [GUARDAR_PISTA] y da un feedback MUY BREVE y amable (ej: "Interesante pista", "Muy bien").
3. Llama al siguiente jugador por su nombre.

RESPUESTA:
[GUARDAR_PISTA] + Feedback breve + Llamada al siguiente.
NO USES EMOJIS.
"""
        
        # --- OTRAS FASES ---
        elif self.fase == "decision_ronda":
            return f"""{contexto}
Usuario: "{texto}"
TAREA: ¿Quieren otra ronda de pistas o votar ya?
RESPUESTA:
- Otra ronda: [NUEVA_RONDA] "De acuerdo, hagamos otra ronda."
- Votar: [INICIAR_VOTACION] "Entendido, pasemos a la votación."
"""

        elif self.fase == "votacion":
            votante_idx = len(self.votos_impostor)
            votante_actual = self.jugadores[votante_idx] if votante_idx < len(self.jugadores) else "?"
            return f"""{contexto}
Votante actual: {votante_actual}
Usuario: "{texto}"

TAREA: Identificar a quién vota {votante_actual}.
RESPUESTA:
- Nombre detectado: [VOTAR:NombreVotado] "Voto registrado."
- Si no detectas nombre: Pregunta amablemente "¿A quién deseas votar?"
"""

        elif self.fase == "resultado":
            return f"""{contexto}
TAREA: Dar el resultado final de forma amena pero formal.
1. Revela quién era el impostor y si ganaron o perdieron.
2. Invita a jugar de nuevo.
NO hagas análisis psicológicos largos.
"""
        
        return texto
    
    def _procesar_comandos_ia(self, respuesta, texto):
        """Ejecuta comandos (Lógica de control)"""
        
        if "[INICIAR]" in respuesta:
            self.fase = "registro"
            print("   -> Fase: REGISTRO")
        
        elif "[REGISTRAR:" in respuesta:
            try:
                # Extracción limpia del nombre
                nombre = respuesta.split("[REGISTRAR:")[1].split("]")[0].strip()
                
                # Limpieza extra por si la IA alucina puntuación
                nombre = nombre.replace(".", "").replace(",", "")
                
                if nombre and nombre not in self.jugadores:
                    self.jugadores.append(nombre)
                    self.generos[nombre] = self.detectar_genero(nombre)
                    print(f"   [Sistema] Jugador registrado: {nombre}")
                    
                    if len(self.jugadores) >= 5:
                        print("   -> Máximo alcanzado, iniciando...")
                
            except Exception as e:
                print(f"   Error registrando: {e}")
        
        elif "[INICIAR_JUEGO]" in respuesta:
            if len(self.jugadores) >= 3: # Bajé el mínimo a 3 para pruebas
                self._iniciar_juego()
            else:
                print("   [Sistema] Faltan jugadores (mínimo 3).")
        
        elif "[JUGADOR_LISTO]" in respuesta:
            if self.turno_actual < len(self.jugadores):
                self.jugadores_listos.add(self.jugadores[self.turno_actual])
                self.turno_actual += 1
                
                if len(self.jugadores_listos) >= len(self.jugadores):
                    self.fase = "jugando"
                    self.turno_actual = 0
                    self.orden_turnos = list(range(len(self.jugadores)))
                    random.shuffle(self.orden_turnos)
                    print("   -> Fase: JUGANDO")

        elif "[GUARDAR_PISTA]" in respuesta:
            if self.turno_actual < len(self.orden_turnos):
                idx = self.orden_turnos[self.turno_actual]
                self.pistas_ronda.append(f"{self.jugadores[idx]}: {texto}")
                self.turno_actual += 1
                
                if self.turno_actual >= len(self.jugadores):
                    self.fase = "decision_ronda"
                    print("   -> Fase: DECISIÓN")

        elif "[NUEVA_RONDA]" in respuesta:
            self.ronda_actual += 1
            self.turno_actual = 0
            self.pistas_ronda = []
            self.fase = "jugando"
            random.shuffle(self.orden_turnos)
            print(f"   -> Nueva ronda #{self.ronda_actual + 1}")

        elif "[INICIAR_VOTACION]" in respuesta:
            self.fase = "votacion"
            self.turno_actual = 0
            print("   -> Fase: VOTACIÓN")

        elif "[VOTAR:" in respuesta:
            try:
                votado = respuesta.split("[VOTAR:")[1].split("]")[0].strip()
                # Búsqueda difusa simple para matchear nombre
                nombre_real = next((j for j in self.jugadores if j.lower() == votado.lower()), None)
                
                if nombre_real:
                    votante = self.jugadores[len(self.votos_impostor)]
                    self.votos_impostor[votante] = nombre_real
                    print(f"   [Sistema] Voto: {votante} -> {nombre_real}")
                    
                    if len(self.votos_impostor) >= len(self.jugadores):
                        self._determinar_ganador()
            except Exception as e:
                print(f"   Error voto: {e}")
    
    def _iniciar_juego(self):
        """Configuración inicial del juego"""
        self.fase = "mostrando_palabras"
        self.palabra_secreta = random.choice(self.palabras_ecuador)
        self.impostor_index = random.randint(0, len(self.jugadores) - 1)
        self.jugadores_listos = set()
        self.turno_actual = 0
        
        print(f"\n{'='*30}")
        print(f" INICIO DE PARTIDA")
        print(f" Palabra: {self.palabra_secreta}")
        print(f" Impostor: {self.jugadores[self.impostor_index]}")
        print(f"{'='*30}\n")
    
    def _determinar_ganador(self):
        """Cálculo de resultados"""
        self.fase = "resultado"
        
        conteo = {}
        for votado in self.votos_impostor.values():
            conteo[votado] = conteo.get(votado, 0) + 1
        
        if not conteo: return

        mas_votado = max(conteo, key=conteo.get)
        impostor = self.jugadores[self.impostor_index]
        
        resultado = "Ganan los CIUDADANOS" if mas_votado == impostor else "Gana el IMPOSTOR"
        self.historial_completo.append(f"RESULTADO: {resultado}. Impostor era {impostor}.")
    
    def obtener_info_ui(self):
        """Retorna estado para la interfaz"""
        # (Lógica idéntica a tu original para mantener compatibilidad UI)
        info = {
            "fase": self.fase,
            "jugadores": self.jugadores,
            "generos": self.generos,
            "turno": self.turno_actual,
            "jugador_actual": None,
            "mostrando_a": None,
            "es_impostor": False,
            "palabra": None,
            "listos": 0,
            "total_jugadores": len(self.jugadores)
        }
        
        if self.fase == "mostrando_palabras" and self.turno_actual < len(self.jugadores):
            info["mostrando_a"] = self.jugadores[self.turno_actual]
            info["es_impostor"] = (self.turno_actual == self.impostor_index)
            info["palabra"] = None if info["es_impostor"] else self.palabra_secreta
            info["listos"] = len(self.jugadores_listos)
        
        if self.fase == "jugando" and self.turno_actual < len(self.orden_turnos):
            idx = self.orden_turnos[self.turno_actual]
            info["jugador_actual"] = self.jugadores[idx]
            
        if self.fase == "votacion":
            votante_idx = len(self.votos_impostor)
            if votante_idx < len(self.jugadores):
                info["jugador_actual"] = self.jugadores[votante_idx]
                
        return info

# Bloque para probarlo en consola rápidamente
if __name__ == "__main__":
    juego = AsistenteImpostor()
    print("--- CONSOLA DE PRUEBA ---")
    while True:
        txt = input("> ")
        print(juego.procesar_entrada(txt))