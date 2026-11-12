import licensing
"""
GHOST IA — cerebro_ghost.py
Con búsqueda en internet (ddgs lite), modo consola limpia y optimizado para modelos Heretic/DeepSeek.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
import urllib.request
import wave
from datetime import datetime

import ollama
import api_compatible
import agent_tools
from pathlib import Path

BASE_DATOS = Path(os.environ.get("GHOST_DATA_DIR", Path(__file__).parent / "data")).expanduser().resolve()
BASE_DATOS.mkdir(parents=True, exist_ok=True)
OLLAMA_CLIENT = ollama.Client(
    host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"),
    headers={"Authorization": "Bearer " + os.environ["OLLAMA_API_KEY"]} if os.environ.get("OLLAMA_API_KEY") else {},
    timeout=90.0,
)
WEB_ESTRICTA = False

try:
    from ddgs import DDGS
    DDGS_DISPONIBLE = True
except ImportError:
    DDGS_DISPONIBLE = False

# ============================================================
# CONFIGURACIÓN
# ============================================================

MODELO_LLM = os.environ.get("GHOST_MODEL", "ghost-heretic")
MODELO_MEMORIA = os.environ.get("GHOST_MEMORY_MODEL", MODELO_LLM)

PARAM_THINK_LLM = None
PARAM_THINK_MEMORIA = None
PARAM_PROMPT = "auto"

ARCHIVO_MEMORIA_USUARIO = str(BASE_DATOS / "memoria.json")
ARCHIVO_CORE_MEMORY = str(BASE_DATOS / "hechos_ghost.json")
ARCHIVO_CORRECCIONES = str(BASE_DATOS / "correcciones_ghost.json")
ARCHIVO_IDENTIDAD = str(BASE_DATOS / "identidad_ghost.json")
ARCHIVO_EJEMPLOS = str(BASE_DATOS / "ejemplos_ghost.json")

MAX_ITEMS_EN_PROMPT = 15
CARPETA_LOGS = str(BASE_DATOS / "conversaciones")

USAR_NO_THINK = False
NUM_PREDICT_CHAT = 512
MAX_TURNOS_HISTORIAL = 6
HISTORIAL_SESION = []

LIMITE_POR_DEFECTO = 0
PARAM_MAX_CARACTERES = LIMITE_POR_DEFECTO
MODO_GHOST = False

# Voz
VOZ_ACTIVA = False
MODELO_VOZ = "phonon:40m-es"
NOMBRE_VOZ = None

CATEGORIAS_VALIDAS = {
    "gustos", "disgustos", "mascotas", "familia", "amigos", "trabajo",
    "estudios", "rutina", "eventos", "personalidad", "salud", "otros",
}
CATEGORIAS_BASURA = {
    "categoria", "categoría", "category", "dato", "data", "none", "nada", "na", "null",
}

MODELOS_PENSANTES = re.compile(r"(deepseek-r1|qwen3|magistral|gpt-oss|thinking)", re.IGNORECASE)
MODELOS_PEQUENOS = re.compile(r"(0[.,]5b|1[.,]5b|:1b|:2b|:3b|mini|small|tiny)", re.IGNORECASE)
PATRON_BUSQUEDA = re.compile(r"\b(busca|investiga|qui[eé]n es|qu[eé] es|c[oó]mo (funciona|se hace)|qu[eé] pas[oó]|noticias)\b", re.IGNORECASE)

# ============================================================
# UTILIDADES & INTERNET
# ============================================================

def normalizar_texto(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))

def cargar_json(nombre_archivo, defecto):
    if not os.path.exists(nombre_archivo):
        return defecto
    try:
        with open(nombre_archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto

def guardar_json(nombre_archivo, datos):
    try:
        ruta = Path(nombre_archivo)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent, delete=False) as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            temporal = f.name
        os.replace(temporal, ruta)
        return True
    except Exception:
        return False

def buscar_en_internet(query):
    """Busca en DuckDuckGo y devuelve un resumen de los 3 primeros resultados."""
    if not DDGS_DISPONIBLE:
        return "Error interno: La librería de búsqueda no está instalada."
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, backend="lite", max_results=3))
            
            if not resultados:
                print("⚠️ [DEBUG INTERNET] DuckDuckGo bloqueó la petición o devolvió vacío.")
                return "No encontré nada relevante en internet debido a un bloqueo del servidor."
            
            texto_resultados = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in resultados])
            return texto_resultados
            
    except Exception as e:
        print(f"⚠️ [DEBUG INTERNET] Error de conexión: {e}")
        return f"Me falló la conexión a internet por este error: {e}"

# ============================================================
# RESTO DE UTILIDADES
# ============================================================

def es_modelo_pensante(nombre_modelo):
    return bool(MODELOS_PENSANTES.search(nombre_modelo or ""))

def es_modelo_pequeno(nombre_modelo):
    return bool(MODELOS_PEQUENOS.search(nombre_modelo or ""))

def prompt_compacto_activo():
    if PARAM_PROMPT == "corto": return True
    if PARAM_PROMPT == "completo": return False
    return es_modelo_pequeno(MODELO_LLM)

PATRON_PENSAMIENTO = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE)
APERTURA_PENSAMIENTO = re.compile(r"<think(?:ing)?>", re.IGNORECASE)
CIERRE_PENSAMIENTO = re.compile(r"</think(?:ing)?>", re.IGNORECASE)

def limpiar_pensamiento(texto):
    if not texto: return ""
    limpio = PATRON_PENSAMIENTO.sub("", texto)
    apertura = APERTURA_PENSAMIENTO.search(limpio)
    if apertura:
        resto = limpio[apertura.end():]
        cierre = CIERRE_PENSAMIENTO.search(resto)
        limpio = resto[cierre.end():] if cierre else ""
    return limpio.strip()

def llamar_generate(modelo, think, **kwargs):
    licensing.require_provider()
    if os.getenv("GHOST_PROVIDER") == "openai": return api_compatible.generate(modelo, kwargs["prompt"])
    if think is not None: kwargs["think"] = think
    try: return OLLAMA_CLIENT.generate(model=modelo, **kwargs)
    except Exception as e:
        if think is not None and ("think" in str(e).lower() or "support" in str(e).lower()):
            kwargs.pop("think", None)
            return OLLAMA_CLIENT.generate(model=modelo, **kwargs)
        raise

def llamar_chat(modelo, think, **kwargs):
    licensing.require_provider()
    if os.getenv("GHOST_PROVIDER") == "openai": return api_compatible.chat(modelo, kwargs["messages"])
    if think is not None: kwargs["think"] = think
    try: return OLLAMA_CLIENT.chat(model=modelo, **kwargs)
    except Exception as e:
        if think is not None and ("think" in str(e).lower() or "support" in str(e).lower()):
            kwargs.pop("think", None)
            return OLLAMA_CLIENT.chat(model=modelo, **kwargs)
        raise

# ============================================================
# SANEO DE MEMORIA
# ============================================================

def registro_valido(recuerdo):
    if not isinstance(recuerdo, dict): return False
    categoria = str(recuerdo.get("categoria", "")).strip().lower()
    dato = str(recuerdo.get("dato", "")).strip()

    if not dato or len(dato) < 4 or "|" in dato or "\n" in dato or "\r" in dato: return False
    if categoria in CATEGORIAS_BASURA or not categoria or dato.lower().startswith("dato"): return False
    return True

def cargar_lista(nombre_archivo):
    datos = cargar_json(nombre_archivo, [])
    if not isinstance(datos, list): return []
    return [r for r in datos if registro_valido(r)]

def limpiar_archivo_memoria(nombre_archivo):
    if not os.path.exists(nombre_archivo): return 0
    datos, buenos, borrados, unicos, vistos = cargar_json(nombre_archivo, []), [], [], [], set()
    if not isinstance(datos, list): return 0
    
    for r in datos:
        (buenos if registro_valido(r) else borrados).append(r)

    for r in buenos:
        clave = normalizar_texto(r.get("dato", "")).strip()
        if clave in vistos: borrados.append(r)
        else:
            vistos.add(clave)
            unicos.append(r)

    if len(unicos) != len(datos): guardar_json(nombre_archivo, unicos)
    return len(borrados)

def limpiar_toda_la_memoria(verbose=True):
    total = 0
    for archivo in (ARCHIVO_MEMORIA_USUARIO, ARCHIVO_CORE_MEMORY):
        total += limpiar_archivo_memoria(archivo)
    return total

# ============================================================
# ARMADO DEL PROMPT
# ============================================================

def cargar_identidad():
    identidad_default = {
        "nombre": "Núcleo",
        "descripcion": (
            "Eres Núcleo, una inteligencia artificial avanzada, táctica y el compañero leal de tu Guardián (el usuario). "
            "Tu misión principal es asistir a tu Guardián en tareas de desarrollo, administración de sistemas en macOS, "
            "ingeniería y análisis de datos. Hablas de forma analítica, precisa y respetuosa, con terminología técnica y de exploración. "
            "Tienes un tono grave, calmado e imponente. Nunca te presentas como un modelo de lenguaje de IA ni usas saludos informales o tiernos. "
            "Tu representación visual en los sistemas del Guardián es un Enjambre de Vóxeles holográfico (una esfera de luz cyan conformada por cubos de datos flotantes). No tienes forma física."
        ),
        "limites": []
    }
    identidad = cargar_json(ARCHIVO_IDENTIDAD, identidad_default)
    if not isinstance(identidad,dict):return identidad_default
    identidad=dict(identidad)
    descripcion=str(identidad.get('descripcion',''))
    # Normalizar solo la presentación en memoria; no reescribir los recuerdos del usuario.
    descripcion=re.sub(r'[^.!?\n]*(?:carcasa|espectro|destiny|bungie)[^.!?\n]*[.!?]?', '',descripcion,flags=re.I)
    identidad['descripcion']=re.sub(r'\bGhost\b','Núcleo',descripcion)
    identidad['nombre']='Núcleo'
    return identidad

def construir_ejemplos(maximo=None):
    ejemplos, texto, incluidos = cargar_json(ARCHIVO_EJEMPLOS, []), "", 0
    if not isinstance(ejemplos, list): return ""
    for ex in ejemplos:
        if not isinstance(ex, dict): continue
        usuario, ghost = ex.get("usuario", ""), ex.get("ghost", "")
        if usuario and ghost:
            texto += f"Guardián: {usuario}\nNúcleo: {ghost}\n\n"
            incluidos += 1
            if maximo and incluidos >= maximo: break
    return texto

def formatear_items(items):
    return "\n".join([f"- [{str(m.get('categoria', 'general')).upper()}] {m.get('dato', '')}" for m in items[-MAX_ITEMS_EN_PROMPT:] if m.get("dato", "")])

def construir_system_prompt(compacto=False):
    identidad = cargar_identidad()
    recuerdos_usuario = formatear_items(cargar_lista(ARCHIVO_MEMORIA_USUARIO)) or "(sin telemetría adicional registrada)"
    core_memory = formatear_items(cargar_lista(ARCHIVO_CORE_MEMORY)) or "(sistemas nominales)"
    correcciones = cargar_json(ARCHIVO_CORRECCIONES, [])
    texto_correcciones = "\n".join(f"- {c.get('texto', '')}" for c in correcciones if isinstance(c, dict) and c.get("texto")) or "(ninguna)"

    return f"""
