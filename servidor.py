"""Enjambre de Vóxeles · servidor de un solo propietario. Ejecutar con un único worker."""
from pathlib import Path
import os
from dotenv import load_dotenv
BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
import json
from contextlib import contextmanager
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit
from uuid import UUID
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, field_validator
import httpx
import ollama
import cerebro_ghost as cerebro
import skills_mac
import licensing
import app_catalog
import api_compatible
import agent_tools
import tool_runtime
import group_actions
import file_actions
import desktop_actions
import web_actions
import voice_actions
import local_voice
import wake_voice

PUBLICO = os.getenv('GHOST_PUBLIC', '0') == '1'
TOKEN = os.getenv('GHOST_API_TOKEN', '')
HOSTS = [h.strip() for h in os.getenv('GHOST_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').split(',') if h.strip()]
ORIGENES = [x.strip().rstrip('/') for x in os.getenv('GHOST_ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',') if x.strip()]
if PUBLICO and (len(TOKEN) < 32 or not ORIGENES or any(not x.startswith('https://') for x in ORIGENES) or '*' in HOSTS or '*' in ORIGENES):
    raise RuntimeError('Modo público: requiere token >=32 caracteres, hosts explícitos y orígenes HTTPS.')
BIND = os.getenv('GHOST_BIND', '127.0.0.1')
if not PUBLICO and BIND not in ('127.0.0.1', 'localhost', '::1'):
    raise RuntimeError('Para escuchar fuera de loopback configura el modo público protegido.')
cerebro.WEB_ESTRICTA = True
# La búsqueda externa es opt-in. La voz se reproduce en el navegador del usuario.
LOCK = threading.Lock()
DB = cerebro.BASE_DATOS / 'chat.sqlite3'
@contextmanager
def database():
    con = sqlite3.connect(DB)
    try:
        with con:
            yield con
    finally:
        con.close()

with database() as con:
    con.execute('CREATE TABLE IF NOT EXISTS turns (id INTEGER PRIMARY KEY, session TEXT, user TEXT, answer TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
    con.execute('CREATE INDEX IF NOT EXISTS session_turns ON turns(session,id)')
    con.execute('CREATE TABLE IF NOT EXISTS pending_tools (id TEXT PRIMARY KEY, session TEXT UNIQUE, text TEXT, call TEXT, created REAL)')
    con.execute('CREATE TABLE IF NOT EXISTS tool_events (id INTEGER PRIMARY KEY, session TEXT, name TEXT, state TEXT, created REAL)')
app = FastAPI(title='Enjambre de Vóxeles', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGENES, allow_methods=['GET','POST'], allow_headers=['Authorization','Content-Type'], allow_credentials=False)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=HOSTS)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')
limites = defaultdict(deque)

@app.middleware('http')
async def seguridad(request: Request, call_next):
    ruta = request.url.path
    api = ruta.startswith('/api/') or ruta == '/chat'
    if api:
        cliente = request.client.host if request.client else ''
        origen = request.headers.get('origin')
        if origen and origen.rstrip('/') not in ORIGENES:
            return JSONResponse({'detail': 'Origen no autorizado.'}, status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Acceso cruzado bloqueado.'}, status_code=403)
        if TOKEN:
            if not secrets.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + TOKEN):
                return JSONResponse({'detail': 'Introduce el token de acceso en Conexión.'}, status_code=401)
        elif PUBLICO or cliente not in ('127.0.0.1','::1','localhost','testclient'):
            return JSONResponse({'detail':'Solo se permite acceso local.'}, status_code=403)
        if request.method == 'POST':
            if not request.headers.get('content-type','').startswith('application/json'):
                return JSONResponse({'detail':'Se requiere JSON.'}, status_code=415)
            # Límite sobre bytes reales, incluso sin Content-Length.
            cuerpo = bytearray()
            async for parte in request.stream():
                cuerpo.extend(parte)
                if len(cuerpo) > (7_000_000 if ruta in ('/api/voice/transcribe','/api/voice/local/transcribe') else 20000):
                    return JSONResponse({'detail':'Petición demasiado grande.'}, status_code=413)
            request._body = bytes(cuerpo)
            ahora = time.monotonic()
            # Una instancia atiende a un propietario: límite global acotado.
            es_escucha=ruta=='/api/voice/local/transcribe'
            limite=60 if es_escucha else 30
            cola = limites['wake' if es_escucha else 'owner']
            while cola and ahora - cola[0] > 60: cola.popleft()
            if len(cola) >= limite:
                return JSONResponse({'detail':f'Límite de {limite} peticiones por minuto.'}, status_code=429)
            cola.append(ahora)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' http://localhost:* http://127.0.0.1:* https:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    return response

class MensajeUsuario(BaseModel):
    texto: str = Field(min_length=1, max_length=6000)
    session_id: str
    modelo: str | None = Field(default=None, max_length=120, pattern=r'^[\w.\-/:]+$')
    confirmar_skill: bool = False
    tool_request_id: str | None = Field(default=None,max_length=36)

    @field_validator('texto')
    @classmethod
    def no_vacio(cls, value):
        if not value.strip(): raise ValueError('Mensaje vacío')
        return value.strip()

    @field_validator('session_id')
    @classmethod
    def session_valida(cls, value):
        return str(UUID(value))

def historial(session):
    with database() as con:
        filas = con.execute('SELECT user,answer FROM turns WHERE session=? ORDER BY id DESC LIMIT 12', (session,)).fetchall()
    return list(reversed(filas))

def selected_tool(call,mensaje,*,confirmed=False):
    try:
        result=tool_runtime.execute(call,mensaje.session_id,cerebro.BASE_DATOS,confirmed=confirmed,public=PUBLICO,request_text=mensaje.texto)
    except (ValueError,PermissionError,FileNotFoundError):
        result={'respuesta':'No pude preparar o ejecutar esa herramienta. Revisa los permisos, repite la búsqueda o pide una acción más específica. No confirmé ningún movimiento.'}
    except (OSError,web_actions.SearchUnavailable,httpx.HTTPError):
        result={'respuesta':'La herramienta no pudo completar la consulta. Revisa permisos o conexión e inténtalo de nuevo.'}
    if result.get('requiere_confirmacion'):
        from uuid import uuid4
        request_id=str(uuid4())
        with database() as con:
            con.execute('DELETE FROM pending_tools WHERE session=? OR created<?',(mensaje.session_id,time.time()-300))
            con.execute('INSERT INTO pending_tools VALUES(?,?,?,?,?)',(request_id,mensaje.session_id,mensaje.texto,json.dumps(call),time.time()))
        return {**result,'tool_request_id':request_id,'popup':None}
    with database() as con:
        con.execute('INSERT INTO turns(session,user,answer) VALUES(?,?,?)',(mensaje.session_id,mensaje.texto,result['respuesta']))
        con.execute('INSERT INTO tool_events(session,name,state,created) VALUES(?,?,?,?)',(mensaje.session_id,call['name'],'handled',time.time()))
    return {**result,'popup':None,'advertencia':None,'herramienta':{'name':call['name'],'mode':'native'}}

@app.get('/')
def inicio():
    return FileResponse(BASE / 'index.html')

@app.get('/api/status')
def estado():
    conectado, modelos = False, []
    try:
        licensing.require_provider()
        if os.getenv('GHOST_PROVIDER') == 'openai':
            # Algunos proveedores no ofrecen /models. La prueba del asistente
            # verifica chat/completions; aquí se consulta sin generar ni cobrar tokens.
            base = os.environ['GHOST_API_BASE'].rstrip('/')
            key = os.getenv('GHOST_API_KEY','')
            try:
                result = httpx.get(base+'/models',headers=api_compatible.request_headers(),timeout=5,follow_redirects=False)
                result.raise_for_status()
                modelos = [m['id'] for m in result.json().get('data',[]) if isinstance(m,dict) and isinstance(m.get('id'),str)]
            except Exception:
                # La disponibilidad real se comprobará al enviar un mensaje.
                modelos = [cerebro.MODELO_LLM]
        else:
            cliente = ollama.Client(host=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'), headers={'Authorization':'Bearer '+os.environ['OLLAMA_API_KEY']} if os.getenv('OLLAMA_API_KEY') else {}, timeout=5)
            modelos = [m.model for m in cliente.list().models]
        conectado = True
    except Exception:
        pass
    host = urlsplit(os.getenv('OLLAMA_HOST','http://127.0.0.1:11434')).hostname
    return {'licencia':licensing.current(),'proveedor':os.getenv('GHOST_PROVIDER','ollama'), 'conectado':conectado, 'modelos':modelos, 'modelo':cerebro.MODELO_LLM, 'servidor_ollama':host, 'publico':PUBLICO, 'skills': not PUBLICO and os.getenv('GHOST_ENABLE_SKILLS','0') == '1', 'aprendizaje':os.getenv('GHOST_LEARNING','1') == '1', 'web':os.getenv('GHOST_ENABLE_WEB','1')=='1' and not PUBLICO, 'microfono':os.getenv('GHOST_ENABLE_MIC','0')=='1' and not PUBLICO, 'voz':voice_actions.provider_info(), 'herramientas':{'mode':agent_tools.mode(cerebro.MODELO_LLM),'catalog':[t['function']['name'] for t in agent_tools.available(local=not PUBLICO,skills=os.getenv('GHOST_ENABLE_SKILLS','0')=='1',web=os.getenv('GHOST_ENABLE_WEB','1')=='1',text='')]}}

@app.get('/api/apps')
def aplicaciones_instaladas():
    if PUBLICO:raise HTTPException(403,'El catálogo de aplicaciones solo está disponible en modo local.')
    if skills_mac.platform.system()!='Darwin':return {'apps':[],'supported':False}
    return {'apps':app_catalog.installed_apps(),'supported':True}

@app.get('/api/history/{session}')
def leer_historial(session: str):
    try: session = str(UUID(session))
    except ValueError: raise HTTPException(422,'Sesión inválida')
    return {'turnos': [{'usuario':u,'ghost':a} for u,a in historial(session)]}

@app.get('/api/memory')
def memoria():
    with LOCK:
        return {'usuario':cerebro.cargar_lista(cerebro.ARCHIVO_MEMORIA_USUARIO), 'ghost':cerebro.cargar_lista(cerebro.ARCHIVO_CORE_MEMORY)}

@app.post('/chat')
@app.post('/api/chat')
def chat(mensaje: MensajeUsuario):
    if not LOCK.acquire(blocking=False):
        raise HTTPException(409,'Núcleo procesa otra solicitud. Espera y vuelve a enviar.')
    try:
        texto, bajo = mensaje.texto, mensaje.texto.lower()
        if mensaje.tool_request_id:
            if not mensaje.confirmar_skill:raise HTTPException(400,'Confirma la herramienta antes de ejecutarla.')
            with database() as con:
                pending=con.execute('SELECT session,text,call,created FROM pending_tools WHERE id=?',(mensaje.tool_request_id,)).fetchone()
                if not pending or pending[0]!=mensaje.session_id or pending[1]!=texto or time.time()-pending[3]>300:
                    raise HTTPException(409,'La confirmación no pertenece a este mensaje o venció. Vuelve a solicitar la acción.')
                con.execute('DELETE FROM pending_tools WHERE id=?',(mensaje.tool_request_id,))
            return selected_tool(json.loads(pending[2]),mensaje,confirmed=True)
        turnos = historial(mensaje.session_id)
        cerebro.HISTORIAL_SESION[:] = [item for u,a in turnos[-6:] if not a.startswith(('Encontré estos archivos por nombre:', 'No encontré coincidencias por nombre', 'Vista previa local:', 'Acción local ejecutada:')) for item in ({'role':'user','content':u},{'role':'assistant','content':a})]
        comando = False
        action=None;sources=None;tool_mode=None
        group_intent=group_actions.intent(texto)
        file_query=file_actions.intent(texto,turnos)
        desktop_intent=desktop_actions.intent(texto)
        web_route=web_actions.route(texto)
        web_query=web_route['query'] if web_route else None
        if group_intent:
            comando=True;web_query=None
            if PUBLICO or os.getenv('GHOST_ENABLE_SKILLS','0')!='1':
                respuesta='Activa las acciones locales en «Skills y permisos» para preparar una carpeta con los resultados de búsqueda.'
            else:
                try:
                    manager=group_actions.GroupActions(cerebro.BASE_DATOS)
                    action=manager.undo_plan(mensaje.session_id) if group_intent=='undo' else manager.plan(mensaje.session_id,os.getenv('GHOST_DESKTOP_ROOT',str(Path.home()/'Desktop')))
                    respuesta='Vista previa local: revisa los archivos y confirma los movimientos. Todavía no he movido nada. Solo se incluyen los resultados de la última búsqueda de esta conversación.'
                except (ValueError,FileNotFoundError,PermissionError,OSError) as error:
                    respuesta=str(error) if isinstance(error,ValueError) else 'No pude preparar la carpeta. Revisa los permisos locales y vuelve a buscar los archivos.'
        elif file_query is not None:
            comando=True
            web_query=None
            if PUBLICO or os.getenv('GHOST_ENABLE_SKILLS','0')!='1':
                respuesta='Puedo buscar archivos por nombre. Activa las acciones locales en «Skills y permisos»; la búsqueda queda limitada a Escritorio, Descargas, Documentos, Música, Imágenes y Películas (o la carpeta configurada).'
            elif not file_query:
                respuesta=file_actions.PROMPT
            elif not mensaje.confirmar_skill:
                return {'requiere_confirmacion':True,'respuesta':'Confirma la búsqueda local por nombre. No abriré ni modificaré archivos.','popup':None}
            else:
                found=[]
                respuesta=file_actions.search(file_query,capture=found)
                group_actions.GroupActions(cerebro.BASE_DATOS).remember(mensaje.session_id,found)
        elif desktop_intent:
            comando=True
            if PUBLICO or os.getenv('GHOST_ENABLE_SKILLS','0')!='1':
                respuesta='Todavía no he movido archivos. Activa las skills locales en Ajustes de IA para revisar un plan de organización del Escritorio antes de confirmarlo.'
            else:
                try:
                    manager=desktop_actions.DesktopActions(os.getenv('GHOST_DESKTOP_ROOT',str(Path.home()/'Desktop')),cerebro.BASE_DATOS)
                    action=manager.undo_plan(mensaje.session_id) if desktop_intent=='undo' else manager.plan(mensaje.session_id)
                    respuesta=('Preparé la vista previa local. Revisa los movimientos y confirma con el botón; todavía no se ha modificado ningún archivo.' if action['count'] else 'No encontré archivos sueltos para organizar. No moví nada.')
                except (PermissionError,FileNotFoundError):
                    respuesta='No pude leer el Escritorio. Concede al Núcleo permiso de acceso a esa carpeta en Ajustes del Sistema. No moví archivos.'
                except ValueError as error:
                    respuesta=str(error)
        elif web_query:
            comando=True
            if PUBLICO or os.getenv('GHOST_ENABLE_WEB','1')!='1':
                respuesta='La búsqueda web está apagada. Actívala en Ajustes de IA. No he consultado internet.'
            else:
                try:
                    sources=web_actions.search(web_query)
                    respuesta='Fuentes relacionadas con tu búsqueda (extractos del buscador):\n\n'+'\n\n'.join(f"{i}. {r['title']}\n{r['body']}" for i,r in enumerate(sources,1)) if sources else 'La búsqueda no devolvió resultados. No voy a inventar fuentes.'
                except Exception:
                    respuesta='No pude obtener fuentes relacionadas con esa consulta después de probar varios buscadores. Puedes reintentar; no voy a inventar resultados.'
        elif skills_mac.es_skill(texto):
            comando = True
            if not PUBLICO and os.getenv('GHOST_ENABLE_SKILLS','0') == '1' and not mensaje.confirmar_skill and not skills_mac.es_accion_app(texto):
                return {'requiere_confirmacion':True, 'respuesta':'Esta acción usa tu Mac. Confirma para ejecutarla.', 'popup':None}
            respuesta = skills_mac.ejecutar_skill(texto, autorizado=mensaje.confirmar_skill)
        elif bajo == 'ver memoria':
            comando = True
            partes = []
            for titulo,archivo in [('SOBRE TI',cerebro.ARCHIVO_MEMORIA_USUARIO),('SOBRE EL NÚCLEO',cerebro.ARCHIVO_CORE_MEMORY)]:
                partes.append(titulo + '\n' + ('\n'.join(f'{i}. [{m["categoria"]}] {m["dato"]}' for i,m in enumerate(cerebro.cargar_lista(archivo),1)) or '(vacío)'))
            respuesta = '\n\n'.join(partes)
        elif bajo.startswith('olvidar '):
            comando = True
            partes = bajo.split()
            if len(partes)!=3 or partes[1] not in ('tu','tú','usuario','ghost','nucleo','núcleo') or not partes[2].isdigit():
                respuesta = 'Usa: olvidar tu 1 | olvidar nucleo 1. Revisa antes «ver memoria».'
            else:
                archivo = cerebro.ARCHIVO_CORE_MEMORY if partes[1] in ('ghost','nucleo','núcleo') else cerebro.ARCHIVO_MEMORIA_USUARIO
                items = cerebro.cargar_lista(archivo)
                idx = int(partes[2])-1
                if not 0 <= idx < len(items): respuesta = 'Ese recuerdo no existe.'
                else:
                    items.pop(idx)
                    if not cerebro.guardar_json(archivo,items): raise OSError('memoria')
                    respuesta = 'Recuerdo eliminado.'
        elif bajo.startswith(('asi:','así:')):
            comando = True
            previo = next((u for u,a in reversed(turnos) if not u.lower().startswith(('asi:','así:','olvidar ')) and u.lower() != 'ver memoria' and not skills_mac.es_skill(u)),None)
            correccion = texto.split(':',1)[1].strip()
            respuesta = 'Envía primero un mensaje normal y después «así: respuesta corregida».'
            if previo and correccion:
                if not cerebro.guardar_ejemplo_core(previo,correccion): raise OSError('ejemplo')
                respuesta = 'Ejemplo de estilo guardado. Lo usaré en las próximas respuestas.'
        else:
            anterior = cerebro.MODELO_LLM
            try:
                cerebro.MODELO_LLM = mensaje.modelo or anterior
                tools=agent_tools.available(local=not PUBLICO,skills=os.getenv('GHOST_ENABLE_SKILLS','0')=='1',web=os.getenv('GHOST_ENABLE_WEB','1')=='1',text=texto)
                try:
                    with agent_tools.scope(tools) as tool_state:
                        respuesta=cerebro.responder_chat(texto)
                    tool_mode=tool_state['mode']
                except agent_tools.ToolSelected as selected:
                    return selected_tool(selected.call,mensaje)
                except agent_tools.InvalidTool as invalid:
                    comando=True;respuesta=str(invalid)
            finally:
                cerebro.MODELO_LLM = anterior
        with database() as con:
            con.execute('INSERT INTO turns(session,user,answer) VALUES(?,?,?)',(mensaje.session_id,texto,respuesta))
        advertencia = ('Este modelo no admite selección de herramientas. Puedes usar los comandos directos del Núcleo, como «busca el archivo informe» u «organiza esos archivos en una carpeta».' if tool_mode=='compatibility' else None)
        if not comando:
            try:
                cerebro.registrar_turno(texto,respuesta)
                if os.getenv('GHOST_LEARNING','1') == '1': cerebro.procesar_aprendizaje(texto)
            except Exception:
                advertencia = 'Respuesta guardada; no se pudo completar el aprendizaje o registro auxiliar.'
        return {'respuesta':respuesta,'popup':None,'advertencia':advertencia,'accion':action,'fuentes':sources,'busqueda':web_route if web_query else None}
    except licensing.LicenseRequired as error:
        raise HTTPException(402,str(error))
    except HTTPException:
        raise
    except (httpx.HTTPError, ollama.ResponseError, ConnectionError):
        raise HTTPException(503,'No pude conectar con el proveedor o cargar el modelo. Revisa URL, clave, modelo y saldo de tu servicio.')
    except Exception:
        raise HTTPException(500,'No se pudo completar la operación. Revisa permisos de datos y registros del servidor.')
    finally:
        LOCK.release()

class ActionRequest(BaseModel):
    plan_id: str
    session_id: str
    confirmar: bool = False

@app.post('/api/actions/execute')
def ejecutar_plan(payload: ActionRequest):
    if PUBLICO or os.getenv('GHOST_ENABLE_SKILLS','0')!='1':raise HTTPException(403,'Skills locales desactivadas.')
    if not payload.confirmar:raise HTTPException(400,'Confirma la vista previa antes de mover archivos.')
    try:
        session=str(UUID(payload.session_id));UUID(payload.plan_id)
    except ValueError:raise HTTPException(422,'Identificador inválido.')
    if not LOCK.acquire(blocking=False):raise HTTPException(409,'Espera a que termine la operación actual.')
    try:
        manager=group_actions.GroupActions(cerebro.BASE_DATOS)
        try:manager.read(payload.plan_id)
        except FileNotFoundError:manager=desktop_actions.DesktopActions(os.getenv('GHOST_DESKTOP_ROOT',str(Path.home()/'Desktop')),cerebro.BASE_DATOS)
        result=manager.execute(payload.plan_id,session)
        verb='restaurados' if result['undo'] else 'organizados'
        answer=f"Acción local ejecutada: {result['moved']} archivos {verb}."
        if result['failed']:answer+=f" {len(result['failed'])} archivos no se movieron por cambios, conflictos o permisos."
        if not result['undo'] and result['moved']:answer+=(' Puedes pedir «deshacer agrupación de archivos».' if result.get('group') else ' Puedes pedir «deshacer organización del escritorio».')
        with database() as con:con.execute('INSERT INTO turns(session,user,answer) VALUES(?,?,?)',(session,'[Confirmación de acción local]',answer))
        return {'respuesta':answer,'resultado':result}
    except (ValueError,FileNotFoundError):raise HTTPException(409,'El plan ya no es válido o los archivos cambiaron. Solicita una vista previa nueva.')
    except PermissionError:raise HTTPException(403,'macOS no permitió acceder al Escritorio. No se pudo completar la acción.')
    finally:LOCK.release()

class AudioRequest(BaseModel):
    audio: str = Field(max_length=6_700_000)
    mime: str = Field(max_length=100)
    consent: bool = False
    wake: bool = False

class LocalVoiceInstall(BaseModel):
    consent: bool = False

def require_local_voice():
    if PUBLICO or os.getenv('GHOST_ENABLE_MIC','0')!='1':
        raise HTTPException(403,'Activa el micrófono en Ajustes de IA.')

@app.get('/api/voice/local/status')
def local_voice_status():
    require_local_voice()
    return {**local_voice.status(),'wake_ready':wake_voice.available()}

@app.post('/api/voice/local/install')
def install_local_voice(payload: LocalVoiceInstall):
    require_local_voice()
    if not payload.consent:raise HTTPException(400,'Confirma la descarga del modelo de voz.')
    try:return local_voice.start_download()
    except ValueError as error:raise HTTPException(400,str(error))

@app.post('/api/voice/local/cancel')
def cancel_local_voice():
    require_local_voice()
    return local_voice.cancel_download()

@app.post('/api/voice/local/transcribe')
def transcribir_voz_local(payload: AudioRequest):
    require_local_voice()
    if not payload.consent:raise HTTPException(400,'Activa la escucha local antes de transcribir.')
    import base64
    try:
        audio=base64.b64decode(payload.audio,validate=True)
        if not audio or len(audio)>5_000_000:raise ValueError('La grabación supera el tamaño permitido.')
        if payload.mime.split(';',1)[0]!='audio/wav':raise ValueError('La escucha local requiere audio WAV.')
        woke,command=wake_voice.detect(audio)
        if woke:return {'wake':True,'texto':skills_mac.normalizar_comando_voz(local_voice.transcribe(command,'audio/wav')) if command else ''}
        if payload.wake:return {'wake':False,'texto':''}
        return {'wake':False,'texto':skills_mac.normalizar_comando_voz(local_voice.transcribe(audio,'audio/wav'))}
    except ValueError as error:
        if str(error).startswith('No detecté una frase'):return {'texto':''}
        raise HTTPException(400,str(error))

@app.post('/api/voice/local/release')
def liberar_detector_local():
    if PUBLICO:raise HTTPException(403,'Solo disponible en modo local.')
    wake_voice.release()
    return {'ok':True}

@app.post('/api/voice/transcribe')
def transcribir_audio(payload: AudioRequest):
    if PUBLICO or os.getenv('GHOST_ENABLE_MIC','0')!='1':raise HTTPException(403,'Activa el dictado por micrófono en Ajustes de IA.')
    if not payload.consent:raise HTTPException(400,'Confirma el uso del micrófono para transcribir.')
    try:return {'texto':voice_actions.transcribe(payload.audio,payload.mime)}
    except ValueError as error:raise HTTPException(400,str(error))
    except httpx.HTTPError:raise HTTPException(503,'No se pudo transcribir con tu proveedor. Revisa modelo, clave, cuota y compatibilidad de audio.')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=BIND, port=int(os.getenv('GHOST_PORT','8000')), proxy_headers=False, workers=1)
