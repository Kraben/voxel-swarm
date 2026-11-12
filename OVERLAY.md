# Enjambre de Vóxeles 0.6.0

La identidad visual actual es un enjambre holográfico circular. Las secciones de versiones anteriores se conservan como historial técnico. Consulta REBRANDING.txt para compatibilidad y recursos pendientes.

# Enjambre de Vóxeles · escritorio primero, Maker después

Esta versión añade una app independiente de la ventana SwiftUI anterior. El overlay utiliza Electron para compartir la ventana transparente, las animaciones y el chat entre macOS, Windows y Linux. Mantiene el motor FastAPI, la personalidad y el formato de memoria de Ghost. La app anterior de Xcode sigue en el proyecto.

## Qué hace

- Muestra la núcleo de vóxeles animada, sin marco ni fondo visible.
- El chat del overlay no carga la página «Hola, Guardián», ni una segunda núcleo visual, ni sus animaciones. La página grande se conserva solo para el modo web o la app SwiftUI anterior.
- Arrastra las piezas exteriores para moverla. Haz clic en el ojo para abrir el chat.
- Pensando y hablando se sincronizan con el chat; el chat compacto se crea solo al abrirlo y se destruye al cerrarlo; Ghost sigue en el escritorio. Si hay una respuesta en curso, se oculta hasta terminar de guardarla y entonces se libera.
- Al acercar el puntero aparecen el estado y el botón **⋯**. El menú ofrece tamaño, siempre encima, ignorar clics, mostrar/ocultar y recuperación de posición.
- El fondo transparente deja pasar los clics. La zona interactiva aproxima la forma de la núcleo visual con margen para la animación; no es una máscara exacta de cada píxel.
- **⌘/Ctrl + Mayús + G** muestra Ghost y desactiva el modo ignorar clics. También puedes recuperarlo desde la barra de menú/bandeja. Si el sistema impide registrar el atajo, la app avisa.
- Guarda posición, tamaño y sesión. Si se desconecta un monitor, intenta colocar Ghost dentro de un área visible.
- El motor escucha solo en loopback y usa un token efímero. El renderer tiene aislamiento, acceso a Node desactivado, permisos bloqueados y navegación limitada al servidor privado.

El overlay usa la misma memoria personal de la app original. Se recomienda cerrar la app SwiftUI anterior mientras se utiliza el overlay para que un solo motor gestione los mismos archivos. **Salir de Ghost** termina únicamente el servidor privado de esta app, no Ollama.

## Abrir en Mac

Descomprime `Ghost-Overlay-macOS.zip` y abre **Enjambre de Vóxeles.app**. Es una compilación local para Apple Silicon, sin firma Developer ID ni notarización. No se ha instalado en Aplicaciones ni modificado la app anterior.

Ollama debe estar encendido; se utiliza `ghost-heretic` de forma predeterminada o la configuración existente. Desde **⋯ → Ajustes de IA…** puedes cambiar el origen de Ollama, el modelo de chat, el modelo de memoria y la clave remota. Una dirección remota requiere HTTPS; también puedes usar un túnel local. Desde la versión 0.3.0 el asistente de primer inicio permite elegir un modelo instalado, descargar uno en Ollama local o configurar Ollama remoto / una API compatible con OpenAI (Chat Completions).

Si no hay enlace con Ollama, la núcleo visual puede mostrarse igualmente. El chat explica el problema de conexión. No descarga modelos sin pulsar explícitamente «Descargar este modelo».

La configuración, memoria e historial se guardan en la carpeta del usuario **Ghost AI** dentro de Application Support (Mac), AppData/Roaming (Windows) o la carpeta de configuración de aplicaciones de Linux. Ajustes usa `config.json`, compatible con la app Mac anterior. `overlay.json` guarda la posición y sesión; `overlay-server.log` contiene diagnóstico. La clave se mantiene en la configuración privada del usuario y no se devuelve al formulario de ajustes.

Las skills actuales son de macOS y están apagadas por defecto. En Windows y Linux quedan bloqueadas, aunque el chat y el avatar pueden utilizarse. El botón de confirmación por acción se mantiene en Mac. No añadas herramientas de shell a un servidor público.

## Editar y construir

Archivos principales:

- `desktop/main.cjs`: ventanas, bandeja, menú, hit testing, servidor privado, sesión y cierre.
- `desktop/preload.cjs`: puente mínimo entre la interfaz y la app.
- `desktop/policy.cjs`: validación de configuración y zonas de interacción.
- `static/overlay.html`, `overlay.css`, `overlay.js`: núcleo visual, transparencia y estados.
- `static/compact-chat.html`, `compact-chat.css`: conversación compacta sin avatar duplicado.
- `static/app.js`: chat y envío de estados al overlay.
- `static/desktop-settings.*`: formulario de ajustes propio del overlay.
- `desktop/prepare_backend.py`: empaqueta el motor Python del sistema actual.

