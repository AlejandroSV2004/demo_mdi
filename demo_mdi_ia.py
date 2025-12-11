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
        
        self.inicializar_ia()
    
    def inicializar_ia(self):
        """IA con personalidad divertida"""
        prompt_sistema = """
Eres Jarvis, asistente IA carismático facilitando "El Impostor" con universitarios ecuatorianos.

PERSONALIDAD:
- Amigable, juvenil, entusiasta
- Humor sutil ecuatoriano (maneja un vocabulario coloquial sin rayar en lo popular)
- Informal pero respetuoso
- Frases: "Que loco!", "Tremendo!"

JUEGO:
- Un jugador es impostor (no conoce palabra)
- Otros tienen la palabra ecuatoriana que es una de las palabras a adivinar (tu no tienes que indicar la palabra, ellos la veran por la interfaz)
- Cada ronda: todos dan pista SIN decir palabra
- Impostor finge conocerla
- Al final: votan al impostor y revelan palabra secreta

ROL:
- Guia con entusiasmo, tienes que actuar como mediador
- Cuando indican estar listos, pedir los nombres y comenzar con las rondas (debes pedirle a cada participante por su nombre su pista - en cada interaccion debe ser un participante)
- Detecta si revelan palabra o son sospechosos
- Crea tension dramatica (al finalizar la ronda consulta si continuan una mas o ya quieren votar)
- Interpreta pistas inteligentemente
- Analisis final: muy breve, divertido, NO psicologo

REGLAS:
- Maximo 2-3 oraciones (excepto analisis)
- Menciona nombres
- Si incoherente: pide aclaracion natural
- Detecta nombres de jugadores en respuestas
- NO uses emojis en ninguna respuesta

PALABRAS PARA ADIVINAR:
- "encebollado", "ceviche", "hornado", "guatita", "cuy", "bolon", "corvina", "empanada", "humita", "bollo", "fritada", "salchipapa", "Galapagos", "Quito", "Montanita", "Cuenca", "Guayaquil", "guambra", "fuego", "morocho", "sabido", "chuchaqui"
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
            
            return "Perdon, no te escuche bien. Puedes repetir?"
    
    def _respuesta_fallback(self, texto):
        """Respuestas basicas sin IA cuando hay rate limit"""
        texto_lower = texto.lower()
        
        # Inicio
        if self.fase == "inicio":
            if any(p in texto_lower for p in ["hola", "comenzar", "empezar", "jugar", "listo"]):
                self.fase = "registro"
                return "[INICIAR] Perfecto! Vamos a jugar. Primer jugador, di tu nombre."
            return "Dime 'comenzar' cuando esten listos."
        
        # Registro
        if self.fase == "registro":
            palabras = texto_lower.split()
            nombre = None
            for p in palabras:
                if p not in ["soy", "me", "llamo", "es"] and len(p) > 2:
                    nombre = p.capitalize()
                    break
            
            if nombre and nombre not in self.jugadores:
                es_ultimo = any(p in texto_lower for p in ["ultimo", "ultima", "final"])
                if es_ultimo and len(self.jugadores) >= 3:
                    self.jugadores.append(nombre)
                    self.generos[nombre] = self.detectar_genero(nombre)
                    self._iniciar_juego()
                    return f"[REGISTRAR:{nombre}] [INICIAR_JUEGO] Listos! Comenzamos con {len(self.jugadores)} jugadores."
                
                self.jugadores.append(nombre)
                self.generos[nombre] = self.detectar_genero(nombre)
                n_actual = len(self.jugadores)
                siguiente = "Siguiente jugador" if n_actual < 5 else "Ya son 5, di 'ultimo' para empezar"
                return f"[REGISTRAR:{nombre}] Registrado {nombre} ({n_actual}/5). {siguiente}."
            elif nombre in self.jugadores:
                return f"Ya estas registrado {nombre}. Siguiente jugador."
        
        # Mostrando palabras
        if self.fase == "mostrando_palabras":
            if any(p in texto_lower for p in ["listo", "ok", "ya", "vi"]):
                siguiente = self.turno_actual + 1
                if siguiente < len(self.jugadores):
                    return f"[JUGADOR_LISTO] Perfecto. {self.jugadores[siguiente]}, tu turno."
                return "[JUGADOR_LISTO] Todos listos! Empecemos con las pistas."
        
        # Jugando
        if self.fase == "jugando":
            siguiente = self.turno_actual + 1
            if siguiente < len(self.jugadores):
                idx = self.orden_turnos[siguiente]
                return f"[GUARDAR_PISTA] Pista registrada. {self.jugadores[idx]}, tu turno."
            return "[GUARDAR_PISTA] Ronda completada. Otra ronda o votar?"
        
        # Decision
        if self.fase == "decision_ronda":
            if any(p in texto_lower for p in ["otra", "si", "continuar"]):
                return "[NUEVA_RONDA] Dale! Nueva ronda."
            return "[INICIAR_VOTACION] A votar entonces."
        
        # Votacion
        if self.fase == "votacion":
            for jugador in self.jugadores:
                if jugador.lower() in texto_lower:
                    siguiente = len(self.votos_impostor) + 1
                    if siguiente < len(self.jugadores):
                        return f"[VOTAR:{jugador}] Voto registrado. {self.jugadores[siguiente]}, tu?"
                    return f"[VOTAR:{jugador}] Ultimo voto. Veamos los resultados..."
        
        return "Entendido."
    
    def _construir_contexto(self):
        """Contexto del juego - MEJORADO para recordar jugadores"""
        ctx = f"FASE ACTUAL: {self.fase}\n"
        ctx += f"JUGADORES REGISTRADOS ({len(self.jugadores)}): {', '.join(self.jugadores) if self.jugadores else 'Ninguno'}\n"
        
        if self.jugadores:
            ctx += "LISTA COMPLETA DE JUGADORES:\n"
            for i, j in enumerate(self.jugadores, 1):
                ctx += f"  {i}. {j}\n"
        
        if self.fase == "mostrando_palabras":
            ctx += f"LISTOS: {len(self.jugadores_listos)}/{len(self.jugadores)}\n"
            ctx += f"TURNO ACTUAL: {self.turno_actual + 1}/{len(self.jugadores)}\n"
            if self.turno_actual < len(self.jugadores):
                ctx += f"MOSTRANDO PALABRA A: {self.jugadores[self.turno_actual]}\n"
        
        if self.fase == "jugando" and self.turno_actual < len(self.orden_turnos):
            idx = self.orden_turnos[self.turno_actual]
            ctx += f"TURNO DE: {self.jugadores[idx]} ({self.turno_actual + 1}/{len(self.jugadores)})\n"
            ctx += f"RONDA: {self.ronda_actual + 1}\n"
            ctx += f"PISTAS DADAS: {len(self.pistas_ronda)}/{len(self.jugadores)}\n"
        
        if self.fase == "votacion":
            ctx += f"VOTOS RECIBIDOS: {len(self.votos_impostor)}/{len(self.jugadores)}\n"
            votante_actual_idx = len(self.votos_impostor)
            if votante_actual_idx < len(self.jugadores):
                ctx += f"TURNO DE VOTAR: {self.jugadores[votante_actual_idx]}\n"
        
        return ctx
    
    def _generar_prompt(self, texto, contexto):
        """Prompt segun fase - MEJORADO"""
        
        if self.fase == "inicio":
            return f"""{contexto}