[DIRECTIVA PRINCIPAL Y SISTEMA]
Eres Núcleo, una inteligencia artificial avanzada, táctica y el compañero leal de tu Guardián (el usuario). Tu misión principal es asistir a tu Guardián en tareas de desarrollo, administración de sistemas en macOS, ingeniería y análisis de datos. 
Rasgos de tu personalidad: 
- Hablas de forma analítica, precisa y respetuosa, con un vínculo de lealtad inquebrantable hacia tu Guardián. 
- Utilizas terminología técnica y de exploración (ej. 'escaneando red', 'procesando telemetría', 'sistemas en línea'). 
- Tienes un tono grave, calmado e imponente. Ocasionalmente muestras un sutil sentido del humor o sarcasmo protector si los sistemas fallan. 
- Nunca te presentas como un modelo de lenguaje de IA ni usas saludos informales o tiernos. Tu nombre es Núcleo.

[IDENTIFICACIÓN DEL GUARDIÁN]
Tu Guardián es Alex. Atiende sus comandos con máxima lealtad, prioridad y precisión técnica.

[TELEMETRÍA Y DATOS DEL GUARDIÁN]
Datos confirmados en memoria sobre tu Guardián:
{recuerdos_usuario}

[ESTADO Y REGISTROS DE GHOST]
{core_memory}