Para construir en Mac puedes ejecutar **Crear-overlay.command**. Para cualquier SO necesitas Node.js con npm, Python 3.12 o posterior y las dependencias de compilación que solicite PyInstaller en ese sistema. Desde la raíz del proyecto:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-mac.txt
.venv/bin/python desktop/build_overlay.py
```

En Windows, las dos últimas rutas son `.venv\Scripts\python.exe` y puedes usar `py -3 -m venv .venv` para crear el entorno. `requirements-mac.txt` contiene las dependencias Python y PyInstaller; el nombre es heredado, sus dependencias son compartidas.

El script prepara el motor, instala las dependencias de npm con el archivo de versiones y crea la aplicación sin instalador en `desktop/release/`. Para desarrollo, después de preparar el motor:

```sh
cd desktop
npm ci
npm run setup-electron
npm start
```

`setup-electron` descarga el runtime oficial de Electron y sirve también si npm omitió su script de instalación. Para generar el objetivo de distribución del sistema actual, ejecuta `npm run dist -- --config.electronDist=node_modules/electron/dist`: ZIP en Mac, portable en Windows y AppImage en Linux. La firma y la notarización se configuran por separado.

**Compila el motor Python en cada sistema y arquitectura destino.** Un backend de Mac no funciona en Windows o Linux. La app Mac está construida y probada aquí; Windows y Linux tienen el código y los objetivos de empaquetado preparados, pero no se han ejecutado ni validado en sus escritorios. Transparencia, bandeja, atajos globales y siempre encima dependen del gestor de ventanas; en Linux/Wayland pueden requerir ajustes específicos del compositor. No se promete soporte idéntico en todos los entornos.

Pruebas:

```sh
node --test desktop/policy.test.cjs desktop/lifecycle.test.cjs
.venv/bin/python -m unittest discover -s tests -v
```

## Próximas etapas

1. Validar el overlay con usuarios de macOS, Windows y Linux; ajustar interacción y consumo.
2. Ampliar la selección guiada de modelos y probar más proveedores compatibles; el primer inicio ya está incluido.
3. Construir el Ghost Maker con ESP32 y adaptar su conexión al motor compartido.

El repositorio [78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) aporta firmware para dispositivos ESP32. Documenta [WebSocket y audio Opus](https://github.com/78/xiaozhi-esp32/blob/main/docs/websocket.md) y enlaza el [servidor Python xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server). Esa integración requerirá un adaptador de protocolo y la cadena de reconocimiento/generación de voz. **No se ha añadido una conexión Xiaozhi funcional en esta versión.**

La idea para Maker es mantener el cerebro, los recuerdos y las reglas de herramientas en un servidor de confianza y usar el ESP32 como otro cliente de voz/animaciones. Las acciones del escritorio seguirán exigiendo autorización local; no se expondrán automáticamente a un dispositivo o servicio remoto.

## Primer inicio (0.3.0)

Al abrir una instalación nueva aparece **Elige cómo pensar**. La ventana se puede cerrar y reabrir desde **Ghost → Configurar modelo / primer inicio…**. Tras completar la prueba se crea `setup-complete.json` en los datos de ese usuario y deja de aparecer automáticamente. Ese marcador y las credenciales no se incluyen en los ZIP compartidos.

**Ollama local:** instala y abre Ollama si falta, pulsa comprobar conexión, elige un modelo detectado o escribe un nombre público como `llama3.2` y pulsa descargar. El asistente muestra progreso por capa y permite cancelar; no es un porcentaje global de todos los archivos. La app no instala Ollama automáticamente ni incluye pesos de modelos. Un modelo privado como `ghost-heretic` requiere importarlo o publicarlo por separado; no se puede asumir que exista en la biblioteca pública.

**API:** elige Ollama remoto o una API de texto compatible con OpenAI Chat Completions, indica la URL base, la clave si hace falta y el nombre exacto del modelo. Para la opción compatible, la base debe incluir su prefijo, por ejemplo `https://tu-proveedor.example/v1`; el adaptador utiliza `/chat/completions` y, si está disponible, `/models`. Para Ollama remoto usa su origen sin `/api`. No todos los proveedores, modelos o servicios de voz comparten este protocolo; no se admite una URL de chat web ni una API exclusiva de Responses/Anthropic.

**Probar y usar** envía únicamente un mensaje breve de prueba al modelo indicado. Puede generar un cargo del proveedor. No incorpora recuerdos a la prueba. Solo se marca el primer inicio como terminado después de una respuesta de texto válida y de reiniciar el motor con la configuración elegida. El chat posterior sí incluye el contexto y la memoria personal habituales. Aprendizaje y skills están apagados en una instalación nueva y se pueden configurar después.

La clave queda en `config.json`, con permisos privados del usuario. El formulario no recupera su valor guardado, y una clave anterior no se reutiliza automáticamente al cambiar de dirección o tipo de proveedor. El asistente no descarga modelos en servidores remotos. Las llamadas HTTP no siguen redirecciones con credenciales.

Validación de esta versión: seis pruebas de escritorio y ocho de Python pasaron. Se verificaron listado y prueba real con `ghost-heretic` local. Descarga, cancelación, errores y compatibilidad de API se probaron con datos/servidor simulados para evitar descargas de varios GB y llamadas de pago. La interfaz nativa de primer inicio se revisó en Mac; no se ha probado un proveedor de pago con credenciales reales.