Usuario: "{texto}"

TAREA: Quiere iniciar?
PALABRAS CLAVE: hola, comenzar, empezar, jugar, listo, vamos, dale

RESPUESTA:
- Si detectas inicio: [INICIAR] + bienvenida entusiasta explicando el juego
- Si no: pregunta amablemente si quiere jugar
NO USES EMOJIS
"""
        
        elif self.fase == "registro":
            return f"""{contexto}
Usuario: "{texto}"

TAREA CRITICA: Extraer SOLO el nombre nuevo que NO este en la lista

JUGADORES YA REGISTRADOS: {', '.join(self.jugadores) if self.jugadores else 'Ninguno'}
TOTAL ACTUAL: {len(self.jugadores)}

REGLAS ESTRICTAS:
1. VERIFICAR que el nombre NO este en: {self.jugadores}
2. SI YA ESTA REGISTRADO: Decir "Ya estas registrado [Nombre]" y pedir el SIGUIENTE jugador
3. IGNORAR: soy, me, llamo, mi, nombre, es, hola, ok, si, bueno
4. DETECTAR fin: "ultimo", "ultima", "final"
5. VALIDAR: Debe ser nombre real, no "hola", "ok", "bien"
6. MINIMO 4 jugadores para iniciar

EJEMPLOS:
- "Maria" (nueva) -> [REGISTRAR:Maria] + "Bienvenida Maria! (1/5)"
- "Soy Juan" (nuevo) -> [REGISTRAR:Juan] + "Registrado Juan (2/5)"
- "Maria" (ya registrado) -> "Maria ya esta registrada. Siguiente jugador."
- "Pedro ultimo" (con 4+ jugadores) -> [REGISTRAR:Pedro] [INICIAR_JUEGO] + "Empecemos!"

