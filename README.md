# Enjambre de Vóxeles 0.7.3 (Multiplataforma: macOS, Windows, Linux)

Enjambre de Vóxeles es un asistente de escritorio con interfaz de overlay transparente, avatar vectorial interactivo («núcleo holográfico»), chat compacto desplegable, activación por voz local («Oye Vox»), herramientas de sistema con adaptadores multiplataforma y soporte de modelos locales (Ollama) y en la nube (Google Gemini y APIs compatibles).

---

## 🚀 Arquitectura y Estado Multiplataforma

La aplicación se compone de:
1. **Frontend / Overlay (Electron)**: Ventana transparente flotante con hit-testing poligonal/circular, bandeja del sistema, menú contextual, atajos globales y burbuja de chat a demanda.
2. **Backend (Python / FastAPI)**: Servicio loopback autenticado con token efímero que gestiona el cerebro, memoria episódica/estilo, ejecución restringida de herramientas (`tool_runtime.py`) y llamadas a proveedores.
3. **Motores de Voz Locales**:
   - **Oye Vox (Vosk 0.3.44 C API)**: Detección continua de palabra clave local en segundo plano en español (`vosk-model-small-es-0.42`), sin enviar audio a la nube.
   - **Transcripción Local (whisper.cpp v1.9.5)**: Binario estático compilado con CMake (`whisper-cli` / `whisper-cli.exe`), mono 16 kHz.

---

## 📊 Matriz de Compatibilidad de Funciones

| Función / Característica | macOS (arm64 / x64) | Windows 10/11 (x64) | Linux (X11) | Linux (Wayland / XWayland) | Estado y Notas |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Avatar Vóxel & Skins** | ✅ Probado | ✅ Compatible | ✅ Compatible | ✅ Compatible | SVG/CSS animado, sin dependencias de plataforma. |
| **Burbuja de Chat Redimensionable** | ✅ Probado | ✅ Compatible | ✅ Compatible | ⚠️ Notas | Funciona sobre XWayland. En Wayland puro el posicionamiento libre depende del compositor. |
| **Transparencia y Click-Through** | ✅ Probado | ✅ Compatible | ✅ Compatible | ⚠️ Notas | `setIgnoreMouseEvents({forward: true})` soportado en macOS, Win32 y X11/XWayland. |
| **Detección «Oye Vox» (Segundo Plano)** | ✅ Probado | ✅ Probado (DLLs listas) | ✅ Probado (libvosk.so) | ✅ Compatible | Funciona con burbuja cerrada, indicador visual en bandeja/menú y opción de silenciar. |
| **Dictado Local (whisper.cpp)** | ✅ Probado | ✅ Compatible | ✅ Compatible | ✅ Compatible | Binario CLI nativo independiente por plataforma. |
| **Apertura de Aplicaciones Autorizadas** | ✅ Probado | ✅ Probado (`Start-Process`) | ✅ Probado (`gtk-launch` / `gio`) | ✅ Compatible | Exclusivo para apps aprobadas por el usuario; no ejecuta comandos arbitrarios. |
| **Cierre Normal de Aplicaciones** | ✅ Probado (Apple Events) | ✅ Probado (`.CloseMainWindow()`) | ✅ Probado (`wmctrl -c` / `pkill -15`) | ⚠️ Limitado | Solicita cierre cortés respetando avisos de cambios sin guardar. No usa `SIGKILL` ni `taskkill /F`. En Wayland puro sin X11/wmctrl, informa limitación del compositor. |
| **Búsqueda y Organización de Archivos** | ✅ Probado | ✅ Probado | ✅ Probado | ✅ Compatible | Previsualización, confirmación explícita y deshacer; restringido a carpetas autorizadas. |
| **Síntesis de Voz Nativa** | ✅ Probado (`/usr/bin/say`) | ✅ Probado (PowerShell SAPI) | ✅ Probado (`spd-say` / `espeak`) | ✅ Compatible | Ejecución segura por stdin / argumentos desinfectados. |
| **Control de Apple Music / Música** | ❌ Retirado | ❌ No soportado | ❌ No soportado | ❌ No soportado | Retirado en v0.7.3. No disponible ni anunciado en ninguna plataforma. |
| **Planes Free / Pro (Licenciamiento)** | ✅ Probado | ✅ Probado | ✅ Probado | ✅ Probado | Verificación criptográfica Ed25519 unificada en Node y Python. |

---

## 🪟 Consideraciones Linux: X11 frente a Wayland

1. **Overlay Transparente y Passthrough de Clics**:
   - En **X11 y XWayland** (modo por defecto de Electron), las propiedades de ventana transparente (`transparent: true`), ventana flotante (`alwaysOnTop: true`) y passthrough de ratón (`setIgnoreMouseEvents`) funcionan con normalidad.
   - En **Wayland nativo** (`--ozone-platform=wayland`), el protocolo Wayland no permite a un cliente posicionarse libremente en coordenadas absolutas de pantalla ni omitir eventos de entrada de forma arbitraria por razones de seguridad. Se recomienda ejecutar el paquete bajo XWayland.
