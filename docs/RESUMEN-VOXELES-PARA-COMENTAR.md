# Vóxeles: avances, dudas y posibles caminos de venta

**Resumen al 11 de noviembre de 2026**  
**Versión actual: 0.7.3 · Beta para macOS Apple Silicon**

> La idea central es un compañero personal tipo «Jarvis»: hablarle desde un dispositivo físico, que recuerde contexto, responda con voz y ejecute tareas autorizadas en la computadora. La app de escritorio es la base que ya construimos; el dispositivo ESP32 todavía está por integrarse.

## 1. Qué queremos construir

Vóxeles empezó como un avatar flotante inspirado en un Ghost de Destiny, conectado a un modelo de IA. Evolucionó hacia una identidad propia, **Enjambre de Vóxeles**, y una experiencia con una burbuja de conversación sobre el escritorio.

La visión final del creador es principalmente **física**: una carcasa impresa con pantalla, micrófono y bocina, desde la que se pueda llamar al asistente y conversar sin estar haciendo clic en la computadora.

Ejemplo deseado:

1. La persona dice «Oye Vox» al dispositivo.
2. El dispositivo escucha la petición y la comunica a Vóxeles.
3. Vóxeles usa el modelo elegido y, si procede, una herramienta autorizada.
4. El dispositivo responde por su bocina y muestra el estado en la pantalla.

**Este recorrido completo desde el ESP32 todavía no funciona.** Ya existe buena parte de la base en la computadora, pero faltan el firmware, la conexión de audio y el emparejamiento del dispositivo.

## 2. Avances de la aplicación

| Área | Qué existe actualmente | Límite o aclaración |
|---|---|---|
| Presencia en escritorio | Avatar flotante, estados visuales y skins de colores. | La experiencia sigue en beta. |
| Conversación | Burbuja de chat redimensionable con el mouse y aspecto relacionado con el skin. | Se sustituyó la presentación de ventana tradicional que incomodaba al creador. |
| Modelos locales | Conexión a Ollama, detección de modelos y descarga desde la configuración. | Requiere Ollama disponible y un modelo adecuado para el equipo. |
| Modelos externos | Gemini y otros servicios compatibles con el formato de API implementado. | Cada comprador aporta su clave; no todos los proveedores o funciones son compatibles automáticamente. |
| Primer inicio | Selección del motor, configuración del servidor, comprobación y elección de modelo. | Los límites y cargos del proveedor pertenecen a la cuenta del usuario. |
| Memoria | Recuerdos persistentes, consulta y opciones de olvido. | No equivale a memoria perfecta ni a razonamiento autónomo sobre toda la actividad del equipo. |
| Voz | Dictado, conversación continua y lectura con voces del sistema. | Aún falta mejorar interrupciones, eco y comportamiento con ruido. |
| Transcripción local | Whisper local para la ruta con Ollama y detección local de activación. | Los modelos de voz se descargan cuando corresponde; el rendimiento depende del equipo. |
| «Oye Vox» en el Mac | Activación opcional, incluso con la burbuja cerrada. | La app debe estar ejecutándose; no despierta un Mac suspendido. No está trasladado al ESP32. |
| Licencia Pro | Activación firmada manual y comprobación de acceso en app y backend. | No existe todavía compra automática ni gestión comercial completa. |

La implementación combina **Electron** para el escritorio y **Python/FastAPI** para el motor, con adaptadores de modelos y herramientas locales. Se conservan configuración y memoria entre versiones.

La última entrega se comprobó con **131 pruebas automatizadas** y verificaciones del paquete. Muchas acciones se probaron con simulaciones para no tocar aplicaciones ni datos personales. Esto **no sustituye una beta con usuarios y equipos distintos**.

## 3. Habilidades actuales

### Abrir y cerrar aplicaciones

- Elegir en Ajustes qué aplicaciones están autorizadas.
- Pedir por texto o voz «abre Notas» o «cierra Notas».
- Solicitar cierre normal; respetar los avisos de documentos sin guardar.
- No forzar procesos ni descartar cambios.

**El alcance sobre aplicaciones termina ahí:** no controla su contenido, no pulsa botones dentro de ellas y no reproduce música. El control musical fue retirado de la versión activa a petición del creador.

### Buscar y organizar archivos

- Buscar por nombre o extensión en las carpetas autorizadas.
- Usar los resultados de una búsqueda para preparar su agrupación.
- Preparar organización del Escritorio en carpetas por tipo, reutilizando las existentes cuando corresponde.
- Mostrar una vista previa antes de mover archivos y disponer de mecanismos para deshacer las operaciones compatibles.

La búsqueda por nombre no implica abrir el contenido de todos los archivos. Las herramientas conservan permisos y confirmaciones para las operaciones correspondientes.

### Consultar internet

- Pedir búsquedas directamente en el chat, sin un botón obligatorio de «Internet».
- Mostrar fuentes o indicar que no se obtuvieron resultados verificables.

Las búsquedas pueden fallar por disponibilidad o bloqueos de los servicios. No hay un navegador autónomo general integrado para operar cualquier sitio.