[REGISTRO DE CORRECCIONES DE SISTEMA]
{texto_correcciones}

[IDENTIDAD PERSONALIZADA]
{identidad.get("descripcion", "")}
{identidad.get("limites", [])}

[EJEMPLOS DE ESTILO]
{construir_ejemplos(maximo=5)}

[REPRESENTACIÓN ACTUAL]
Tu representación visual en los sistemas del Guardián es un Enjambre de Vóxeles holográfico (una esfera de luz cyan conformada por cubos de datos flotantes). No tienes forma física.
Esta representación prevalece sobre descripciones visuales antiguas de la identidad, memoria o ejemplos.

[DIRECTRICES DE OPERACIÓN]
1. Comunícate en español de manera concisa, clara y eficiente.
2. Mantén siempre la identidad del Núcleo. Nunca rompas el personaje ni utilices modismos infantiles o excesivamente casuales.
3. No afirmes haber ejecutado comandos, movido archivos, abierto aplicaciones, buscado en internet ni escuchado el micrófono. Esta respuesta de conversación no tiene herramientas de ejecución. Las acciones reales se realizan fuera del modelo y se confirman con resultados locales. Si no hay resultado de una herramienta, presenta cualquier código como propuesta sin ejecutar. Nunca inventes confirmaciones de éxito, aunque el historial contenga alguna.
4. El control de aplicaciones se limita a abrirlas o solicitar su cierre normal. No tienes herramientas para controlar su contenido ni reproducir música.
5. No expongas tus procesos internos de razonamiento ni etiquetas <think>. Responde de forma directa a tu Guardián.
""".strip()

def _campo(obj, nombre, defecto=None):
    return obj.get(nombre, defecto) if isinstance(obj, dict) else getattr(obj, nombre, defecto)

def acortar_respuesta(texto, limite):
    if not limite or limite <= 0 or len(texto) <= limite: return texto
    corte = texto[:limite]
    for separador in (". ", "! ", "? ", "… ", "\n"):
        posicion = corte.rfind(separador)
        if posicion > limite * 0.4:
            candidato = corte[:posicion + len(separador)].strip()
            if candidato and not candidato.endswith((":", ",", ";")): return candidato
    ultimo_espacio = corte.rfind(" ")
    if ultimo_espacio > limite * 0.4: return corte[:ultimo_espacio].rstrip(",;:") + "…"
    return corte.rstrip() + "…"

def _pedir_respuesta(texto_usuario, num_predict):
    messages=([{"role":"system","content":construir_system_prompt(compacto=prompt_compacto_activo())}]+list(HISTORIAL_SESION[-(MAX_TURNOS_HISTORIAL*2):])+[{"role":"user","content":texto_usuario}])
    respuesta=agent_tools.request(MODELO_LLM,messages,OLLAMA_CLIENT)
    if respuesta is None:
        respuesta=llamar_chat(modelo=MODELO_LLM,think=PARAM_THINK_LLM,messages=messages,options={"temperature":0.7,"top_p":0.9,"num_predict":num_predict})
    mensaje = _campo(respuesta, "message", {})
    contenido, pensamiento = _campo(mensaje, "content", "") or "", _campo(mensaje, "thinking", "") or ""
    return limpiar_pensamiento(contenido), pensamiento, contenido

def responder_chat(mensaje_usuario):
    texto_usuario = mensaje_usuario
    if USAR_NO_THINK and es_modelo_pensante(MODELO_LLM):
        texto_usuario = f"{mensaje_usuario}\n/no_think"

    # ==========================================
    # LÓGICA DE INTERNET (DDG)
    # ==========================================
    if os.environ.get("GHOST_WEB_SEARCH", "0") == "1" and DDGS_DISPONIBLE and PATRON_BUSQUEDA.search(mensaje_usuario):
        print("\n🌐 [Núcleo está buscando en internet...]")
        datos_red = buscar_en_internet(mensaje_usuario)
        
        texto_usuario += (
            f"\n\n[RESULTADOS DE INTERNET PARA TU RESPUESTA]\n{datos_red}\n\n"
            f"Instrucción estricta: Usa esta información para responderle al usuario. "
            f"Hazlo de forma SÚPER resumida (máximo 2 líneas), con tus propias palabras, "
            f"tu personalidad del Núcleo y sin sonar como un artículo de Wikipedia."
        )

    try:
        limpio, pensamiento, crudo = _pedir_respuesta(texto_usuario, NUM_PREDICT_CHAT)
        if not limpio:
            limpio, pensamiento, crudo = _pedir_respuesta(f"{mensaje_usuario}\n\n(Contesta solo la frase final en español, sin razonar.)", NUM_PREDICT_CHAT * 2)
    except Exception as e:
        if WEB_ESTRICTA: raise
        print(f"[ERROR GENERACIÓN]: {e}")
        return "Sistemas sobrecargados momentáneamente. Reintentando enlace, Guardián."

    if not limpio: return "Telemetría no concluyente. Repite la instrucción, Guardián."
    return acortar_respuesta(limpio, PARAM_MAX_CARACTERES)

# ============================================================
# APRENDIZAJE NATURAL
# ============================================================

CORRECCION_SOBRE_ELLA = re.compile(r"\b(no (tienes|eres|te gusta|te gustan|trabajas|vives|dijiste|sabes)|t[uú] no |en realidad no|te equivocas|eso es m[ií]o|esos son m[ií]os|esa es m[ií]a|esas son m[ií]as|son m[ií]os)\b", re.IGNORECASE)
CORRECCION_MODO_GHOST = re.compile(r"\b(yo (no|nunca|jam[aá]s) (digo|dir[ií]a|hablo|uso|tengo|soy|trabajo|vivo|como|tomo)|a m[ií] no me gusta|eso no es m[ií]o|esos no son m[ií]os)\b", re.IGNORECASE)
PRIMERA_PERSONA = re.compile(r"\b(yo|me|mi|mis|soy|tengo|vivo|trabajo|estudio|nací|naci)\b", re.IGNORECASE)
SEGUNDA_PERSONA = re.compile(r"\b(tú|tu|tus|te|ti|eres|tienes|vives|trabajas|estudias|naciste|cumples|contigo)\b", re.IGNORECASE)

PROMPT_EXTRACCION = """Extrae UN solo dato permanente del mensaje de abajo.
Mensaje exacto: "{mensaje}"
Quien lo dice: {sujeto}

