# Free / Pro y distribución — 0.7.3

## Aprobado e implementado en esta beta
Una sola app. Free: Ollama local y Gemini con la clave del usuario. Pro: demás proveedores, endpoints personalizados y Ollama remoto. No se restringe el nombre de los modelos; sí el endpoint real del proveedor. Memoria, voz local y herramientas básicas continúan en Free. El control de Música está retirado. Las apps autorizadas solo se abren o reciben una solicitud de cierre normal; MusicKit está archivado.

La configuración y las llamadas al proveedor se comprueban en Electron y Python. El instalador arranca sin licencia en Free. Un proveedor Pro guardado anteriormente se conserva, pero sus consultas se bloquean hasta activar Pro o cambiar a una opción Free. No se borran recuerdos, conversaciones ni claves API. Comprar Pro no concede permisos del sistema ni incluye consumo de IA.

Ajustes permite consultar el plan y pegar una activación firmada. Este es un mecanismo beta manual, sin plataforma de cobro conectada. No se aceptan claves de una tienda externa directamente. Precio, pago único/suscripción y proveedor de pagos siguen pendientes de decisión.

## Emisor y formato
Se usa Ed25519 con el mismo contrato en desktop/licensing.cjs y licensing.py. La clave pública comercial está en license-public-key.json y se incluye tanto con Electron como con el backend. La clave privada del titular se conserva fuera del proyecto, en el directorio de trabajo del titular, y no se incluye en los ZIP. No compartirla con compradores ni con el agente del port.

El emisor de desarrollo desktop/issue-license.cjs NO se empaqueta con la app. Para emitir una activación manual desde la raíz del proyecto:

```sh
node desktop/issue-license.cjs --private-key /ruta/privada/issuer-private.pem --days 30 --output /ruta/privada/activacion-cliente.txt
```

El archivo generado contiene el token para pegar en Ajustes. Emitirlo no registra ni comprueba un pago. No ejecutar --init otra vez: cambiar la clave pública invalidaría activaciones existentes. Guardar una copia segura de la clave privada del titular antes de emitir licencias para clientes. No publicar activaciones reales en ejemplos ni tests.

Una activación vence en la fecha firmada; quitarla localmente vuelve a Free. En esta beta no hay límite de dos dispositivos, revocación online, transferencia de puestos ni siete días adicionales de gracia. Una activación copiada puede usarse en otros equipos hasta que venza. Estos límites comerciales necesitan una integración de activación con servidor/proveedor y no deben prometerse como implementados. El cliente de escritorio puede modificarse; no existe protección absoluta contra copia.

## Cobro pendiente
Recomendación por evaluar: Lemon Squeezy, que ofrece claves y API de activación/validación/desactivación. La tienda requiere aprobación del titular. Su clave comercial no es el token de esta beta: hace falta implementar el adaptador/servicio que valide compra, producto, variante y entorno antes de emitir permisos firmados. Si hay servicio propio, verificar webhooks, idempotencia, reembolsos y revocación; nunca aceptar el regreso del checkout como comprobante. No incluir claves administrativas o secretos de webhooks en clientes.

No hay ventas activas, checkout ni renovación automática. Calendario, recordatorios y mensajería están pendientes y no deben anunciarse como disponibles. El titular debe aprobar precio, alcance de actualizaciones, reembolsos y términos antes de cobrar.

## Distribución
La compilación macOS actual es una beta para Apple Silicon sin firma Developer ID ni notarización. La clave de firma de licencias es distinta de la identidad de firma de Apple: no resuelve Gatekeeper. Apple Developer sigue pendiente para distribución pública firmada/notarizada.

Windows/Linux están con otro agente. Compartir PORT-WINDOWS-LINUX-FREE-PRO.txt y los cambios de código; conservar la misma clave pública y lógica, sin reemplazar sus adaptaciones del sistema.

Primera distribución: una descarga por plataforma/arquitectura realmente probada, alojada en Releases u otro almacenamiento estable. desktop/make_release_manifest.py genera tamaño y SHA256; no publica ni sustituye firma del editor. Comenzar con actualización manual; autoactualización firmada y preservación de datos requieren implementación y prueba por SO.

## Pruebas
La suite anterior puede ejecutarse con GHOST_LICENSE_ENFORCE=0 solo para pruebas de transporte simulado. Las pruebas nuevas de licencia fuerzan la comprobación activa. La app Electron siempre inicia el backend con GHOST_LICENSE_ENFORCE=1, sin respetar el valor heredado. Nunca distribuir una app modificada con ese control desactivado.

Antes de vender: compra/activación sandbox completa, producto incorrecto, expiración, reembolso/revocación con servicio real, límites de dispositivos y pruebas de actualizaciones e instaladores. Hasta completar esa integración comercial, describir esta versión como beta con activación manual.