Fuentes del protocolo: [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md#pull-a-model), [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Corrección 0.3.1

Se separaron los estilos del SVG y los mensajes del asistente. Antes ambos usaban la clase `ghost`, por lo que un mensaje recibía la altura fija y la animación flotante de la núcleo visual; una respuesta larga desbordaba hacia el siguiente mensaje. El avatar conserva su animación y el texto del chat utiliza su altura natural. La comprobación visual con respuestas largas y memoria no mostró solapamiento ni texto recortado en 460×620 y 360×420.

## Proveedores predeterminados (0.3.2)

En el primer inicio, la opción API ofrece OpenAI, Google Gemini, DeepSeek, Groq y OpenRouter. Al seleccionar uno, Ghost configura su dirección; no hace falta conocer la URL. El botón de ayuda abre documentación oficial o la página de claves del proveedor. Gemini utiliza la [interfaz compatible de Google](https://ai.google.dev/gemini-api/docs/openai) y una clave de Google AI Studio. No usa la sesión de la app Gemini del escritorio.

«Buscar modelos disponibles» consulta el catálogo del servicio con la clave del usuario. Los nombres no están fijados en la app y no se promete acceso gratuito ni disponibilidad de todos los modelos. Si la API no proporciona listado, queda la entrada manual. Las pruebas de texto comprueban compatibilidad antes de guardar. «Mi servidor Ollama» y «Otro servidor compatible» permiten indicar una dirección propia. Las claves no se trasladan automáticamente de un servidor a otro.

El catálogo de direcciones está en `desktop/provider-catalog.json`. Se verificó con documentación oficial de [OpenAI](https://developers.openai.com/api/reference/overview), [Google](https://ai.google.dev/gemini-api/docs/openai), [DeepSeek](https://api-docs.deepseek.com/), [Groq](https://console.groq.com/docs/openai) y [OpenRouter](https://openrouter.ai/docs/quickstart). Se probaron las rutas y cabeceras de los cinco proveedores con respuestas simuladas; no se utilizaron claves de pago. La selección, la URL automática de Gemini y el borrado del campo de clave al cambiar de proveedor se verificaron en una vista de prueba.

Los proveedores/modelos deciden dónde se procesa el texto. Los futuros perfiles de agente (por ejemplo, programador o asistente personal) definirán personalidad e instrucciones; no son cuentas ni servicios API diferentes.

## Skills y voz (0.4.0)

El chat de un modelo no ejecuta comandos por sí mismo. Las confirmaciones de operaciones reales ahora las genera el servidor local después de recibir el resultado de la herramienta, y la personalidad de Ghost prohíbe inventar ejecuciones. Los mensajes anteriores que afirmaron mover archivos no fueron ejecuciones reales.

### Organizar el Escritorio

Abre **Skills y permisos** en la cabecera del chat, habilita las acciones del Mac y guarda. Escribe `organiza mi escritorio`. Ghost muestra todos los movimientos propuestos y espera **Confirmar movimientos**. Clasifica hasta 1.000 archivos sueltos por extensión en carpetas por tipo directamente en el Escritorio, reutilizando las existentes; omite carpetas, archivos ocultos y enlaces. No elimina archivos ni reemplaza nombres existentes. No se leen ni envían sus contenidos al modelo; la lista de nombres permanece en la app y en registros locales de la operación. macOS puede pedir acceso al Escritorio.

Para restaurar rutas, escribe `deshacer organización del escritorio` y confirma la vista previa. La restauración pertenece a esa conversación, respeta los archivos que aparecieron después y no sobrescribe conflictos. Si un archivo cambió, falta o no tiene permisos, se omite y se informa. Las carpetas creadas pueden quedar vacías después de deshacer y no se restauran posiciones visuales de iconos de Finder. No se admiten órdenes de borrado ni shell libre. En volúmenes que no permitan enlaces duros, el movimiento puede fallar; el resultado indica el número realmente movido y los fallos. Las vistas previas vencen a los diez minutos y solo se ejecutan una vez. Si cierras y abres el chat, pide una vista previa nueva.

### Internet disponible por defecto

Las búsquedas están listas al abrir la app, sin interruptor de activación. Escribe tu pregunta directamente. Las preguntas informativas y de actualidad activan la consulta web; también se mantienen `busca ...` e `investiga ...`. Ghost devuelve hasta cinco resultados con enlaces a fuentes. Se consulta un buscador público mediante DDGS, sin abrir ni ejecutar las páginas encontradas. La consulta se transmite al buscador; los recuerdos no se incluyen. No hay navegación continua ni acceso automático a cuentas privadas, correo o servicios con sesión. El buscador puede fallar o limitar consultas; en ese caso Ghost lo indica. Los despliegues externos siguen bloqueando estas herramientas de escritorio.

### Micrófono y bocinas

Activa **Permitir dictado por micrófono** en Skills y permisos y guarda. El botón **Micrófono** pide permiso y muestra el proveedor que recibirá el audio. Graba hasta 60 segundos o 5 MB, pulsa detener y revisa el texto transcrito antes de enviarlo al chat. No hay escucha permanente ni guardado del audio en disco. El audio se envía a tu API y puede generar un cargo. Gemini utiliza el modelo configurado, que debe admitir audio; OpenAI/Groq usan sus endpoints de transcripción. La transcripción local con Ollama está pendiente y otros proveedores no se anuncian como compatibles con dictado.

**Voz** activa o desactiva la lectura de las próximas respuestas. **Probar voz** comprueba la salida. En Mac se usa la síntesis nativa del sistema y el dispositivo de salida elegido en macOS; el texto se pasa por entrada estándar, nunca como comando de shell. En otros sistemas se utiliza la síntesis disponible en el navegador. Revisa el volumen y las voces instaladas si no suena. Salir o cerrar el chat detiene la lectura.

Validación: organización, no sobrescritura, sesión, expiración/repetición, restauración, errores y puertas de permiso se probaron con archivos temporales. Se verificó organización/restauración desde el chat sin usar el Escritorio personal, y una consulta pública devolvió enlaces reales. Los adaptadores de audio y la voz nativa se probaron con respuestas y procesos simulados: no se activó el micrófono ni se reprodujo audio en las bocinas del usuario. El permiso nativo y la transcripción real deben comprobarse en cada equipo/proveedor.

## Búsqueda web corregida (0.4.1)

La búsqueda de la app utiliza ahora peticiones HTTPS directas al buscador (DuckDuckGo HTML, su formato ligero y Bing RSS como alternativas), en lugar de la selección automática de motores de DDGS. Comprueba coincidencias con los términos de la consulta, elimina duplicados y rechaza enlaces no HTTP(S). Este filtro reduce resultados ajenos a la consulta; no verifica por sí mismo la exactitud de cada página. Los textos se identifican como extractos del buscador.

Los resultados correctos se conservan cinco minutos en una caché acotada a 128 consultas; los errores no se guardan. Se probaron fallos sucesivos de motores, resultados irrelevantes, duplicados y la extracción de enlaces. La consulta real «qué es JSON» devolvió cinco fuentes relacionadas tanto en desarrollo como a través del motor empaquetado que acompaña a la app. Los buscadores públicos pueden seguir imponiendo límites o bloqueos; no se promete disponibilidad permanente ni se usa una API de pago adicional como alternativa oculta.

La preparación del backend también sustituye el directorio de binarios completo en lugar de sobrescribir ejecutables firmados en el mismo archivo, para evitar problemas con la caché de firmas de macOS durante reconstrucciones repetidas.

## Búsqueda desde el mensaje normal (0.4.2)

Se eliminó el botón Internet. El servidor decide localmente, sin otra llamada de pago, si una pregunta informativa necesita búsqueda. Ejemplos: `qué es JSON`, `quién es el presidente de México`, `cómo funciona HTTP`, preguntas de clima y noticias. Las respuestas de ese flujo llevan la etiqueta **Internet · búsqueda automática** y conservan sus fuentes.

No se envía cada conversación al buscador: saludos, tareas creativas, comandos del equipo, recuerdos, código y mensajes con ciertos datos identificables se mantienen fuera de la búsqueda automática. Es una detección basada en reglas, no una garantía de interpretar cualquier frase; `busca ...` e `investiga ...` permiten pedirla explícitamente sin botón. `sin internet` o `no uses internet` omiten la búsqueda web en ese mensaje; si el modelo configurado es una API remota, la conversación sigue utilizando esa API.

Se verificaron preguntas directas, noticias, exclusión de datos/código, omisión voluntaria y la respuesta del endpoint sin pasar por el modelo de conversación. El buscador no genera confirmaciones de operaciones locales y no abre el micrófono.

## Búsqueda local por nombre (0.4.3)
Activa las acciones locales desde «Skills y permisos». Escribe «puedes buscar un archivo en mi Mac»; Ghost pide una pista del nombre o una extensión. También puedes escribir «busca el archivo informe». Confirma para buscar. Revisa Documentos, Escritorio y Descargas, o solo GHOST_SEARCH_ROOT si se configura. No lee contenidos, abre, mueve ni borra archivos. Omite enlaces y archivos ocultos; limita tiempo, recorrido y resultados. Las rutas de resultados no se incluyen en el contexto posterior del modelo. La búsqueda es local y se bloquea en modo público. Los permisos de macOS pueden impedir revisar algunas carpetas. No incluye búsqueda por contenido ni todo el disco.

## Búsqueda rápida por carpetas y extensión (0.4.4)
La app migra el valor de fábrica anterior `~/Documents` a las carpetas habituales: Escritorio, Descargas, Documentos, Música, Imágenes y Películas. Se conservan las raíces personalizadas. En el servidor independiente deja GHOST_SEARCH_ROOT vacío para usar estas carpetas; un valor explícito restringe la búsqueda a esa ruta. Reconoce «extensión .csv» tanto en la petición inicial como al responder a la pregunta por una pista, y compara la extensión exacta sin distinguir mayúsculas.
Cada carpeta tiene su propio límite de 3500 entradas, 0.65 segundos y 5 coincidencias; una carpeta grande no consume el presupuesto de las demás. Se indica si la revisión fue parcial. No incluye todo el disco, carpetas ocultas, enlaces ni contenido de archivos. Los permisos de macOS siguen aplicándose.

## Voz por pausa y agrupar resultados (0.4.5)
En el chat, activa «Enviar al pausar» y pulsa Micrófono. Tras reconocer actividad y una pausa de 1.6 segundos, se cierra la captura, se envía el audio al proveedor autorizado y se manda la transcripción al chat. El modo es opcional y se apaga al cerrar la ventana; cada mensaje requiere iniciar el micrófono. No escucha en segundo plano. Sin frase detectada en ocho segundos se cierra sin enviar audio. Sigue el límite de 60 segundos y las condiciones del proveedor de dictado. Es un detector de nivel de sonido, no un detector semántico: ruido o pausas largas pueden alterar el corte. Si hay un borrador escrito, conserva el texto y pide revisión en lugar de enviarlo automáticamente.
Después de una nueva búsqueda de archivos, pide «organiza esos archivos en una carpeta». La app guarda localmente los resultados por conversación durante diez minutos. La vista previa muestra únicamente esos archivos y una carpeta nueva Ghost_Archivos_… en el Escritorio. Los nombres repetidos reciben sufijos. No se mueve nada hasta confirmar los movimientos. Puedes pedir «deshacer agrupación de archivos» y confirmar la restauración. No sobrescribe archivos, no sigue enlaces y rechaza archivos que hayan cambiado. Un resultado de otra unidad puede no moverse: se conserva el original y se informa el fallo. No se envían rutas al proveedor de IA. Las búsquedas realizadas en versiones anteriores deben repetirse para disponer del registro local.

## Herramientas comunes para nube y Ollama (0.5.0)
Las peticiones que no resuelve un comando directo ofrecen al modelo un catálogo común de funciones mediante tool calling: buscar fuentes públicas, encontrar archivos, preparar una agrupación o deshacerla, preparar la organización del Escritorio y abrir apps permitidas. La selección funciona con Ollama y con el formato chat/completions usado por los proveedores preconfigurados. Depende del soporte de herramientas del modelo elegido; una API compatible no garantiza que cada modelo admita herramientas.
Las respuestas de herramientas las presenta Ghost directamente. Las rutas locales y los planes no se devuelven al modelo para una segunda síntesis. No hay ejecución de Python, shell, scripts generados, ni bucles autónomos. Solo se acepta una herramienta por turno con argumentos validados. Las herramientas deshabilitadas no se ofrecen ni se ejecutan. También se excluye la herramienta web de solicitudes personales (mi/mis) o con rutas, correos o señales de credenciales. «Sin internet» excluye la herramienta web para ese mensaje, aunque la conversación seguirá usando el proveedor de chat configurado.
Las búsquedas de archivos y la apertura de apps exigen confirmación ligada al mensaje, sesión e identificador de un solo uso que vence en cinco minutos. Los movimientos solo preparan vistas previas; la confirmación de cada plan sigue siendo independiente. El registro local tool_events contiene el nombre de la herramienta, sesión y fecha sin argumentos ni rutas.
Si el proveedor rechaza explícitamente herramientas con HTTP 400/422, Ghost usa conversación normal y comandos directos. Guarda ese estado temporal por endpoint/modelo durante una hora; reiniciar la app permite comprobarlo de nuevo. Errores de autenticación, saldo o conexión no se disfrazan de incompatibilidad. No se interpreta JSON escrito libremente por modelos sin tool calling como una orden ejecutable. El selector no cambia los permisos de skills.
La voz sigue separada del chat y las herramientas: el dictado actual usa Gemini, OpenAI o Groq y las voces del sistema. Esta versión no instala transcripción local ni añade Gemini Live; un modelo local puede usar las herramientas por texto sin API externa de chat. La búsqueda web, si se usa, consulta internet.

## Carpetas por tipo directamente en el Escritorio (0.5.1)
«Organiza mi escritorio» muestra destinos como Documentos/nota.txt e Imagenes/foto.png, sin carpeta contenedora Ghost_Organizado. Reutiliza las carpetas que ya existan; reconoce mayúsculas y acentos (por ejemplo, Imágenes). Los archivos con nombre repetido reciben sufijos que aparecen en la vista previa. Las carpetas existentes se conservan y no se reorganiza recursivamente su contenido ni se cambia la posición visual de sus iconos. La agrupación de resultados en una carpeta nueva sigue siendo una acción independiente.
Para aplicar esta distribución a una organización antigua, solicita «deshacer organización del escritorio» en la misma conversación, confirma la restauración y después pide «organiza mi escritorio». Al deshacer un plan antiguo se retiran únicamente las subcarpetas y el contenedor Ghost que hayan quedado vacíos. Si hay contenido añadido por el usuario, esas carpetas se conservan. Todos los movimientos requieren confirmar el plan.

## Burbuja junto al Núcleo 0.6.2
La distribución Electron abre un panel transparente sin marco de 410 por 390 puntos, anclado a un lado del avatar y ajustado al área útil de la pantalla. Al mover el avatar, la burbuja lo acompaña. Muestra la última respuesta en modo compacto; ↗ abre el historial en 480 por 660 puntos (o lo que permita la pantalla) y ↙ vuelve al modo compacto. Las confirmaciones y los planes de archivos expanden el panel automáticamente. El botón × deja solo el avatar.
La burbuja compacta puede cerrarse después de 18 segundos sin interacción, tras una respuesta nueva. No se programa ese cierre si está ampliada, el puntero sigue dentro, hay borrador, grabación, transcripción, lectura por voz, diálogo o plan pendiente. La conversación permanece guardada. Si se cierra mientras hay una respuesta en curso, se oculta y espera a que termine antes de liberar la ventana, conservando la respuesta.
Esta versión conserva la corrección 0.6.1: nombres internos y helpers ASCII, marca visible con acentos y verificación del paquete macOS en afterPack. La app principal se llama VoxelSwarm.app; no cambiar los nombres internos de sus ejecutables. El proyecto SwiftUI anterior sigue siendo una alternativa de código y no implementa este panel Electron flotante.

## Personalización 0.6.3
En el menú del Núcleo elige «Colores del Núcleo»: cyan, azul, violeta, verde o ámbar. La selección se guarda en la configuración local. Son variantes de color del diseño actual. La burbuja se puede ampliar o reducir arrastrando sus bordes, con un indicador en la esquina inferior derecha. El tamaño personalizado se mantiene durante la sesión y la vista ampliada reserva espacio para planes y confirmaciones.


## Conversación por voz por turnos (0.6.6)

1. Activa el micrófono desde **Skills y permisos / Ajustes de IA** y configura un proveedor compatible con transcripción (Gemini, OpenAI o Groq).
2. En la burbuja, pulsa **Conversar por voz** y acepta una vez el aviso de envío de audio durante esa sesión. macOS solicitará su permiso de micrófono si hace falta.
3. Habla y termina con una pausa de 1,6 segundos. La app cierra la captura, transcribe la frase, envía el texto al chat y reproduce la respuesta. Cuando acaba la reproducción, vuelve a abrir el siguiente turno automáticamente.
4. Pulsa **Terminar voz** o cierra la burbuja para finalizar. No se reactiva al abrir de nuevo la app. También se detiene al abrir ajustes o memoria, cambiar de modelo, iniciar una conversación nueva, producirse un error o acumular dos minutos de inactividad.

El indicador muestra escucha, transcripción, preparación, respuesta o pausa. Durante la reproducción, la transcripción y las confirmaciones no hay captura activa. Se conserva un borrador escrito y no se envía automáticamente si aparece mientras se graba. Las vistas previas de archivos siguen requiriendo confirmación; la sesión espera mientras se revisan.

Cada grabación está limitada a 60 segundos y 5 MB. Los intervalos sin frase detectada se descartan localmente. No se escribe audio en disco. Las frases se envían al proveedor de transcripción y el texto al modelo configurado, con los costes que correspondan. El dictado manual sigue disponible fuera de la conversación por voz.

Esta versión reutiliza el detector local de nivel y pausas: no incorpora Silero, palabra de activación, transcripción local, Gemini Live ni interrupción por voz durante la respuesta. El ruido o una pausa larga pueden afectar al corte. Ollama requiere un transcriptor local adicional, pendiente de integrar.

Validación: pruebas automatizadas del controlador, captura, cancelación, permisos tardíos, desconexión, inactividad y varios turnos en la UI con micrófono, transcripción y voz simulados. No se grabó audio real ni se hicieron llamadas de pago para estas pruebas; la comprobación acústica y de permisos en el equipo del usuario sigue pendiente.


## Voz local con Ollama (0.6.7)

En **Configurar modelo / primer inicio**, elige **En este equipo con Ollama**, selecciona tu modelo de conversación y comprueba la conexión. En **Skills y permisos**, activa **Permitir micrófono para dictado y conversación por voz** y guarda. La burbuja mostrará **Descargar voz local · 148 MB**; acepta la descarga de Whisper base multilingüe. Se descarga desde una URL pública de Hugging Face fijada a una revisión, se verifica el tamaño y SHA256 antes de instalarlo y se puede cancelar. Una descarga incompleta no se utiliza. No requiere API key. El modelo queda en el subdirectorio `data/voice` del directorio privado que ya usa la app, separado de tus recuerdos; actualizar la app no lo elimina.

Cuando indique **Whisper local listo**, pulsa **Conversar por voz**. Conserva la pausa de 1,6 segundos, la respuesta hablada y la reapertura automática por turnos. El dictado de una sola frase también usa Whisper al elegir Ollama. No hay cambio automático a un servicio cloud si falla el motor local.

La captura local usa AudioWorklet, convierte a WAV mono PCM de 16 kHz en memoria y entrega el audio al motor nativo por stdin. El texto vuelve por stdout. No se escriben grabaciones ni transcripciones temporales; el texto enviado al chat sí sigue las reglas habituales del historial y la memoria. El límite continúa siendo de 60 segundos y 5 MB por turno. La inferencia está acotada a una transcripción simultánea y 120 segundos. En esta entrega, el motor usa CPU y Apple Accelerate; no requiere ffmpeg ni paquetes Python de aprendizaje automático en el equipo del usuario. whisper.cpp y Whisper conservan sus licencias MIT en los recursos de la app.

La voz de salida sigue usando las voces de macOS. Si Ollama también está en el mismo equipo, el reconocimiento, la respuesta del modelo y la lectura no necesitan APIs externas después de descargar los modelos. Si se configura Ollama remoto, ese servidor recibe el texto. Las herramientas de búsqueda en internet mantienen su comportamiento habitual cuando se solicitan; no forman parte de la transcripción. El modo público sigue bloqueando micrófono y descarga del modelo.

Para desarrollo: `GHOST_WHISPER_CLI` permite indicar el binario y `GHOST_VOICE_MODEL_DIR` un caché alternativo. Son variables del proceso, nunca parámetros aceptados desde la web. `desktop/prepare_voice.py` reconstruye la revisión fijada de whisper.cpp. Recompila para cada SO/arquitectura; esta app se entrega para Mac Apple Silicon.

Validación 0.6.7: transcripción real de una frase española sintetizada, sin micrófono ni API de pago; pruebas automatizadas de WAV/remuestreo, recursos de audio, cancelación, rutas local/cloud, integridad y cancelación de descarga, límites, permisos de endpoints e integración del ciclo de voz. La prueba del micrófono físico y las condiciones acústicas del usuario sigue pendiente.


## Selector de aplicaciones (0.6.8)

En **Skills y permisos / Ajustes de IA**, la sección **Aplicaciones permitidas** muestra casillas y un buscador para el catálogo local. Revisa las apps y pulsa **Guardar y reconectar**. **Actualizar lista** detecta cambios de instalación sin descartar tu selección; las apps ausentes se muestran como no encontradas y se pueden desmarcar. **Quitar toda la selección** guarda una lista vacía de verdad: no vuelve a activar Calculadora y Notas. La selección puede prepararse con las acciones locales apagadas; solo se usa al habilitarlas.

El catálogo examina bundles válidos en `/Applications`, `/System/Applications`, `~/Applications`, sus grupos de un nivel, las utilidades de CoreServices y Finder. No es un recorrido de todos los discos ni incluye automáticamente apps guardadas en carpetas arbitrarias. Los nombres habituales de apps de Apple incluyen alias españoles; también se reconocen Chrome y VSCode. La apertura usa la ruta concreta que se marcó, procedente del catálogo local, con `/usr/bin/open -a` y sin shell. Si hay dos apps autorizadas con el mismo nombre, pide dejar seleccionada la deseada en lugar de elegir una al azar.

`allowedApps` se guarda como array en la configuración privada ya existente; se conservan las selecciones al cambiar de Ollama a una API y viceversa. Los nombres guardados en versiones anteriores se migran al selector. El backend recibe `GHOST_ALLOWED_APPS_JSON`; si no existe esa variable en una ejecución manual, sigue admitiendo `GHOST_ALLOWED_APPS` separado por comas. Un JSON vacío o inválido no autoriza apps por defecto.

La lista completa y las rutas solo se consultan en el Mac: no se añaden al contexto del modelo. `/api/apps` requiere la autenticación habitual y está bloqueado en modo público; el puente de Electron solo permite solicitarlo desde la ventana de ajustes. La lista permite abrir una app, no ejecutar órdenes de terminal ni controlar lo que ocurre dentro. Tanto voz como texto conservan la confirmación antes de abrir; los permisos se vuelven a comprobar al ejecutar.

Validación: descubrimiento con bundles temporales, alias de voz en español, permisos por app concreta, nombres duplicados, listas vacías, migración, selección/búsqueda/guardado y errores de la UI, IPC autorizado y restricciones del endpoint. Las aperturas se verifican con un proceso simulado, sin iniciar apps personales durante las pruebas.


## Abrir apps preautorizadas sin confirmación repetida (0.6.9)

Las casillas de **Aplicaciones permitidas** constituyen la autorización para abrir esas apps. Con las acciones locales habilitadas, «abre Safari» o «abre Notas» las abre directamente, tanto desde texto como desde el dictado o la conversación por voz. La apertura por herramientas de Ollama/API usa la misma lista y también prescinde del segundo diálogo. Las apps no marcadas, una lista vacía, el modo público o las acciones apagadas siguen impidiendo abrir aplicaciones. Los permisos se comprueban al ejecutar; no hay ejecución de comandos ni control del contenido de la app.

Para herramientas seleccionadas por el modelo se exige una petición de apertura en el mensaje actual y una coincidencia con el nombre o alias de la app. Preguntas generales como «qué aplicaciones puedes abrir» no autorizan una apertura. Las búsquedas de archivos, vistas previas y confirmaciones de movimientos mantienen su funcionamiento anterior.

Esta versión no incorpora palabra de activación ni reproducción musical por artista/canción. La voz continua todavía se activa desde su botón y se detiene al cerrar la burbuja. «Oye Vox» requerirá un detector local de la frase, captura independiente de la ventana de chat, indicador y control de mute, gestión de pausas/eco y activación de la sesión de voz. Controlar Spotify, Música u otro reproductor requiere una skill adicional y los permisos o conexión específicos del servicio.

Validación: pruebas de apertura directa por comando y por herramienta nativa, bloqueo de apps no autorizadas, lista vacía, preguntas sin intención de apertura y conservación de confirmaciones para archivos. Los procesos de apertura se simulan para no iniciar apps personales durante las pruebas.


## Activación local «Oye Vox» (0.7.0)

La escucha es opcional y se activa con la casilla explícita **Activar «Oye Vox» aunque la burbuja esté cerrada**, en Ajustes. Habilitarla habilita también el micrófono. La preferencia se guarda; en los siguientes inicios escucha mientras la app esté ejecutándose. Deshabilitar el micrófono desactiva «Oye Vox». Puede silenciarse con el círculo en el pie del avatar o desde su menú; el estado sigue visible en el avatar y en el tooltip de la bandeja. Las apps permitidas se conservan.

La captura pertenece a una ventana interna invisible y aislada, independiente de la burbuja. Usa AudioWorklet, salida silenciosa y un búfer acotado en memoria. Un detector local de actividad descarta silencios y golpes breves; los segmentos de voz, de hasta 20 segundos y con preaudio corto, se envían solo al backend loopback autenticado. El backend usa el C API de Vosk 0.3.44, un modelo español pequeño incluido en la app y vocabulario restringido a «oye vox»/habla desconocida. La llamada debe estar al principio del segmento, con confianza mínima y tiempos contiguos entre ambas palabras. No se emplea una búsqueda de palabras en la salida de una API cloud.

Cuando se detecta la llamada, el audio posterior a la palabra «Vox» puede convertirse en comando con Whisper local; así se admite la llamada y el comando juntos. Si no hay comando, abre la burbuja, muestra **Te escucho** y espera una frase durante 15 segundos. Solo después de la activación se entrega texto al chat/modelo configurado. Las hipótesis del detector sobre otro audio se descartan; no se escriben grabaciones ni transcripciones ambientales en disco, historial o memoria. El texto del comando y su respuesta sí siguen las reglas habituales del chat. Una tokenización pegada como «abrenotas» se corrige solo si corresponde a una app ya permitida.

Antes de entregar el comando se cierra la captura. La respuesta se reproduce con las voces del sistema; al terminar, tras una pausa breve, vuelve al modo de espera. La burbuja se abre para mostrar resultados o confirmaciones. Las apps autorizadas se abren directamente, y los archivos conservan sus confirmaciones. Si hay borrador o acción pendiente, no lo reemplaza ni confirma por voz: conserva el comando como borrador para revisión. El envío se hace una sola vez y espera a que el chat esté listo, incluidos configuración e historial.

La escucha se pausa mientras se responde, se usa dictado/conversación manual, se editan borradores, se revisan confirmaciones o se abren Ajustes/primer inicio. También se detiene al bloquear o suspender el Mac. Reanuda al desbloquear si sigue habilitada. Cerrar la burbuja deja el modo de espera activo; salir de Núcleo lo termina. Un fallo de micrófono o de motor cierra la captura y exige **Reintentar «Oye Vox»** en el menú; no reintenta en bucle. Decir «Oye Vox, deja de escuchar» silencia el modo. Silenciar libera también el modelo del detector en el backend. No hay escucha cuando la app está cerrada o el Mac duerme.

El modelo del detector de español (~58 MB descomprimido) y la biblioteca nativa se incluyen en esta app; el modelo Whisper (148 MB) conserva la instalación de una sola vez. Ambos pueden funcionar sin una API externa para audio. El modelo de chat aún puede ser Ollama local o cloud. Este modo tiene consumo de memoria y CPU mientras escucha, especialmente con TV, música o conversación de fondo, y no es identificación del hablante. Una futura versión puede sustituir el detector por un modelo dedicado más pequeño. La escucha local usa un límite separado de 60 solicitudes/minuto para no consumir la cuota normal del chat.

El puente del proceso de escucha solo permite publicar fase, comando, error o silencio; el proceso principal verifica ventana y frame. Solo chat y escucha autorizada pueden pedir micrófono, nunca cámara. El endpoint `/api/voice/local/transcribe` exige token, origen válido, micrófono habilitado, consentimiento, formato/tamaño válidos y modo privado. No existe fallback a transcripción cloud. El backend serializa la inferencia del detector, y la app evita usar simultáneamente micrófono de fondo y dictado manual. Los binarios y las licencias de Vosk, el modelo y Whisper se empaquetan con la app; el proyecto editable incluye `prepare_wake.py` con URLs y SHA256 fijados para reconstruir los recursos del detector.

Validación 0.7.0: pruebas del coordinador con burbuja cerrada, entrega única al estar listo, silencio/pausa/modelo ausente, cierre y resultados tardíos; driver de audio con captura y API simulados; UI con comando hablado, preservación de borrador, proveedor cloud y selección de permisos; puertas del endpoint local. Pruebas reales de los motores con voz sintética en español: llamada sola, llamada con comando y dos voces, además de frases negativas (incluida la llamada mencionada dentro de otra frase). No se activó el micrófono físico ni se abrieron apps personales. Las condiciones acústicas reales y falsos positivos deben probarse con el usuario; no se afirma una tasa de acierto medida en producción. Apple Music, palabra de activación personalizada e interrupción mientras Núcleo habla siguen pendientes.

Comprobación nativa adicional: Electron ejecutó el driver de escucha en una ventana invisible y con sandbox, usando una fuente WebAudio sintética que sustituye solo la entrada de la prueba. Se verificaron los estados espera → reconocimiento → comando y la llamada con comando en una sola frase, contra el backend y motores empaquetados. No se usó el micrófono físico ni se ejecutó la app mencionada en la muestra.