2. **Atajos Globales**:
   - X11 permite el registro directo mediante `globalShortcut`. En entornos Wayland puros, los atajos globales están delegados al portal XDG Desktop Portal (`org.freedesktop.portal.GlobalShortcuts`).
3. **Cierre Cortés de Aplicaciones**:
   - En X11, `wmctrl -c <nombre>` envía el mensaje cliente EWMH `_NET_CLOSE_WINDOW`, permitiendo a las ventanas solicitar guardar documentos. En ausencia de wmctrl, se envía `SIGTERM` (señal 15) al proceso. En Wayland puro, los clientes no pueden controlar ventanas de otros clientes; el sistema informa educadamente la limitación en lugar de forzar terminaciones.

---

## 🔒 Modelo de Seguridad y Licenciamiento (Free / Pro)

Enjambre de Vóxeles opera con una única aplicación e instalador por plataforma:
- **Plan Free (Sin Licencia)**:
  - **Ollama Local**: `http://localhost:11434` o `http://127.0.0.1:11434` (sin rutas ajenas ni credenciales en URL).
  - **Google Gemini Oficial**: Endpoint oficial HTTPS exacto `https://generativelanguage.googleapis.com/v1beta/openai` (puerto 443).
  - Todas las herramientas locales (Oye Vox, Whisper, memoria, apertura/cierre de apps autorizadas, organización de archivos con confirmación y deshacer).
- **Plan Pro (Activación Beta Firmada)**:
  - Acceso a servidores Ollama remotos, OpenAI, Anthropic, DeepSeek, Groq, Mistral y endpoints personalizados compatibles con OpenAI Chat Completions.
  - El usuario aporta siempre sus propias claves API; no se incluyen créditos de IA.
  - Verificación offline mediante token firmado Ed25519 (`payload.signature`). Clave pública compartida en `commercial/license-public-key.json`. El backend Python valida la firma (`GHOST_LICENSE_ENFORCE=1`) devolviendo HTTP 402 si se intenta usar un proveedor Pro sin activación válida.

---

## 🛠️ Instrucciones de Desarrollo y Compilación

### Requisitos Previos Comunes
- **Node.js**: v20+ LTS y `npm`.
- **Python**: 3.12 o posterior.
- **CMake**: Requerido si se recompila `whisper.cpp`.

---

### Preparación del Entorno (macOS / Linux / Windows)

1. **Clonar y preparar entorno virtual**:
   ```bash
   # En macOS / Linux:
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # En Windows (PowerShell):
   py -3 -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Preparar Motores de Voz (Vosk y Whisper)**:
   ```bash
   # Descarga las bibliotecas Vosk correspondientes y el modelo de español:
   python desktop/prepare_wake.py --all

   # Opcional: compilar whisper.cpp para la plataforma local (requiere CMake):
   python desktop/prepare_voice.py
   ```

3. **Empaquetar el Backend Python (PyInstaller)**:
   ```bash
   python desktop/prepare_backend.py
   ```

4. **Instalar Dependencias de Electron y Probar**:
   ```bash
   cd desktop
   npm ci
   npm run setup-electron
   npm start
   ```

5. **Construir Paquetes de Distribución**:
   ```bash
   # Desde la raíz del proyecto:
   python desktop/build_overlay.py dist

   # O desde la carpeta desktop:
   cd desktop
   npm run dist
   ```

Los artefactos empaquetados se generan en `desktop/release/`:
- **macOS**: `Enjambre de Voxeles-0.7.3-arm64-mac.zip`
- **Windows**: `VoxelSwarm-0.7.3-win.exe` (Portable) y `VoxelSwarm-0.7.3-win.zip`
- **Linux**: `VoxelSwarm-0.7.3.AppImage` y `VoxelSwarm-0.7.3.tar.gz`

---

## 🧪 Verificación y Pruebas

Ejecutar la suite completa de pruebas:
```bash
# Pruebas del backend Python (79 pruebas unitarias y de integración):
.venv/bin/python -m unittest discover -s tests -v