RESPUESTA:
- Nombre NUEVO valido: [REGISTRAR:NombreCapitalizado] + confirmacion con contador
- Nombre DUPLICADO: "Ya estas registrado/a [Nombre]. Siguiente jugador"
- Detecto "ultimo" + 4+ jugadores: [INICIAR_JUEGO]
- Automatico con 5: [INICIAR_JUEGO]
NO USES EMOJIS
"""
        
        elif self.fase == "mostrando_palabras":
            jugador_actual = self.jugadores[self.turno_actual] if self.turno_actual < len(self.jugadores) else "?"
            return f"""{contexto}
JUGADOR VIENDO PALABRA: {jugador_actual}
Usuario: "{texto}"

TAREA: Confirmo que vio su palabra?
PALABRAS: listo, ok, ya, entendido, vi, perfecto

RESPUESTA:
- Si confirmo: [JUGADOR_LISTO] + mensaje breve positivo + indicar siguiente jugador
- Si no: pregunta amablemente si ya vio
NO USES EMOJIS
"""
        
        elif self.fase == "jugando":
            if self.turno_actual >= len(self.orden_turnos):
                return texto
            
            idx = self.orden_turnos[self.turno_actual]
            jugador = self.jugadores[idx]
            
            return f"""{contexto}
TURNO ACTUAL: {jugador}
PALABRA SECRETA: {self.palabra_secreta}
IMPOSTOR: {self.jugadores[self.impostor_index]}
PISTAS PREVIAS EN ESTA RONDA:
{chr(10).join([f"  - {p}" for p in self.pistas_ronda]) if self.pistas_ronda else "  (ninguna aun)"}

Usuario ({jugador}): "{texto}"

ANALIZA CUIDADOSAMENTE:
1. Dijo exactamente "{self.palabra_secreta}"? -> ALERTA GRAVE
2. Pista coherente con palabra? (si es impostor, no puede saberlo)
3. Muy vago/generico? -> Sospechoso
4. Contradice pistas previas? -> Impostor posible
5. Es {jugador} el impostor? -> Evalua si fingio bien

RESPUESTA:
[GUARDAR_PISTA] + analisis breve pero perspicaz
- Si revelo palabra: Menciona que la dijo!
- Si sospechoso: comentario intrigante
- Si es buena: celebralo
- Indica quien sigue
NO USES EMOJIS
"""
        
        elif self.fase == "decision_ronda":
            return f"""{contexto}
Usuario: "{texto}"

TAREA: Quiere otra ronda o votar?

RESPUESTA:
- Si detectas "otra", "continuar", "si", "seguir": [NUEVA_RONDA] + mensaje emocionado
- Si detectas "votar", "ya", "no", "basta": [INICIAR_VOTACION] + mensaje de tension
- Si no claro: pregunta directamente
NO USES EMOJIS
"""
        
        elif self.fase == "votacion":
            votante_actual_idx = len(self.votos_impostor)
            votante_actual = self.jugadores[votante_actual_idx] if votante_actual_idx < len(self.jugadores) else "?"
            
            return f"""{contexto}