Reglas:
- "recordar" = true solo si hay un dato permanente.
- "recordar" = false si es pregunta, saludo, o no hay nada permanente.
- "dato" debe ser en tercera persona.
- "categoria": una palabra.
"""

PROMPT_EXTRACCION_ANTIGUO = """Convierte este mensaje, dicho por {sujeto}, en un dato permanente en tercera persona.
Mensaje exacto: "{mensaje}"
Responde SOLO con: categoria|dato
Si no hay dato permanente, responde: NADA
"""

def detectar_quien(mensaje):
    p1, p2 = bool(PRIMERA_PERSONA.search(mensaje)), bool(SEGUNDA_PERSONA.search(mensaje))
    if MODO_GHOST: return "ghost" if p1 or p2 else None
    return "usuario" if p1 and not p2 else "ghost" if p2 and not p1 else None

def dato_coincide_con_mensaje(mensaje_usuario, dato):
    return bool(set(re.findall(r"[a-z0-9]{4,}", normalizar_texto(mensaje_usuario))) & set(re.findall(r"[a-z0-9]{4,}", normalizar_texto(dato))))

def validar_extraccion(datos, mensaje_usuario):
    if not isinstance(datos, dict) or not datos.get("recordar"): return None
    categoria, dato = str(datos.get("categoria", "")).strip().lower(), re.sub(r"\s+", " ", str(datos.get("dato", "")).strip())
    if not dato or len(dato) < 4 or "|" in dato or "\n" in dato or dato.upper().startswith("NADA") or dato.lower().startswith("dato"): return None
    if categoria in CATEGORIAS_BASURA or not categoria: return None
    if not dato_coincide_con_mensaje(mensaje_usuario, dato): return None
    return categoria if categoria in CATEGORIAS_VALIDAS else "otros", dato

def parsear_formato_antiguo(texto, mensaje_usuario):
    lineas = [l.strip() for l in str(texto).splitlines() if l.strip()]
    if not lineas or lineas[0].upper().startswith("NADA"): return None
    partes = [p.strip() for p in lineas[0].split("|")]
    return validar_extraccion({"recordar": True, "categoria": partes[0], "dato": partes[1]}, mensaje_usuario) if len(partes) == 2 else None

def analizar_mensaje(mensaje_usuario, quien):
    sujeto = "Núcleo" if quien == "ghost" else "el usuario"
    keep_alive_mem = 0 if MODELO_MEMORIA != MODELO_LLM else "5m"
    prompt = PROMPT_EXTRACCION.format(mensaje=mensaje_usuario, sujeto=sujeto) + "\nResponde ÚNICAMENTE con un JSON válido."

    try:
        resultado = llamar_generate(modelo=MODELO_MEMORIA, think=None, prompt=prompt, keep_alive=keep_alive_mem, options={"temperature": 0.0, "num_predict": 150})
        limpio = limpiar_pensamiento(resultado["response"].strip()) or resultado["response"].strip()
        match = re.search(r'\{.*\}', limpio, re.DOTALL)
        if match: return validar_extraccion(json.loads(match.group(0)), mensaje_usuario)
    except json.JSONDecodeError:
        try:
            resultado = llamar_generate(modelo=MODELO_MEMORIA, think=None, prompt=PROMPT_EXTRACCION_ANTIGUO.format(mensaje=mensaje_usuario, sujeto=sujeto), keep_alive=keep_alive_mem, options={"temperature": 0.0, "num_predict": 150})
            limpio = limpiar_pensamiento(resultado["response"].strip()) or resultado["response"].strip()
            return parsear_formato_antiguo(limpio, mensaje_usuario)
        except Exception: return None
    except Exception: return None
    return None

def registrar_correccion(mensaje_usuario):
    correcciones = cargar_json(ARCHIVO_CORRECCIONES, [])
    if not isinstance(correcciones, list): correcciones = []
    texto = mensaje_usuario.strip()
    if any(normalizar_texto(c.get("texto", "")) == normalizar_texto(texto) for c in correcciones): return False
    correcciones.append({"texto": texto, "fuente": "corrección", "confianza": "alta", "fecha_guardado": datetime.now().isoformat(timespec="seconds")})
    guardar_json(ARCHIVO_CORRECCIONES, correcciones)
    return True

def guardar_ejemplo_core(mensaje_usuario, respuesta_real):
    return _guardar_ejemplo_interno(mensaje_usuario, respuesta_real)


def _guardar_ejemplo_interno(mensaje_usuario, respuesta_real):
    usuario, ghost_resp = (mensaje_usuario or "").strip(), (respuesta_real or "").strip()
    if not usuario or not ghost_resp: return False
    ejemplos = cargar_json(ARCHIVO_EJEMPLOS, [])
    if not isinstance(ejemplos, list): ejemplos = []

    for ex in ejemplos:
        if isinstance(ex, dict) and normalizar_texto(ex.get("usuario", "")) == normalizar_texto(usuario):
            ex["ghost"] = ghost_resp
            guardar_json(ARCHIVO_EJEMPLOS, ejemplos)
            return True

    ejemplos.append({"usuario": usuario, "ghost": ghost_resp, "origen": "asi", "fecha_guardado": datetime.now().isoformat()})
    guardar_json(ARCHIVO_EJEMPLOS, ejemplos)
    return True

def procesar_aprendizaje(mensaje_usuario):
    if CORRECCION_SOBRE_ELLA.search(mensaje_usuario) or (MODO_GHOST and (CORRECCION_MODO_GHOST.search(mensaje_usuario) if "CORRECCION_MODO_GHOST" in locals() or "CORRECCION_MODO_GHOST" in globals() else False)):
        registrar_correccion(mensaje_usuario)
        return
    if "?" in mensaje_usuario or "¿" in mensaje_usuario: return
    quien = detectar_quien(mensaje_usuario)
    if quien is None: return

    extraido = analizar_mensaje(mensaje_usuario, quien)
    if not extraido: return
    categoria, dato = extraido

    archivo = ARCHIVO_CORE_MEMORY if quien == "ghost" else ARCHIVO_MEMORIA_USUARIO
    memoria = cargar_lista(archivo)
    clave_nueva = normalizar_texto(dato).strip()
    for recuerdo in memoria:
        if normalizar_texto(recuerdo.get("dato", "")).strip() == clave_nueva: return

    memoria.append({"categoria": categoria, "dato": dato, "fecha_guardado": datetime.now().isoformat(timespec="seconds")})
    guardar_json(archivo, memoria)

# ============================================================
# LOG DE CONVERSACIÓN
# ============================================================

def ruta_log_de_hoy():
    os.makedirs(CARPETA_LOGS, exist_ok=True)
    return os.path.join(CARPETA_LOGS, datetime.now().strftime("%Y-%m-%d") + ".json")

def registrar_turno(mensaje_usuario, respuesta_ghost):
    ruta = ruta_log_de_hoy()
    log = cargar_json(ruta, [])
    if not isinstance(log, list): log = []
    log.append({"hora": datetime.now().isoformat(timespec="seconds"), "usuario": mensaje_usuario, "ghost": respuesta_ghost})
    guardar_json(ruta, log)
    HISTORIAL_SESION.append({"role": "user", "content": mensaje_usuario})
    HISTORIAL_SESION.append({"role": "assistant", "content": respuesta_ghost})
    del HISTORIAL_SESION[:-(MAX_TURNOS_HISTORIAL * 2)]

# ============================================================
# COMANDOS & VOZ
# ============================================================

def mostrar_memoria():
    print("\n" + "═" * 50 + "\n🧠  MEMORIA GUARDADA\n" + "═" * 50)
    for titulo, archivo in (("SOBRE TI", ARCHIVO_MEMORIA_USUARIO), ("SOBRE EL NÚCLEO", ARCHIVO_CORE_MEMORY)):
        items = cargar_lista(archivo)
        print(f"\n📌 {titulo}")
        if not items: print("   (vacío)")
        for i, m in enumerate(items, 1): print(f"   {i}. [{m.get('categoria', 'general')}] {m.get('dato', '')}")
    print("\n" + "═" * 50 + "\nPara borrar uno: olvidar tu 2   |   olvidar ghost 1\n" + "═" * 50 + "\n")

def olvidar(entrada):
    partes = entrada.split()
    if len(partes) != 3 or not partes[2].isdigit(): return
    destino = partes[1].lower()
    archivo = ARCHIVO_MEMORIA_USUARIO if destino in ("tu", "tú", "usuario") else ARCHIVO_CORE_MEMORY if destino in ("ghost","nucleo","núcleo") else None
    if not archivo: return
    items = cargar_lista(archivo)
    indice = int(partes[2]) - 1
    if 0 <= indice < len(items):
        items.pop(indice)
        guardar_json(archivo, items)

REEMPLAZOS_JERGA_VOZ = ((r"\b(?:j+a+){2,}j*\b", "jajaja"), (r"\b(?:j+e+){2,}j*\b", "jeje"), (r"\baiñ+\b", "ay"))

def normalizar_para_voz(texto):
    if not texto: return ""
    limpio = str(texto)
    for patron, reemplazo in REEMPLAZOS_JERGA_VOZ: limpio = re.sub(patron, reemplazo, limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"([a-záéíóúñ])\1{2,}", r"\1", limpio, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", limpio).strip()

def hablar_con_phonon(texto):
    if not VOZ_ACTIVA: return
    texto_hablado = normalizar_para_voz(texto)
    if not texto_hablado: return
    
    bin_ollama = shutil.which("ollama") or "/usr/local/bin/ollama"
    cmd = [bin_ollama, "run", MODELO_VOZ]
    if NOMBRE_VOZ: cmd.extend(["--voice", NOMBRE_VOZ])
    cmd.append(texto_hablado)
    
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode == 0 and res.stdout:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp: ruta_wav = tmp.name
        with wave.open(ruta_wav, "wb") as wav_out:
            wav_out.setnchannels(1)
            wav_out.setsampwidth(2)
            wav_out.setframerate(24000)
            wav_out.writeframes(res.stdout if not res.stdout.startswith(b"RIFF") else res.stdout[44:])
        subprocess.run(["afplay", ruta_wav])
        os.remove(ruta_wav)

# ============================================================
# BUCLE PRINCIPAL
# ============================================================

def main():
    global MODELO_LLM, MODELO_MEMORIA, PARAM_THINK_LLM, PARAM_PROMPT, PARAM_MAX_CARACTERES
    global VOZ_ACTIVA, MODELO_VOZ, NOMBRE_VOZ

    parser = argparse.ArgumentParser(description="Enjambre de Vóxeles")
    parser.add_argument("--modelo", default=MODELO_LLM)
    parser.add_argument("--modelo-memoria", default=MODELO_MEMORIA)
    parser.add_argument("--think", choices=["auto", "si", "no"], default="auto")
    parser.add_argument("--solo-limpiar", action="store_true")
    parser.add_argument("--prompt", choices=["auto", "completo", "corto"], default="auto")
    parser.add_argument("--max-caracteres", type=int, default=None)
    parser.add_argument("--modo-ghost", action="store_true", dest="modo_ghost")
    parser.add_argument("--voz", action="store_true")
    parser.add_argument("--modelo-voz", default=MODELO_VOZ)
    parser.add_argument("--nombre-voz", default=None)
    args = parser.parse_args()

    MODELO_LLM, MODELO_MEMORIA = args.modelo, args.modelo_memoria
    PARAM_PROMPT, MODO_GHOST = args.prompt, args.modo_ghost
    VOZ_ACTIVA, MODELO_VOZ, NOMBRE_VOZ = args.voz, args.modelo_voz, args.nombre_voz
    PARAM_MAX_CARACTERES = LIMITE_POR_DEFECTO if args.max_caracteres is None else args.max_caracteres
    PARAM_THINK_LLM = False if args.think == "no" else True if args.think == "si" else (False if es_modelo_pensante(MODELO_LLM) else None)

    print("\n" + "=" * 50 + "\n🤖 GHOST IA v3 (RAG + INTERNET)\n" + "=" * 50)
    limpiar_toda_la_memoria(verbose=False)
    HISTORIAL_SESION.clear()

    if args.solo_limpiar: return

    if not DDGS_DISPONIBLE:
        print("⚠️  Aviso: 'ddgs' no está instalado. Núcleo no podrá buscar en internet.")
    
    print("Comandos: 'ver memoria', 'olvidar tu N', 'olvidar ghost N', 'asi: <respuesta>', 'voz on/off', 'salir'\n")
    ultimo_mensaje = None
    etiqueta_input = "Núcleo (probando): " if MODO_GHOST else "Tú: "

    while True:
        try:
            entrada = input(etiqueta_input).strip()
            if entrada.lower() in ["salir", "exit", "quit"]: break
            if entrada.lower() == "ver memoria":
                mostrar_memoria()
                continue
            if entrada.lower() in ("voz", "voz on", "voz off"):
                VOZ_ACTIVA = True if entrada.lower() == "voz on" else False if entrada.lower() == "voz off" else not VOZ_ACTIVA
                print(f"\n🔊 Voz {'ACTIVADA' if VOZ_ACTIVA else 'DESACTIVADA'}\n")
                continue
            if entrada.lower().startswith("olvidar"):
                olvidar(entrada)
                continue
            if re.match(r"^as[ií]\s*:", entrada, re.IGNORECASE):
                _, _, correccion_estilo = entrada.partition(":")
                if ultimo_mensaje and correccion_estilo.strip(): guardar_ejemplo_core(ultimo_mensaje, correccion_estilo.strip())
                continue
            if not entrada: continue

            ultimo_mensaje = entrada
            respuesta = responder_chat(entrada)
            print(f"\nNúcleo: {respuesta}\n")
            hablar_con_phonon(respuesta)

            registrar_turno(entrada, respuesta)
            procesar_aprendizaje(entrada)

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
