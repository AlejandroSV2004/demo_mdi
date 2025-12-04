# 🤖 Jarvis AI Assistant (Python)

Jarvis es un asistente virtual de voz inspirado en J.A.R.V.I.S. de Iron Man, diseñado para ser extremadamente rápido gracias a una arquitectura híbrida que combina reconocimiento de voz local con generación de respuestas y síntesis de voz en la nube. Además, posee una personalidad sarcástica y formal.

## 🚀 Arquitectura del Sistema

El asistente funciona mediante cuatro módulos principales:

1. **Oído (Local):**  
   Usa **Vosk** para transcribir tu voz en tiempo real directamente en tu PC, sin necesidad de internet.

2. **Cerebro (Nube):**  
   Envía la transcripción a **Google Gemini 1.5 Flash**, donde se genera la respuesta inteligente.

3. **Voz (Nube):**  
   Convierte la respuesta de texto en audio utilizando **ElevenLabs** (voz “Adam”).

4. **Reproducción (Local):**  
   Utiliza **Pygame** para reproducir el audio sin depender de software externo.

---

## 📦 Instalación de Dependencias

Instala todas las librerías necesarias con el siguiente comando:

```bash
pip install sounddevice numpy scipy keyboard google-generativeai elevenlabs python-dotenv pygame vosk
```

---

## 📚 Librerías Utilizadas y Su Función

| Librería                | Función en Jarvis                                                            |
| ----------------------- | ---------------------------------------------------------------------------- |
| **vosk**                | Reconocimiento de voz offline para convertir audio a texto sin latencia.     |
| **google-generativeai** | Conexión con la API de Google Gemini para generar respuestas.                |
| **elevenlabs**          | Generación de voz humana realista a partir del texto.                        |
| **pygame**              | Reproduce los audios generados mediante su módulo `mixer`.                   |
| **sounddevice**         | Captura el audio del micrófono mientras se presiona la tecla asignada.       |
| **numpy**               | Procesa arrays de audio crudo para prepararlos para Vosk.                    |
| **scipy**               | Guarda el audio capturado como archivos `.wav` temporales.                   |
| **keyboard**            | Detecta la tecla push-to-talk utilizada para iniciar y detener la grabación. |
| **python-dotenv**       | Carga las API Keys desde un archivo `.env`.                                  |

---

## ⚙️ Configuración Requerida

### 1. Modelo de Voz Local (Vosk)

Para que Jarvis reconozca tu voz sin conexión:

1. Descarga un modelo desde: [https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models)
2. Obtén el modelo español: **vosk-model-small-es-0.42**
3. Descomprime el archivo.
4. Renombra la carpeta a: **`model`**
5. Colócala en la raíz del proyecto.

Ejemplo de estructura:

```text
Proyecto_Jarvis/
├── main.py
├── .env
├── README.md
└── model/
```

### 2. Configurar las API Keys (.env)

Crea un archivo `.env` con el siguiente contenido:

```env
GOOGLE_API_KEY=tu_clave_de_google_aqui
ELEVENLABS_API_KEY=tu_clave_de_elevenlabs_aqui
```

---

## 🎮 Uso del Asistente

1. Ejecuta el programa principal:

   ```bash
   python main.py
   ```
2. Presiona la tecla **`r`** para hablar y luego presiona **`r`** de nuevo para terminar la grabación (push-to-talk).
3. Presiona **`q`** para cerrar el programa.