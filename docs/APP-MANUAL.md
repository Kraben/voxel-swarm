# Enjambre de Vóxeles 0.6.0

La identidad visual actual es un enjambre holográfico circular. Las secciones de versiones anteriores se conservan como historial técnico. Consulta REBRANDING.txt para compatibilidad y recursos pendientes.

# Ghost AI para macOS

**Nuevo: [Enjambre de Vóxeles](../OVERLAY.md)** añade la núcleo flotante y una base compartida para macOS, Windows y Linux. La documentación de abajo corresponde a la ventana SwiftUI original.

Primera versión de escritorio: ventana SwiftUI + WKWebView, motor FastAPI/Python incluido y Ollama local o remoto. El avatar Ghost vectorial anima los estados reposo, pensando y hablando sin depender de GIFs externos. Interfaz inspirada en la composición oscura y el protagonismo del personaje de [Troko](https://troko.vercel.app/troko/).

## Abrir la app ya compilada

1. Abre `dist/Ghost AI.app`. Puedes copiarla a Aplicaciones.
2. Mantén Ollama ejecutándose con tu modelo `ghost-heretic` disponible. No hace falta iniciar FastAPI a mano.
3. Escribe un mensaje. Ghost cambia a pensando mientras recibe la respuesta y a hablando mientras la presenta o lee.
4. En el menú **Ghost AI → Ajustes…** (`⌘,`) configura el servidor Ollama, los modelos y las skills. Pulsa **Guardar y reiniciar** para aplicar cambios.

La compilación incluida es para Apple Silicon, construida en este Mac. Es una versión local sin firma Developer ID ni notarización. Para distribuirla a otros Macs hay que firmar también el motor Python y sus bibliotecas y notarizar el conjunto. No está preparada para Mac App Store. Los fuentes Swift apuntan a macOS 14 o posterior; el motor incluido usa el Python y las bibliotecas de este equipo, por lo que no se ha verificado su compatibilidad con otras versiones de macOS.

## Editar con Xcode

Abre `macos/GhostAI.xcodeproj`, elige el esquema **GhostAI**, destino **My Mac** y pulsa ▶. El motor preparado está en `macos/GhostAI/Backend`. Si descargaste el ZIP de fuentes, ejecuta primero `Preparar-motor.command`: ese ZIP excluye los binarios para mantenerlo ligero. El proyecto utiliza el motor empaquetado, no los archivos Python de la raíz directamente.

- Ventana, arranque privado, cierre del motor y ajustes nativos: `macos/GhostAI/GhostAIApp.swift`.
- Composición y avatar vectorial editable: `index.html`.
- Colores, movimiento y diseño adaptable: `static/style.css`.
- Chat, estados, voz y diálogos: `static/app.js`.
- API y restricciones: `servidor.py`.
- Personalidad, recuerdos, correcciones, aprendizaje y consola: `cerebro_ghost.py`.
- Apertura de apps y búsqueda Spotlight: `skills_mac.py`.
- Los cuatro archivos originales se conservan en `originales/`.

Después de editar HTML, CSS, JS o Python, ejecuta **Preparar-motor.command** y vuelve a compilar en Xcode. Después de editar solo Swift, basta con compilar en Xcode.

## Reconstruir la app

Necesitas Xcode, Python 3.12 o posterior y conexión para instalar dependencias desde PyPI. Ollama debe estar instalado por separado. El paquete no incorpora ni descarga pesos de modelos.

Haz doble clic en **Crear-app.command**. Prepara un entorno Python, empaqueta FastAPI y construye `dist/Ghost AI.app`. **Iniciar.command** abre esa app y la construye si falta. Los scripts eligen `/Applications/Xcode.app/Contents/Developer` sin modificar la selección global del equipo. Si Xcode está en otra ubicación, define `DEVELOPER_DIR`.

También puedes hacerlo desde Terminal, situado en esta carpeta:

```sh
./Preparar-motor.command
open macos/GhostAI.xcodeproj
# O construir todo:
./Crear-app.command
```

Si prefieres una versión específica de Python para reconstruir, ejecuta `GHOST_PYTHON=/ruta/a/python3.12 ./Preparar-motor.command` antes de que exista `.venv`. Reconstruye para Intel en un Mac Intel con dependencias de esa arquitectura.

## Configuración y memoria

En la app, los datos se guardan en:

```text
~/Library/Application Support/Ghost AI/
  config.json           ajustes privados del usuario (permisos 600)
  server.log            diagnóstico del motor
  data/
    memoria.json
    hechos_ghost.json
    correcciones_ghost.json
    identidad_ghost.json
    ejemplos_ghost.json
    chat.sqlite3        historial por sesión
    conversaciones/     registros compatibles con el cerebro original
```

**Tus JSON anteriores no estaban entre los cuatro adjuntos.** Se conserva su formato y toda la lógica, pero no se han inventado ni importado recuerdos. Para migrarlos: cierra Ghost, haz una copia de seguridad de ambas carpetas y copia tus cinco JSON existentes a la carpeta `data/`. En **Ajustes → Abrir datos** encuentras la carpeta. Si hay archivos con el mismo nombre, conserva una copia antes de sustituirlos. Reinicia la app. Los registros viejos de `conversaciones/` se pueden conservar, aunque no se importan automáticamente a SQLite ni al contexto de la sesión.

La app conserva el identificador de la conversación entre arranques, independientemente del puerto privado. La memoria personal es compartida por las conversaciones del propietario. El historial de contexto es independiente por sesión. **Nueva conversación** crea una sesión nueva; no borra registros ni recuerdos. Se restauran los últimos doce turnos de la sesión y se usan los últimos seis para el contexto.

Comandos conservados:

- `ver memoria`: muestra los recuerdos numerados. También existe el botón **Memoria**.
- `olvidar tu 1` / `olvidar ghost 1`: elimina el recuerdo indicado.
- `así: respuesta corregida`: enseña el estilo para el último mensaje normal de esa sesión. Los ejemplos ahora se incluyen en el prompt.

Las escrituras JSON usan reemplazo atómico. Un único worker y un bloqueo protegen el estado heredado del cerebro frente a solicitudes simultáneas. El historial se guarda en SQLite y no se registra una respuesta fallida de Ollama como si fuera válida. Cuando el motor está ocupado, el segundo envío recibe una indicación para esperar.

## Ollama local o remoto

En la app usa **Ajustes**:

- Local: `http://127.0.0.1:11434`, modelo `ghost-heretic` (o el nombre exacto que muestre tu Ollama).
- Remoto: origen HTTPS del servidor Ollama, sin `/api`, parámetros ni credenciales en la URL. Añade la clave API si tu servicio la requiere. Para un servidor privado sin HTTPS utiliza un túnel SSH y configura un puerto local.
- Modelo de memoria: debe existir en ese mismo servidor. Puede ser el mismo que el del chat.

La clave de Ollama queda en la configuración privada del Mac y se envía al motor por el entorno del proceso; no llega al JavaScript. Con Ollama remoto se transmiten los mensajes, el contexto y los recuerdos incluidos en el prompt. [Ollama documenta la autenticación local y mediante Bearer para su servicio remoto](https://docs.ollama.com/api/authentication).

La voz utiliza la síntesis disponible en WKWebView y las voces del sistema. Es opcional; no activa el micrófono ni depende de VoiceStudio. Se eliminó la reproducción automática en el altavoz del servidor. La búsqueda web heredada se conserva, pero requiere instalar `ddgs` y habilitar `GHOST_WEB_SEARCH=1` en el modo web; el lanzador macOS la mantiene apagada.

## Skills del Mac

Están apagadas al instalar. Para usarlas, habilita **Permitir acciones locales con confirmación** en Ajustes y guarda. Cada comando detectado muestra primero un diálogo con el texto exacto de la acción.

- `abre calculator`: solo abre nombres exactos de la lista permitida, separados por coma y en minúsculas. Se mantienen alias como `vscode` → `visual studio code`; el nombre final debe figurar en la lista.
- `busca el archivo informe`: usa Spotlight solo dentro de la carpeta configurada y devuelve hasta tres rutas relativas. Puede requerir permisos normales de macOS sobre esa carpeta.

No hay ejecución de shell ni instrucciones arbitrarias generadas por el modelo. Solo los prefijos escritos por el usuario activan skills. No ejecutes esta versión de propietario único como servicio multiusuario. Un token válido representa al propietario; la confirmación de la interfaz es una protección contra acciones accidentales, no un segundo factor frente a alguien que ya posea el token.

## Uso web opcional / publicación futura

La prioridad es la app macOS. También se puede ejecutar el mismo motor en el navegador:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python servidor.py
```

Abre `http://127.0.0.1:8000`. Edita `.env` para elegir Ollama y los límites. La app nativa utiliza sus Ajustes, no el `.env` de esta carpeta. El lanzador nativo elige un puerto de loopback libre y un token aleatorio distinto en cada arranque; cierra su motor al salir. No modifica ni detiene tu Ollama.

En web, **Conexión** acepta el origen del backend y su token. Estos valores no se guardan permanentemente en el navegador. El destino de Ollama se controla en el servidor para evitar un proxy arbitrario. Para servir la interfaz en otro origen, configura también `GHOST_ALLOWED_ORIGINS`. Un sitio HTTPS necesita un backend HTTPS.

Para un despliegue externo, `GHOST_PUBLIC=1` obliga a usar token de al menos 32 caracteres, hosts explícitos y orígenes HTTPS. Las skills se bloquean aunque `GHOST_ENABLE_SKILLS=1`. Usa un proxy HTTPS, `GHOST_BIND=0.0.0.0`, un único worker y desactiva el aprendizaje si no necesitas memoria personal. Esta base sigue siendo para un propietario: autenticación multiusuario, aislamiento por usuario y cuotas distribuidas requieren trabajo adicional. No se ha publicado ningún servicio.

API: `GET /api/status`, `GET /api/memory`, `GET /api/history/{uuid}`, `POST /chat` (alias `/api/chat`). El POST recibe `texto`, `session_id`, `modelo` opcional y `confirmar_skill` opcional. Se mantienen `respuesta` y `popup` para compatibilidad; la interfaz nueva presenta memoria sin ventanas alert.

## Verificación

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Las pruebas usan memoria temporal y no abren apps. Cubren acceso, origen, tamaño de petición, sesiones, memoria, ejemplos de estilo, errores de Ollama, concurrencia, límite de frecuencia y bloqueo/confirmación de skills. La compilación, el motor empaquetado y una conversación real con `ghost-heretic` se comprobaron en este Mac. No se verificó un proveedor Ollama remoto ni firma/notarización de distribución.

## Siguiente etapa posible

Modo Ghost flotante sobre el escritorio: núcleo visual sin fondo en una ventana transparente, arrastrable, opcionalmente encima de otras ventanas y con opción de ignorar clics. Un clic abriría el chat. Esta primera versión entrega la ventana completa; el overlay queda para una iteración posterior.

## Voz continua y transcripción local (0.6.7)

Con **Ollama**, activa el micrófono en Skills y permisos y pulsa **Descargar voz local · 148 MB** en el chat. La app incluye whisper.cpp; el modelo Whisper base multilingüe se descarga una vez y se verifica con SHA256. Después, **Conversar por voz** transcribe en este Mac, envía el texto al Ollama configurado y lee la respuesta con las voces del sistema. Para una conversación sin APIs externas, configura Ollama en este equipo. **Terminar voz** o cerrar la burbuja detiene la sesión. Gemini, OpenAI y Groq conservan su transcripción cloud. Consulta [OVERLAY.md](../OVERLAY.md#voz-local-con-ollama-067).


Para reconstruir el motor nativo en el SO y arquitectura de destino: `python3 desktop/prepare_voice.py` (requiere CMake; en Mac, Xcode Command Line Tools). Después ejecuta `desktop/prepare_backend.py` con el entorno Python de desarrollo. La app distribuida ya incluye el motor; el usuario no necesita Python, CMake ni ffmpeg. La versión entregada aquí es macOS arm64.


## Elegir aplicaciones permitidas (0.6.9)

Abre **Skills y permisos → Aplicaciones permitidas**, busca y marca las apps instaladas que quieres autorizar, activa **Habilitar acciones del Mac** y pulsa **Guardar y reconectar**. Después puedes escribir o decir «abre Safari», «abre Notas» o «abre VSCode» si están marcadas. Las apps marcadas se abren directamente cuando lo pides, sin repetir la confirmación. Los archivos conservan sus confirmaciones. Puedes desmarcar todas para impedir abrir cualquier app. Cambiar de modelo local/cloud conserva esta selección.


## «Oye Vox» con la burbuja cerrada (0.7.0)

En **Skills y permisos / Ajustes de IA**, activa **Activar «Oye Vox» aunque la burbuja esté cerrada** y guarda. Esta elección habilita el micrófono y se conserva entre inicios. Si falta Whisper local, abre el chat desde el menú del Núcleo y pulsa **Descargar voz local · 148 MB**. El detector español de activación ya viene incluido en esta app; no requiere claves ni instalar paquetes.

Puedes cerrar la burbuja, decir **«Oye Vox»**, esperar el indicador **«Te escucho»** y dar el comando. También reconoce una sola frase como **«Oye Vox, abre Calculadora»**. Abre la burbuja para responder y luego vuelve a esperar la llamada. Para silenciar: pulsa el círculo del Núcleo, elige **Silenciar «Oye Vox»** en su menú o di **«Oye Vox, deja de escuchar»**. Cerrar la burbuja no silencia este modo; salir de la app, bloquear o suspender el Mac sí detiene la captura.

La activación se detecta localmente con Vosk y el comando se transcribe con Whisper. Si usas una API para conversar, recibe el texto del comando, no el audio ambiente. No se guardan grabaciones ni transcripciones de conversaciones de fondo. Es una primera versión: la acústica, el ruido y las voces reales requieren prueba en cada equipo. La app y el Mac deben estar ejecutándose; no despierta un Mac suspendido. La reproducción musical de Apple Music sigue pendiente.

Para reconstruir desde el proyecto editable: además de `desktop/prepare_voice.py`, ejecuta `desktop/prepare_wake.py` antes de `desktop/prepare_backend.py`. El detector macOS universal y el modelo pequeño de español se descargan con hashes fijados. La app entregada es macOS Apple Silicon.

## Abrir y cerrar apps autorizadas (0.7.3)

En Ajustes, marca las aplicaciones permitidas y habilita las acciones locales. Puedes decir «Oye Vox, abre Notas» y «Oye Vox, cierra Notas», o escribirlo en el chat. Se solicita un cierre normal: si hay documentos sin guardar, la app puede pedir una decisión. No se fuerza el cierre ni se descartan cambios. macOS puede solicitar permiso de Automatización para enviar el cierre. Las respuestas no afirman que una app esté cerrada si sigue abierta.

El control del contenido de aplicaciones y la reproducción musical se retiraron de la versión activa. Los experimentos de Música y MusicKit permanecen archivados para más adelante. Las herramientas de búsqueda y organización de archivos conservan sus permisos y confirmaciones.

### Licencia y monetización · 0.7.3

Una sola app: Free incluye Ollama local y Gemini con clave propia. Pro habilita los demás proveedores y servidores compatibles. Modelos sin restricción adicional por nombre. Memoria, voz local y herramientas básicas se conservan en Free. Abrir y cerrar apps autorizadas no requiere Pro. El consumo de IA pertenece a cada cuenta del usuario.

Esta beta incluye comprobación de acceso en Electron y backend, y activaciones Pro firmadas manuales desde Ajustes. El cobro automático, límites de dispositivos, revocación online y autoactualizaciones no están implementados. Sigue [commercial/README.md](../commercial/README.md) para alcance, emisor y distribución. La directriz para el port está en commercial/PORT-WINDOWS-LINUX-FREE-PRO.txt.

MusicKit permanece archivado fuera de la línea activa. La 0.7.3 actual conserva Free/Pro y retira el control de Música. La app macOS aún no está firmada con Developer ID ni notarizada.
