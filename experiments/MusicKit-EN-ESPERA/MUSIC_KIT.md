# Apple Music: catálogo con MusicKit (0.7.2)

## Estado de esta entrega

La integración está implementada en el código: reproductor nativo Swift, búsqueda del catálogo, cola, autorización, comprobación de suscripción, controles y conexión con los comandos escritos o de «Oye Vox». El proyecto nativo compila con el SDK instalado. Las pruebas de integración usan un reproductor simulado: **todavía no se ha validado reproducción real con tu cuenta**.

El paquete de desarrollo no contiene un componente con tu firma de Apple. El modo biblioteca sigue disponible; el modo catálogo mostrará que falta configurar MusicKit hasta completar estos pasos. El componente de catálogo requiere **macOS 14 o posterior** y una suscripción activa de Apple Music para canciones completas. Reproduce dentro de Vóxeles mediante ApplicationMusicPlayer; no modifica la cola de la app Música. La disponibilidad depende del catálogo de la región de tu cuenta.

## 1. En Apple Developer

1. Entra en https://developer.apple.com/account/resources/identifiers/list y selecciona tu equipo de pago.
2. En **Identifiers**, pulsa **+ → App IDs → App → Continue**.
3. Nombre/descripción: **Voxeles Music**. Bundle ID: **Explicit**, con el valor **com.voxelswarm.desktop.music**. Este es el ID del reproductor nativo, diferente del de Electron (`com.voxelswarm.desktop`). Si ese ID ya pertenece a otro equipo, elige uno propio, por ejemplo `com.tumarca.voxeles.music`, y usa exactamente el mismo en Xcode y en el comando de compilación.
4. En la pestaña **App Services**, habilita **MusicKit**. No lo confundas con crear una clave de Media Services o buscar un entitlement inventado.
5. Continúa y registra. Si el App ID ya existe en tu equipo, edítalo y guarda el servicio MusicKit habilitado.
6. En **Account → Membership details**, localiza tu **Team ID** (10 caracteres). Puedes introducirlo localmente; no es una clave privada.

Este proyecto usa generación automática de tokens de MusicKit para Swift, asociada al Bundle ID firmado. **No necesitas generar ni compartir un archivo .p8**, Key ID, contraseña o token del usuario para esta vía nativa. No es necesario registrar el servidor FastAPI ni Vercel como redirect URI.