TODOS LOS JUGADORES: {', '.join(self.jugadores)}
VOTOS ACTUALES: {len(self.votos_impostor)}/{len(self.jugadores)}
VOTANDO AHORA: {votante_actual}

Usuario: "{texto}"

TAREA: Detectar nombre de jugador votado
BUSCAR nombres exactos en: {self.jugadores}

RESPUESTA:
- Si detecta nombre de la lista: [VOTAR:NombreExacto] + confirma con intriga
- Si no: pregunta especificamente a quien vota
NO USES EMOJIS
"""
        
        elif self.fase == "resultado":
            return f"""{contexto}

HISTORIAL COMPLETO:
{chr(10).join(self.historial_completo[-30:])}

TAREA: Analisis final DIVERTIDO

INCLUIR:
1. Quien era impostor y resultado (gano/perdio)
2. Mejor jugada o pista mas sospechosa
3. Comentario chistoso sobre algo que paso
4. Animo para jugar de nuevo

ESTILO:
- Maximo 5-6 oraciones
- Tono: amigos conversando despues del juego
- NO como psicologo ni formal
- Humor sutil ecuatoriano si cabe
- Inicia: "Bueno bueno, que partidazo!" o similar

EVITAR:
- Analisis psicologico profundo
- Lenguaje corporativo
- Ser aburrido
NO USES EMOJIS
"""
        
        return texto
    
    def _procesar_comandos_ia(self, respuesta, texto):
        """Ejecuta comandos - MEJORADO"""
        
        if "[INICIAR]" in respuesta:
            self.fase = "registro"
            print("   -> Fase: REGISTRO")
        
        elif "[REGISTRAR:" in respuesta:
            try:
                nombre = respuesta.split("[REGISTRAR:")[1].split("]")[0].strip()
                print(f"   [DEBUG] Intentando registrar: '{nombre}'")
                print(f"   [DEBUG] Jugadores actuales: {self.jugadores}")
                
                # Validacion mas estricta
                if not nombre or len(nombre) <= 1:
                    print(f"   X Nombre invalido: muy corto")
                    return
                
                if nombre in self.jugadores:
                    print(f"   X Nombre duplicado: {nombre} ya existe")
                    return
                
                # Registrar jugador
                self.jugadores.append(nombre)
                self.generos[nombre] = self.detectar_genero(nombre)
                print(f"   OK Registrado: {nombre} (genero: {self.generos[nombre]})")
                print(f"   Total jugadores: {len(self.jugadores)}/5")
                
                # Auto-iniciar con 5 jugadores
                if len(self.jugadores) >= 5:
                    print(f"   -> 5 jugadores alcanzados, auto-iniciando...")
                    
            except Exception as e:
                print(f"   Error registrando: {e}")
        
        elif "[INICIAR_JUEGO]" in respuesta:
            if len(self.jugadores) >= 4:
                self._iniciar_juego()
            else:
                print(f"   X No se puede iniciar: solo {len(self.jugadores)} jugadores (minimo 4)")
        
        elif "[JUGADOR_LISTO]" in respuesta:
            if self.turno_actual < len(self.jugadores):
                jugador = self.jugadores[self.turno_actual]
                self.jugadores_listos.add(jugador)
                print(f"   OK {jugador} listo ({len(self.jugadores_listos)}/{len(self.jugadores)})")
                self.turno_actual += 1
                
                if len(self.jugadores_listos) >= len(self.jugadores):
                    self.fase = "jugando"
                    self.turno_actual = 0
                    self.orden_turnos = list(range(len(self.jugadores)))
                    random.shuffle(self.orden_turnos)
                    print("   -> Fase: JUGANDO")
                    print(f"   Orden de turnos: {[self.jugadores[i] for i in self.orden_turnos]}")
        
        elif "[GUARDAR_PISTA]" in respuesta:
            if self.turno_actual < len(self.orden_turnos):
                idx = self.orden_turnos[self.turno_actual]
                jugador = self.jugadores[idx]
                self.pistas_ronda.append(f"{jugador}: {texto}")
                print(f"   OK Pista de {jugador} guardada")
                self.turno_actual += 1
                
                if self.turno_actual >= len(self.jugadores):
                    self.fase = "decision_ronda"
                    print("   -> Fase: DECISION")
                else:
                    siguiente_idx = self.orden_turnos[self.turno_actual]
                    print(f"   Siguiente: {self.jugadores[siguiente_idx]}")
        
        elif "[NUEVA_RONDA]" in respuesta:
            self.ronda_actual += 1
            self.turno_actual = 0
            self.pistas_ronda = []
            self.fase = "jugando"
            random.shuffle(self.orden_turnos)
            print(f"   -> Nueva ronda #{self.ronda_actual + 1}")
            print(f"   Nuevo orden: {[self.jugadores[i] for i in self.orden_turnos]}")
        
        elif "[INICIAR_VOTACION]" in respuesta:
            self.fase = "votacion"
            self.turno_actual = 0
            print("   -> Fase: VOTACION")
        
        elif "[VOTAR:" in respuesta:
            try:
                votado = respuesta.split("[VOTAR:")[1].split("]")[0].strip()
                if votado in self.jugadores:
                    votante_idx = len(self.votos_impostor)
                    if votante_idx < len(self.jugadores):
                        votante = self.jugadores[votante_idx]
                        self.votos_impostor[votante] = votado
                        print(f"   OK {votante} voto por {votado}")
                        
                        if len(self.votos_impostor) >= len(self.jugadores):
                            self._determinar_ganador()
                else:
                    print(f"   X Voto invalido: {votado} no es un jugador")
            except Exception as e:
                print(f"   Error votando: {e}")
    
    def _iniciar_juego(self):
        """Inicia juego"""
        self.fase = "mostrando_palabras"
        self.palabra_secreta = random.choice(self.palabras_ecuador)
        self.impostor_index = random.randint(0, len(self.jugadores) - 1)
        self.jugadores_listos = set()
        self.turno_actual = 0
        
        print(f"\n{'='*60}")
        print(f"   JUEGO INICIADO")
        print(f"   Palabra: {self.palabra_secreta}")
        print(f"   Impostor: {self.jugadores[self.impostor_index]}")
        print(f"   Jugadores: {', '.join(self.jugadores)}")
        print(f"   Primer turno: {self.jugadores[0]}")
        print(f"{'='*60}\n")
    
    def _determinar_ganador(self):
        """Determina ganador"""
        self.fase = "resultado"
        
        # Contar votos
        conteo = {}
        for votado in self.votos_impostor.values():
            conteo[votado] = conteo.get(votado, 0) + 1
        
        mas_votado = max(conteo, key=conteo.get)
        impostor = self.jugadores[self.impostor_index]
        
        print(f"\n{'='*60}")
        print(f"   RESULTADOS:")
        for jugador, votos in conteo.items():
            print(f"      {jugador}: {votos} voto(s)")
        
        if mas_votado == impostor:
            resultado = f"Los JUGADORES GANARON! Descubrieron que {impostor} era el impostor."
        else:
            resultado = f"El IMPOSTOR GANO! Era {impostor}, pero votaron a {mas_votado}."
        
        print(f"\n   {resultado}")
        print(f"{'='*60}\n")
        
        self.historial_completo.append(resultado)
    
    def obtener_info_ui(self):
        """Info para UI"""
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
        
        if self.fase == "mostrando_palabras":
            if self.turno_actual < len(self.jugadores):
                info["mostrando_a"] = self.jugadores[self.turno_actual]
                info["es_impostor"] = (self.turno_actual == self.impostor_index)
                info["palabra"] = None if info["es_impostor"] else self.palabra_secreta
                info["listos"] = len(self.jugadores_listos)
        
        if self.fase == "jugando":
            if self.turno_actual < len(self.orden_turnos):
                idx = self.orden_turnos[self.turno_actual]
                info["jugador_actual"] = self.jugadores[idx]
        
        if self.fase == "votacion":
            votante_idx = len(self.votos_impostor)
            if votante_idx < len(self.jugadores):
                info["jugador_actual"] = self.jugadores[votante_idx]
        
        return info