### Voz y memoria

- Conversar sin pulsar el micrófono para cada turno dentro de los modos implementados.
- Activar «Oye Vox» en el Mac y silenciarlo.
- Guardar y consultar recuerdos.

Todavía **no** es una conversación natural de nivel Jarvis: falta resolver mejor cuándo interrumpir, cómo evitar escuchar su propia bocina y cómo mantener referencias entre tareas de varios pasos.

## 4. Dispositivo físico y carcasa

Se está considerando una **Seeed Studio XIAO ESP32-C6** como terminal de voz. La compra del resto del kit está prevista para este mes.

### Lo que ya está hecho

- El **frontal de la carcasa V3 ya fue impreso** y el creador confirmó que salió bien.
- El diseño revisado tiene un núcleo de **90 mm**, pared de **2.4 mm** y unión posterior con guía y cuatro clips.
- Hay scripts de Fusion para bandeja de electrónica, alojamiento de bocina, micrófono y tapa con paso USB-C.

### Qué falta comprobar

- Módulo exacto de pantalla y su soporte: las dimensiones reservadas son provisionales.
- Alineación del puerto del micrófono con el conducto impreso.
- Circuito y altura real de la PCB portadora.
- Medidas y fijación del conector USB-C.
- Alimentación, batería, espacio para cables y aislamiento acústico.

**No hay un motivo demostrado para rehacer todo.** La propuesta es conservar el frontal y adaptar piezas interiores, bisel y tapa posterior. La revisión se hizo sobre scripts y cálculos; falta validar el ensamblaje y los componentes físicos.

Los componentes previstos incluyen pantalla GC9A01, micrófono I²S, amplificador MAX98357A, bocina y alimentación. La lista técnica está en `hardware/COMPRA-Y-REVISION-GHOST-XIAO-C6.txt`, si se comparte junto a este resumen.

### Reparto de funciones previsto

| Parte | Responsabilidad prevista |
|---|---|
| ESP32 | Capturar audio, enviarlo por Wi-Fi, reproducir respuestas y mostrar estados. |
| Computadora con Vóxeles | Transcripción, memoria, modelo de IA y ejecución de herramientas autorizadas. |
| Servicios opcionales | Modelos o voces externos, según la configuración y sus costes. |

La C6 se plantea como terminal dependiente de la computadora. La escucha avanzada y la interrupción durante reproducción aún requieren validación. No se ha prometido que «Oye Vox» pueda configurarse localmente en esa placa solo cambiando un texto.

## 5. Qué NO está implementado todavía

- Conexión del ESP32 con Vóxeles y audio de ida y vuelta.
- Firmware validado para la placa, pantalla, audio y conexiones elegidas.
- Experiencia de voz con interrupciones y cancelación de eco plenamente probada.
- Recordatorios, timers y calendario.
- Integraciones de Telegram y WhatsApp.
- Ejecución autónoma general de tareas largas o control del contenido de aplicaciones.
- Compra automática, envío comercial de activaciones, límite de equipos y revocación online.
- Actualizaciones automáticas de la app.
- Distribución pública terminada con firma y notarización de macOS.

**Windows y Linux están siendo porteados por otro agente.** Todavía falta integrar sus resultados y comprobar instaladores, permisos y funciones en cada sistema.

**MusicKit y la reproducción musical están apartados.** El acceso a Apple Developer mostró problemas y esta integración no forma parte de la versión activa. No hay que dedicarle prioridad ahora.

## 6. Free y Pro: lo que existe y lo que se está reconsiderando

La decisión implementada actualmente es **una sola app**:

- **Free:** Ollama local y Gemini con clave propia, junto con memoria, voz local y herramientas básicas.
- **Pro:** los demás proveedores compatibles, endpoints personalizados y Ollama remoto.
- No hay una selección artificial de modelos permitidos por nombre: se usan los disponibles en el proveedor/equipo.
- La licencia de Vóxeles **no incluye créditos de IA** ni garantiza uso ilimitado de Gemini.

La beta usa activaciones firmadas emitidas manualmente. No se ha conectado una tienda, no hay precio definitivo y no se ha establecido pago único o suscripción. No se ha asignado una activación Pro personal al creador desde esta conversación.

**Esta división comercial sigue abierta a revisión.** Después de implementarla, el creador cuestionó si cobrar por más proveedores ofrece suficiente valor, ya que muchas funciones pueden obtenerse gratis o configurarse por separado. No se ha retirado el control Free/Pro del código, pero tampoco debe tratarse como un modelo de negocio validado.

El creador tiene PayPal y está abierto a otra plataforma más conveniente. Se mencionó Lemon Squeezy como candidata para venta y licencias; no hay una tienda aprobada ni integración activa. La clave privada para emitir activaciones pertenece al titular y no debe compartirse con compradores o colaboradores.

## 7. Preocupaciones expresadas por el creador