Fuentes oficiales: [habilitar MusicKit](https://developer.apple.com/help/account/services/musickit), [tokens automáticos](https://developer.apple.com/documentation/musickit/using-automatic-token-generation-for-apple-music-api).

## 2. En Xcode

1. Abre `macos/MusicKitBridge/VoxelMusic.xcodeproj` (el proyecto nuevo del reproductor; no el prototipo antiguo GhostAI).
2. Ve a **Xcode → Settings → Accounts**, añade tu cuenta Apple si hace falta y selecciona el equipo con membresía activa.
3. Selecciona el target **VoxelMusic → Signing & Capabilities**.
4. Activa **Automatically manage signing**, elige tu **Team** y comprueba que **Bundle Identifier** coincida con el registrado. El servicio MusicKit se habilita en el portal; no hace falta agregar una clave de MusicKit manualmente al archivo de entitlements.
5. El proyecto ya incluye el texto de permiso `NSAppleMusicUsageDescription`, App Sandbox y permiso de red saliente. Mantén esos ajustes. No ejecutes el target independiente para probar la música: espera comandos privados de la app Electron.

## 3. Compilar e instalar el componente en el proyecto

Desde la raíz de `ghost-ai`, ejecuta sustituyendo `TU_TEAM_ID`:

```sh
python3 desktop/prepare_music.py --team TU_TEAM_ID
```

Si registraste otro Bundle ID:

```sh
python3 desktop/prepare_music.py --team TU_TEAM_ID --bundle-id com.tumarca.voxeles.music
```

El script usa Xcode y el llavero local para construir y verificar el componente. Puede necesitar conexión para gestionar la firma. Coloca la app firmada en `desktop/music-runtime/VoxelMusic.app`. Si falla por cuenta, certificados o perfil, resuélvelo en Xcode; no desactives la firma para hacer funcionar MusicKit. El script no comprueba que hayas habilitado el servicio en el portal: esa verificación final se hace al conectar.

Para probar con el backend de desarrollo ya preparado, cierra Vóxeles y ejecuta:

```sh
npm start --prefix desktop
```

Si recibiste solo el ZIP de código y aún no tienes dependencias/backend, sigue primero los pasos de preparación de README.md; el proyecto editable excluye dependencias y modelos descargados.

Para que el componente forme parte de una app empaquetada, hay que empaquetar **después** de compilarlo:

```sh
npm run pack --prefix desktop -- --config.electronDist=node_modules/electron/dist --config.directories.output=release-musickit-signed
```

No basta con firmar el helper para afirmar que el instalador entero está firmado/notarizado. Este flujo utiliza una compilación de desarrollo del componente para tu Mac. Antes de distribuirlo a terceros, prepara firma Developer ID, configuración de distribución y notarización de la app completa. No redistribuyas perfiles de desarrollo ni certificados privados.

## 4. Conectar dentro de Vóxeles

1. Abre **Ajustes de IA / Skills y permisos**.
2. Activa las acciones del Mac y **Permitir controles de Apple Music por voz y texto**.
3. Selecciona **MusicKit · Catálogo de Apple Music**.
4. Pulsa **Conectar Apple Music** y acepta el permiso del sistema para **Vóxeles Music**.
5. **Comprobar conexión** debe mostrar cuenta autorizada y suscripción activa. Guarda y reconecta.
6. Prueba por texto «reproduce Rammstein». Para voz, activa «Oye Vox» y descarga la voz local si aún falta.
7. Prueba «pausa la música», «reanuda la música», «siguiente canción» y «canción anterior». Los controles visibles de MusicKit en Ajustes permiten hacer lo mismo.

Cuando la consulta coincide con un artista, se utilizan sus canciones destacadas; para otras consultas se utiliza la lista de canciones encontrada. Se omiten resultados sin parámetros de reproducción. No se afirma que esté sonando si MusicKit no confirma el estado.

**Desconectar** detiene y vacía el reproductor; no revoca el permiso concedido a Apple. Para revocarlo, utiliza **Ajustes del Sistema → Privacidad y seguridad → Contenido multimedia y Apple Music** (el nombre puede variar según la versión). Desactivar la integración o salir de Vóxeles detiene el componente. Cambiar de proveedor de IA no cambia tu cuenta Apple Music.

## Datos y permisos

- La consulta musical se envía a Apple para buscar; Vóxeles no guarda claves de MusicKit ni extrae la biblioteca para enviarla al LLM.
- La transcripción del micrófono mantiene su configuración local/cloud existente. MusicKit no implementa el reconocimiento de «Oye Vox».
- Backend → Electron: loopback con puerto aleatorio y token distinto al del chat; sin redirecciones ni proxies. Electron → Swift: pipes privados heredados. No hay un servidor público para controlar música.
- No acepta scripts, URLs ni rutas del modelo como comandos. Las acciones están limitadas a reproducción, pausa y navegación.
- No se descarga música ni se emplean APIs privadas. No hay reproducción automática al conectar.
- La música que sale por los altavoces puede activar falsos despertares. Esta entrega no incorpora cancelación acústica de eco ni interrupción de voz durante TTS.

## Monetización

Apple Music está fuera del bloqueo Pro. El resto del apartado de licencia continúa siendo una propuesta sin checkout ni validación de licencias. Las condiciones de Apple restringen cobrar o monetizar el acceso a Apple Music; una suscripción Pro de Vóxeles no sustituye la suscripción del usuario al servicio.

Referencia: [Apple Developer Program License Agreement, MusicKit](https://developer.apple.com/support/terms/apple-developer-program-license-agreement/).
