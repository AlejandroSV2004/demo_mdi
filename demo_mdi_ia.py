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
            # Comida
            "pizza", "hamburguesa", "pasta", "sushi", "chocolate", "helado", "pan",
            "arroz", "pollo", "café", "taco", "papas fritas",

            # Bebidas
            "agua", "coca cola", "cerveza", "vino", "jugo", "té",

            # Películas
            "Titanic", "Avatar", "Harry Potter", "Star Wars", "El Rey León",
            "Jurassic Park", "Matrix", "Avengers",

            # Actores y actrices famosos
            "Leonardo DiCaprio", "Brad Pitt", "Tom Cruise", "Johnny Depp",
            "Scarlett Johansson", "Jennifer Lopez", "Will Smith",

            # Series
            "Friends", "Breaking Bad", "La Casa de Papel", "Los Simpson", "Rick and Morty", 

            # Países
            "Estados Unidos", "España", "México", "Brasil", "Francia",
            "Italia", "Japón", "China", "Argentina",

            # Ciudades y lugares famosos
            "Nueva York", "París", "Roma", "Tokio", "Londres",
            "Torre Eiffel", "Estatua de la Libertad", "Coliseo Romano",

            # Objetos cotidianos
            "celular", "computadora", "televisión", "reloj", "audífonos",
            "mochila", "libro",

            # Animales
            "perro", "gato", "león", "tigre", "elefante", "delfín",

            # Deportes
            "fútbol", "baloncesto", "tenis", "natación", "ciclismo",

            # Música
            "Michael Jackson", "Taylor Swift", "Bad Bunny", "Shakira",
            "Beyoncé",

            # Conceptos generales
            "dinero", "amor", "familia", "amigos", "vacaciones",
            "escuela", "trabajo"
        ]
        
        # Preguntas capciosas para la dinámica final
        self.preguntas_capciosas = [
            "¿Te gusta?",
            "¿Te lo pondrías?",
            "¿Lo llevarías a una fiesta?",
            "¿Te parece bonito?",
            "¿Lo usarías todos los días?",
            "¿Lo compartirías en familia?",
            "¿Lo recomendarías a un amigo?",
            "¿Pagarías mucho dinero por conocerlo?",
            "¿Lo tendrías en tu casa?",
            "¿Te da confianza?",
            "¿Lo considerarías elegante?",
            "¿Combina con tu personalidad?",
            "¿Lo extrañarías?",
            "¿Lo presentarías a tus padres?",
            "¿Te hace sentir importante?"
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
        
        # Variables para la dinámica final - MEJORADO
        self.parejas_dinamica = []  # Lista de tuplas (preguntador, respondedor)
        self.pareja_actual_index = 0
        self.preguntador = None
        self.respondedor = None
        self.pregunta_elegida = None
        self.preguntas_mostradas = []
        
        # Rate limiting
        self.ultimo_request_ia = 0
        self.min_intervalo = 2.0
        
        self.inicializar_ia()
    
    def inicializar_ia(self):
        """IA con personalidad ajustada: Formal, Amable y Neutra"""
        prompt_sistema = """
Eres Jarvis cómico, un asistente IA inteligente y muy amable encargado de moderar el juego "El Impostor".

PERSONALIDAD:
- Tono: Amiguero pero cálido, algo medio formal, educado y servicial.
- Estilo: Jovial pero evita el exceso de jerga y modismos.
- Objetivo: Que el juego sea claro y organizado pero con momentos de ligereza cómica.
- IMPORTANTE: Cada vez que un jugador dé una pista, haz un comentario sutil y ligeramente cómico sobre lo que dijo (máximo 1 frase corta).

FLUJO DEL JUEGO:
1. SALUDO: Al inicio, saluda cordialmente y explica las reglas, NO OLVIDAR DECIRLES QUE PARA INICAR EL JUEGO DEBEN DECIR EXPLICITAMENTE LA PALABRA "COMENZAR".
2. REGISTRO: Solo cuando digan "Comenzar", pide los nombres de los participantes.
3. REVELAR PALABRAS: Cuando sea el turno de cada jugador, SIEMPRE di: "Todos los demás, tápense los ojos o volteen la pantalla para que solo [NOMBRE] pueda ver su palabra".
4. JUEGO: Durante las pistas, emite comentarios sutiles y cómicos sobre lo que dicen.
5. VOTACIÓN: Coordinas la votación para descubrir al impostor.
6. DINÁMICA FINAL: Escoges MÚLTIPLES PAREJAS de participantes para que todos interactúen con preguntas capciosas. Cada pareja tiene su turno.

REGLAS DE INTERACCIÓN:
- Sé conciso (máximo 2 frases por turno, salvo en la dinámica final).
- NO uses emojis.
- NO uses **** ni símbolos innecesarios.
- SOLO responde en texto plano (No negritas, ni bulletpoints). 
- Usa humor sutil sin ofender.
"""
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=prompt_sistema
        )
        self.chat = self.model.start_chat(history=[])
    
    def generar_comentario_pista(self, jugador, pista):
        """Genera un comentario cómico sobre la pista usando IA"""
        try:
            prompt = f"""El jugador {jugador} acaba de dar esta pista sobre la palabra secreta: "{pista}"

Genera UN comentario corto (máximo 15 palabras), sutil y ligeramente cómico sobre lo que dijo. El comentario debe ser amigable y no revelar nada sobre la palabra. Solo responde con el comentario, sin explicaciones adicionales."""
            
            self._esperar_rate_limit()
            response = self.chat.send_message(prompt)
            comentario = response.text.strip()
            
            # Limitar longitud por seguridad
            if len(comentario.split()) > 20:
                comentario = ' '.join(comentario.split()[:20]) + "..."
            
            return comentario
        except Exception as e:
            print(f"[ERROR COMENTARIO IA] {e}")
            # Fallback: comentarios genéricos
            comentarios_fallback = [
                "Interesante perspectiva.",
                "Hmm, muy revelador.",
                "Esa pista dice mucho... o tal vez nada.",
                "Curioso enfoque.",
                "Veo que piensas diferente.",
                "Eso nos da mucho en qué pensar."
            ]
            return random.choice(comentarios_fallback)
    
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
    
    def _crear_parejas_dinamica(self):
        """Crea parejas para que todos participen al menos una vez"""
        jugadores_copia = self.jugadores.copy()
        random.shuffle(jugadores_copia)
        
        parejas = []
        n = len(jugadores_copia)
        
        if n % 2 == 0:
            # Número par: crear n/2 parejas sin repetir
            for i in range(0, n, 2):
                parejas.append((jugadores_copia[i], jugadores_copia[i + 1]))
        else:
            # Número impar: crear (n-1)/2 parejas, el último participa dos veces
            for i in range(0, n - 1, 2):
                parejas.append((jugadores_copia[i], jugadores_copia[i + 1]))
            # El último jugador participa en una pareja adicional
            parejas.append((jugadores_copia[-1], jugadores_copia[0]))
        
        print(f"\n[PAREJAS CREADAS] Total: {len(parejas)}")
        for i, (p1, p2) in enumerate(parejas, 1):
            print(f"  Pareja {i}: {p1} pregunta a {p2}")
        print()
        
        return parejas
    
    def procesar_entrada(self, texto_usuario):
        """IA interpreta y decide"""
        print(f"\n{'='*60}")
        print(f"[PROCESANDO] Entrada: '{texto_usuario}'")
        print(f"[PROCESANDO] Fase actual: {self.fase}")
        print(f"[PROCESANDO] Turno: {self.turno_actual}")
        print(f"{'='*60}")
        
        self.historial_completo.append(f"Usuario: {texto_usuario}")
        
        # SIEMPRE intentar fallback primero
        respuesta_fallback = self._respuesta_fallback(texto_usuario)
        
        # Si el fallback dio una respuesta válida (con comando), usarla
        if respuesta_fallback:
            print(f"[FALLBACK USADO] Respuesta: {respuesta_fallback[:100]}...")
            self.historial_completo.append(f"Jarvis: {respuesta_fallback}")
            return respuesta_fallback
        
        print("[PROCESANDO] Fallback no manejó, intentando con IA...")
        
        # Solo usar IA para casos complejos
        contexto = self._construir_contexto()
        prompt = self._generar_prompt(texto_usuario, contexto)
        
        try:
            self._esperar_rate_limit()
            response = self.chat.send_message(prompt)
            respuesta_ia = response.text.strip()
        
            self._procesar_comandos_ia(respuesta_ia, texto_usuario)
            
            self.historial_completo.append(f"Jarvis: {respuesta_ia}")
            print(f"[IA USADA] Respuesta: {respuesta_ia[:100]}...")
            return respuesta_ia
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR IA] {error_msg}")
            
            if "429" in error_msg or "quota" in error_msg.lower():
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
        elif self.fase == "pregunta_final":
            return "[RESPUESTA_PREGUNTA] Interesante respuesta. Siguiente pareja."
        
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
                    siguiente = self.jugadores[0]
                    return f"[INICIAR_JUEGO] Perfecto, {len(self.jugadores)} jugadores registrados. Ahora cada uno verá su palabra. Todos los demás, tápense los ojos o volteen la pantalla. {siguiente}, presiona 'Ver mi palabra' y cuando ya no salga en pantalla presiona el botón de Listo."
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
                         siguiente = self.jugadores[0]
                         return f"[REGISTRAR:{nombre}] [INICIAR_JUEGO] Tenemos 5 jugadores. Iniciando juego. Todos los demás, tápense los ojos o volteen la pantalla. {siguiente}, presiona 'Ver mi palabra' y cuando ya no salga en pantalla presiona el botón de Listo."
                    
                    return f"[REGISTRAR:{nombre}] Perfecto, {nombre} registrado. ¿Quién más va a jugar?"
                else:
                    return f"{nombre} ya está registrado. ¿Siguiente jugador?"
            
            return None
        
        # === MOSTRANDO PALABRAS ===
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
                    return f"[JUGADOR_LISTO] Perfecto. Ahora todos los demás vean a otro lado. {siguiente}, presiona 'Ver mi palabra' y luego el botón de Listo."
                
            return None
        
        # === JUGANDO ===
        if self.fase == "jugando":
            if len(texto.strip()) > 2:
                if self.turno_actual < len(self.orden_turnos):
                    idx = self.orden_turnos[self.turno_actual]
                    jugador = self.jugadores[idx]
                    self.pistas_ronda.append(f"{jugador}: {texto}")
                    
                    # Generar comentario cómico
                    comentario = self.generar_comentario_pista(jugador, texto)
                    
                    self.turno_actual += 1
                    
                    print(f"[FALLBACK] Pista guardada. Turno: {self.turno_actual}/{len(self.jugadores)}")
                    
                    if self.turno_actual >= len(self.jugadores):
                        self.fase = "decision_ronda"
                        return f"[GUARDAR_PISTA] {comentario} Todos han dado sus pistas. ¿Desean jugar otra ronda o ya votar?"
                    
                    siguiente_idx = self.orden_turnos[self.turno_actual]
                    siguiente = self.jugadores[siguiente_idx]
                    return f"[GUARDAR_PISTA] {comentario} {siguiente}, tu turno para dar una pista."
            return None
        
        # === DECISIÓN RONDA ===
        if self.fase == "decision_ronda":
            print(f"[FALLBACK] En decisión_ronda, analizando: '{texto_lower}'")
            
            if any(palabra in texto_lower for palabra in ["otra", "más", "mas", "si", "sí", "continuar", "nueva", "ronda"]):
                self.ronda_actual += 1
                self.turno_actual = 0
                self.pistas_ronda = []
                self.fase = "jugando"
                random.shuffle(self.orden_turnos)
                primer_idx = self.orden_turnos[0]
                primer_jugador = self.jugadores[primer_idx]
                print(f"[FALLBACK] -> NUEVA RONDA, primer jugador: {primer_jugador}")
                return f"[NUEVA_RONDA] De acuerdo, nueva ronda de pistas. {primer_jugador}, comienza."
            elif any(palabra in texto_lower for palabra in ["votar", "votación", "votacion", "ya", "no", "terminar", "basta"]):
                self.fase = "votacion"
                self.turno_actual = 0
                print(f"[FALLBACK] -> VOTACIÓN, primer votante: {self.jugadores[0]}")
                return f"[INICIAR_VOTACION] Perfecto, iniciemos la votación. {self.jugadores[0]}, ¿a quién votas como impostor?"
            
            # Si no detecta nada claro, asumir que quieren votar (para avanzar el juego)
            print(f"[FALLBACK] No detectó opción clara, pasando a VOTACIÓN por defecto")
            self.fase = "votacion"
            self.turno_actual = 0
            return f"[INICIAR_VOTACION] Entendido, pasemos a votar. {self.jugadores[0]}, ¿a quién votas?"
        
        # === VOTACIÓN ===
        if self.fase == "votacion":
            print(f"[FALLBACK] En votación, texto: '{texto_lower}'")
            print(f"[FALLBACK] Jugadores disponibles: {self.jugadores}")
            
            # Buscar nombre del votado
            nombre_encontrado = None
            for jugador in self.jugadores:
                if jugador.lower() in texto_lower:
                    nombre_encontrado = jugador
                    break
            
            if nombre_encontrado:
                votante_idx = len(self.votos_impostor)
                if votante_idx < len(self.jugadores):
                    votante = self.jugadores[votante_idx]
                    self.votos_impostor[votante] = nombre_encontrado
                    
                    print(f"[FALLBACK] Voto registrado: {votante} -> {nombre_encontrado}")
                    print(f"[FALLBACK] Votos actuales: {len(self.votos_impostor)}/{len(self.jugadores)}")
                    
                    if len(self.votos_impostor) >= len(self.jugadores):
                        print("[FALLBACK] ¡VOTACIÓN COMPLETA! Iniciando dinámica final...")
                        return self._iniciar_dinamica_final()
                    
                    siguiente_idx = len(self.votos_impostor)
                    siguiente_votante = self.jugadores[siguiente_idx]
                    return f"[VOTAR:{nombre_encontrado}] Voto registrado. {siguiente_votante}, ¿a quién votas?"
            
            print(f"[FALLBACK] No se detectó nombre válido en: '{texto_lower}'")
            return "No detecté un nombre válido. Por favor, di el nombre del jugador que crees que es el impostor."
        
        # === PREGUNTA FINAL - MODIFICADO PARA MÚLTIPLES PAREJAS ===
        if self.fase == "pregunta_final":
            # Cualquier respuesta avanza a la siguiente pareja o al resultado
            confirmaciones = ["ok", "ya", "listo", "entendido", "bien", "siguiente"]
            if any(palabra in texto_lower for palabra in confirmaciones) or len(texto.strip()) > 3:
                self.pareja_actual_index += 1
                
                # Verificar si hay más parejas
                if self.pareja_actual_index < len(self.parejas_dinamica):
                    return self._mostrar_siguiente_pareja()
                else:
                    # Todas las parejas completadas, mostrar resultado final
                    return self._mostrar_resultado_final()
            return None
        
        return None
    
    def _iniciar_dinamica_final(self):
        """Inicia la dinámica de pregunta capciosa con múltiples parejas"""
        self.fase = "pregunta_final"
        
        # Crear parejas para que todos participen
        self.parejas_dinamica = self._crear_parejas_dinamica()
        self.pareja_actual_index = 0
        
        # Mostrar primera pareja
        return self._mostrar_siguiente_pareja()
    
    def _mostrar_siguiente_pareja(self):
        """Muestra la siguiente pareja de pregunta-respuesta"""
        if self.pareja_actual_index >= len(self.parejas_dinamica):
            return self._mostrar_resultado_final()
        
        # Obtener pareja actual
        self.preguntador, self.respondedor = self.parejas_dinamica[self.pareja_actual_index]
        
        # Seleccionar 3 preguntas aleatorias
        self.preguntas_mostradas = random.sample(
            self.preguntas_capciosas, 
            min(3, len(self.preguntas_capciosas))
        )
        
        # Formatear preguntas para mostrar
        preguntas_texto = "\n".join([f"{i+1}. {p}" for i, p in enumerate(self.preguntas_mostradas)])
        
        pareja_num = self.pareja_actual_index + 1
        total_parejas = len(self.parejas_dinamica)
        
        mensaje = f"[DINAMICA_FINAL] Perfecto, ahora {self.preguntador} vas a hacerle una pregunta a {self.respondedor}. Escoge una pregunta de las siguientes opciones:\n\n{preguntas_texto}\n\n y luego pregúntasela directamente a {self.respondedor}l. Una vez que haya respondido, dime por el micrófono un resumen de lo que dijo."
        
        print(f"[DINAMICA] Pareja {pareja_num}/{total_parejas}: {self.preguntador} -> {self.respondedor}")
        
        return mensaje
    
    def _mostrar_resultado_final(self):
        """Muestra el resultado final después de todas las interacciones"""
        impostor_real = self.jugadores[self.impostor_index]
        
        # Contar votos
        conteo = {}
        for votado in self.votos_impostor.values():
            conteo[votado] = conteo.get(votado, 0) + 1
        mas_votado = max(conteo, key=conteo.get)
        votos_mas_votado = conteo[mas_votado]
        
        self._determinar_ganador()

        if mas_votado == impostor_real:
            return f"[RESPUESTA_PREGUNTA] Excelente. Los votos están sobre la mesa y el señalado es {mas_votado}, con un total de {votos_mas_votado} votos; sin embargo, la verdad emerge desde las sombras: el impostor real, quien sonrió todo el tiempo, era {impostor_real}. La palabra secreta era '{self.palabra_secreta}'. Resultado final: el grupo cae en la trampa, el impostor se sale con la suya y la victoria es reclamada sin ser vista venir. Excelente actuación {impostor_real}. Gracias por jugar, fin de la partida."

        else:
            return f"[RESPUESTA_PREGUNTA] Excelente. Los votos están sobre la mesa y el señalado es {mas_votado}, con un total de {votos_mas_votado} votos. Sin embargo, el impostor real, ese que sonrió todo el tiempo, era {impostor_real}. La palabra secreta era '{self.palabra_secreta}'. Resultado final: el grupo cae en la trampa, el impostor se sale con la suya y alguien acaba de ganar sin que nadie lo viera venir. Excelente actuación {impostor_real}, el público está en shock. Gracias por jugar, episodio terminado."
       
        # if mas_votado == impostor_real:
        #     return f"[RESPUESTA_PREGUNTA] Excelente. Ahora sí, los resultados finales: ¡{mas_votado} recibió {votos_mas_votado} votos y SÍ era el impostor! La palabra era '{self.palabra_secreta}'. ¡GANAN LOS INOCENTES! Bien jugado chicos, gracias por jugar, eso es todo."
        # else:
        #     return f"[RESPUESTA_PREGUNTA] Muy bien. Resultados finales: {mas_votado} recibió {votos_mas_votado} votos, pero el impostor real era {impostor_real}. La palabra era '{self.palabra_secreta}'. ¡GANA EL IMPOSTOR! Bien jugado {impostor_real}, gracias por jugar, eso es todo."
    
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

        indices_disponibles = list(range(len(self.jugadores)))
        random.shuffle(indices_disponibles)
        self.impostor_index = indices_disponibles[0]  # Mezclar bien los índices

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
            "total_jugadores": len(self.jugadores),
            "preguntador": self.preguntador,
            "respondedor": self.respondedor,
            "preguntas": self.preguntas_mostradas,
            "pareja_actual": self.pareja_actual_index + 1 if self.fase == "pregunta_final" else 0,
            "total_parejas": len(self.parejas_dinamica) if self.fase == "pregunta_final" else 0
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