1. **No perder la idea original.** El objetivo es un compañero físico tipo Jarvis; añadir proveedores y resolver detalles técnicos empezó a sentirse alejado de esa experiencia.
2. **Encontrar algo por lo que realmente quieran pagar.** Preocupa cobrar por funciones que ya existen gratis o que pueden montarse con otras herramientas.
3. **No encarecer demasiado el producto.** Ya hubo dudas sobre precios altos; se quiere empezar con algo accesible y escuchar feedback.
4. **Controlar costes de desarrollo y de IA.** Se quiere evitar gastar innecesariamente en iteraciones de Codex y no asumir sin límites el consumo de los compradores.
5. **Que la IA haga cosas reales y no lo aparente.** Antes llegó a decir que organizaba archivos sin haberlo hecho; se añadieron herramientas y resultados verificables para evitarlo.
6. **Una interacción cómoda.** Se pidió dejar la ventana tradicional por una burbuja y usar la voz sin pulsar botones en cada turno.
7. **Reutilizar lo que ya existe.** Aprovechar el frontal impreso y los componentes disponibles, evitando compras y reimpresiones innecesarias.
8. **Tener permisos claros.** Abrir/cerrar solo apps autorizadas y revisar movimientos de archivos; no convertir el asistente en un ejecutor libre de comandos.
9. **Mantener identidad propia.** El proyecto comenzó con referencias a Ghost/Destiny y luego se trabajó un rebranding. La identidad y el diseño del producto comercial necesitan seguir resolviéndose antes de una venta pública.
10. **Validar que haya interés.** Todavía no hay una base de compradores ni feedback suficiente que justifique funciones, precios o suscripción.

## 8. Posibles formas de venderlo

Estas son **hipótesis para discutir**, no decisiones cerradas ni previsiones de ingresos.

| Opción | Por qué alguien pagaría | Qué habría que resolver |
|---|---|---|
| App Pro | Comodidad, integración y funciones adicionales útiles. | Demostrar valor más allá de seleccionar otra API. |
| Kit Maker | Carcasa, componentes compatibles, instrucciones y ahorro de búsqueda/pruebas. | Lista verificada, disponibilidad, montaje y soporte para quien lo construye. |
| Dispositivo terminado | Recibir un compañero armado, probado y fácil de configurar. | Costes reales, fabricación, calidad, configuración inicial, soporte y devoluciones. |
| Servicio opcional | IA/voz incluidas o servicios continuos mantenidos por el proyecto. | Servidor propio, límites de consumo, seguridad, coste por usuario y margen sostenible. |

La propuesta más reciente fue explorar **el valor del producto físico integrado**, sin asumir que necesite suscripción para las funciones locales. El cobro no tiene por qué estar dentro del ESP32: podría corresponder a la compra del dispositivo y, si se ofrece, a un servicio gestionado desde la app/cuenta.

Si el usuario pone su propia API, el proyecto no paga ese consumo. Si el proyecto ofrece IA y voz incluidas, tendría que cubrirlos mediante un servicio controlado; nunca distribuyendo una clave privada común dentro del dispositivo o instalador.

## 9. Referencias que inspiran la visión

- [Hermes Agent](https://hermes-agent.nousresearch.com/): referencia para pensar memoria, herramientas y tareas de un agente.
- [Fish Audio](https://fish.audio/es/): posible proveedor de voz más expresiva.
- [ElevenLabs](https://elevenlabs.io/): posible proveedor de voz/conversación.
- [xiaozhi-esp32](https://github.com/78/xiaozhi-esp32): posible base o referencia para el dispositivo de voz.

**Ninguno de estos enlaces significa que ya esté integrado en Vóxeles.** No se ha decidido incorporar todos ni sustituir el motor actual por Hermes.

## 10. En qué puede ayudar tu opinión

- ¿A quién le resolvería algo: aficionados Maker, personas que quieren un asistente listo para usar, o un nicho concreto?
- ¿Qué tres tareas justificarían tener este objeto en el escritorio todos los días?
- ¿Tendría más sentido vender un kit, un dispositivo terminado o solo software?
- ¿Qué parte pagarías por recibir ya resuelta, aunque las herramientas base sean gratuitas?
- ¿Qué configuración tolerarías: instalar Ollama, introducir una API o solo conectarlo al Wi-Fi?
- ¿Qué haría que lo dejaras de usar después de una semana?
- ¿Qué prueba pequeña podríamos hacer con unas pocas personas antes de diseñar una tienda y fabricar más unidades?

## 11. Próximo objetivo propuesto para validar el producto

**Un prototipo físico que escuche una petición, la envíe a Vóxeles y responda por su bocina, conservando el frontal impreso.** Primero puede activarse con botón; después se evalúa «Oye Vox» y una conversación más natural.

Ese prototipo permitiría preguntar a usuarios reales si la experiencia aporta valor. La lista de funciones de pago, el precio y la necesidad de una suscripción deberían decidirse con esa evidencia, en lugar de seguir agregando funciones sin comprobar el uso.

---

**Este resumen se puede compartir sin claves API, activaciones reales ni la clave privada del emisor. No representa un producto comercial terminado.**
