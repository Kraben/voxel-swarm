# Enjambre de Vóxeles

Asistente de escritorio con avatar flotante, conversación, memoria y herramientas locales autorizadas. Proyecto en desarrollo hacia un compañero físico de voz con ESP32.

**Versión actual: 0.7.3 · beta.** macOS Apple Silicon es la plataforma empaquetada y comprobada en este proyecto. Los ports de Windows/Linux están en desarrollo por separado; este repositorio no incluye todavía instaladores validados de esos sistemas.

## Qué funciona

- Avatar flotante, skins y burbuja de chat redimensionable.
- Ollama local y API de Gemini en Free; otros proveedores compatibles con activación Pro.
- Memoria persistente, búsqueda web y búsqueda/organización de archivos con límites y confirmaciones.
- Voz local, conversación continua y activación opcional «Oye Vox» en el Mac.
- Abrir y solicitar cierre normal de aplicaciones elegidas por el usuario, sin controlar su contenido ni forzar su salida.

La beta incluye activaciones Pro firmadas manuales; **no hay cobro automático, límite de equipos ni revocación online**. Cada usuario proporciona sus claves API y paga el consumo de su proveedor cuando corresponda. El código público no incluye una activación Pro, claves privadas ni credenciales de servicios.

## Límites actuales

No están integrados ESP32, calendario, recordatorios, Telegram/WhatsApp ni control de reproducción musical. MusicKit permanece archivado como experimento, fuera de la aplicación activa. Los scripts de carcasa son prototipos; las fijaciones y componentes necesitan validación física.

La app macOS es una beta sin firma Developer ID ni notarización. No está lista para distribuirse como producto comercial terminado.

## Documentación y estructura

- [Manual de la app](docs/APP-MANUAL.md)
- [Overlay y voz](OVERLAY.md)
- [Estado y visión del proyecto](docs/RESUMEN-VOXELES-PARA-COMENTAR.md)
- [Licencias y distribución](commercial/README.md)
- [Directriz para Windows/Linux](commercial/PORT-WINDOWS-LINUX-FREE-PRO.txt)
- [Revisión de componentes y carcasa](docs/hardware/COMPRA-Y-REVISION-GHOST-XIAO-C6.txt)
- `hardware/carcasa-fusion/`: scripts y notas de Fusion, incluido el frontal V3 existente.
- `web/archive-kit-0.6.0/`: material histórico para la web; no representa el estado comercial actual.
- `experiments/`: trabajo en espera; no se empaqueta con la app activa.

## Desarrollo

El código de escritorio está en `desktop/`, la interfaz en `static/` y el backend FastAPI en la raíz. Consulta el manual antes de ejecutar. No se incluyen dependencias, modelos de voz, ejecutables nativos o motores empaquetados.

Para reconstruir en macOS se necesitan Python, Node, herramientas de compilación y preparar los runtimes con `desktop/prepare_voice.py` y `desktop/prepare_wake.py` antes de `desktop/prepare_backend.py`. `requirements-mac.txt` incluye el empaquetador Python. Después de instalar las dependencias de Electron, `npm start --prefix desktop` utiliza el backend preparado.

Las herramientas locales necesitan autorización explícita en la app. No expongas el backend de escritorio a internet para conectar un dispositivo.

## Colaboración

Los ports deben fusionar los cambios compartidos sin sustituir adaptaciones de cada sistema. Mantener las mismas reglas Free/Pro y la misma clave pública de verificación. No regenerar el emisor para cada plataforma. No subir claves privadas, datos de memoria o activaciones reales.

No se ha seleccionado una licencia de código abierto para el código propio. La publicación del repositorio permite revisarlo; las condiciones de reutilización comercial deben acordarse con el titular. Las dependencias y recursos de terceros conservan sus licencias y avisos.