# Pruebas del frontend Electron y políticas (57 pruebas Node):
node --test desktop/*.test.cjs
```

---

## 📄 Licencia y Créditos
- Licencia general: MIT.
- Modelos y motores incluidos: Vosk (Apache 2.0), whisper.cpp (MIT), miniaudio (MIT/Public Domain).


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

Con **Ollama**, activa el micrófono en Skills y permisos y pulsa **Descargar voz local · 148 MB** en el chat. La app incluye whisper.cpp; el modelo Whisper base multilingüe se descarga una vez y se verifica con SHA256. Después, **Conversar por voz** transcribe en este Mac, envía el texto al Ollama configurado y lee la respuesta con las voces del sistema. Para una conversación sin APIs externas, configura Ollama en este equipo. **Terminar voz** o cerrar la burbuja detiene la sesión. Gemini, OpenAI y Groq conservan su transcripción cloud. Consulta [OVERLAY.md](OVERLAY.md#voz-local-con-ollama-067).


Para reconstruir el motor nativo en el SO y arquitectura de destino: `python3 desktop/prepare_voice.py` (requiere CMake; en Mac, Xcode Command Line Tools). Después ejecuta `desktop/prepare_backend.py` con el entorno Python de desarrollo. La app distribuida ya incluye el motor; el usuario no necesita Python, CMake ni ffmpeg. La versión entregada aquí es macOS arm64.


## Elegir aplicaciones permitidas (0.6.9)

Abre **Skills y permisos → Aplicaciones permitidas**, busca y marca las apps instaladas que quieres autorizar, activa **Habilitar acciones del Mac** y pulsa **Guardar y reconectar**. Después puedes escribir o decir «abre Safari», «abre Notas» o «abre VSCode» si están marcadas. Las apps marcadas se abren directamente cuando lo pides, sin repetir la confirmación. Los archivos conservan sus confirmaciones. Puedes desmarcar todas para impedir abrir cualquier app. Cambiar de modelo local/cloud conserva esta selección.


## «Oye Vox» con la burbuja cerrada (0.7.0)

En **Skills y permisos / Ajustes de IA**, activa **Activar «Oye Vox» aunque la burbuja esté cerrada** y guarda. Esta elección habilita el micrófono y se conserva entre inicios. Si falta Whisper local, abre el chat desde el menú del Núcleo y pulsa **Descargar voz local · 148 MB**. El detector español de activación ya viene incluido en esta app; no requiere claves ni instalar paquetes.

Puedes cerrar la burbuja, decir **«Oye Vox»**, esperar el indicador **«Te escucho»** y dar el comando. También reconoce una sola frase como **«Oye Vox, abre Calculadora»**. Abre la burbuja para responder y luego vuelve a esperar la llamada. Para silenciar: pulsa el círculo del Núcleo, elige **Silenciar «Oye Vox»** en su menú o di **«Oye Vox, deja de escuchar»**. Cerrar la burbuja no silencia este modo; salir de la app, bloquear o suspender el Mac sí detiene la captura.

La activación se detecta localmente con Vosk y el comando se transcribe con Whisper. Si usas una API para conversar, recibe el texto del comando, no el audio ambiente. No se guardan grabaciones ni transcripciones de conversaciones de fondo. Es una primera versión: la acústica, el ruido y las voces reales requieren prueba en cada equipo. La app y el Mac deben estar ejecutándose; no despierta un Mac suspendido. La reproducción musical de Apple Music sigue pendiente.

Para reconstruir desde el proyecto editable: además de `desktop/prepare_voice.py`, ejecuta `desktop/prepare_wake.py` antes de `desktop/prepare_backend.py`. El detector macOS universal y el modelo pequeño de español se descargan con hashes fijados. La app entregada es macOS Apple Silicon.

## Apple Music · Vista previa Pro (0.7.1)
En Ajustes, activa las acciones del Mac, marca Música en aplicaciones permitidas y habilita Apple Music en Funciones especiales. Guarda y reconecta. Con «Oye Vox» activado puedes decir «reproduce Rammstein», «pausa la música», «reanuda la música», «siguiente canción» y «canción anterior». También funcionan escritos en el chat con Ollama y APIs; el control se ejecuta en tu Mac.

La búsqueda utiliza la biblioteca de Música; añade antes el artista/canción a ella. No incluye búsqueda en todo el catálogo. Reproduce la primera coincidencia; siguiente/anterior siguen la cola actual de Música. macOS puede pedir permiso de Automatización para controlar Música. No se envía la biblioteca al proveedor. Si la música activa falsos despertares, silencia Oye Vox desde el menú.

### Licencia y monetización
El apartado Funciones especiales describe Free (Ollama local) y Pro previsto (API e integraciones). Esta compilación es una vista previa de desarrollo: no cobra, valida claves ni bloquea funciones por pago. El interruptor Apple Music es un permiso local, no una licencia. No hay precios definitivos. Calendario, recordatorios y mensajería son funciones pendientes.

Antes de vender Pro: definir productos y términos, integrar checkout alojado y portal de cliente, recibir webhooks verificados en servidor, emitir permisos firmados y validarlos también al ejecutar cada función en el backend. No aceptar un booleano del cliente como prueba de pago; mantener los secretos de cobro fuera de la app, prever caducidad, revocación y periodo sin conexión. No restringir instalaciones existentes sin migración y comunicación explícitas. El consumo de APIs y Apple Music se contrata por separado.
