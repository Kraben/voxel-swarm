"""Private loopback bridge to the signed native MusicKit app, without cloud secrets."""
import os
from urllib.parse import urlsplit
import httpx

def execute(command):
    endpoint=os.getenv('GHOST_MUSICKIT_ENDPOINT','')
    token=os.getenv('GHOST_MUSICKIT_TOKEN','')
    try:
        url=urlsplit(endpoint)
        if url.scheme!='http' or url.hostname!='127.0.0.1' or url.path!='/music' or not url.port or url.username or url.password or url.query or url.fragment or len(token)<32:
            return 'MusicKit no está preparado. Instala el componente firmado y conecta Apple Music desde Ajustes.'
        with httpx.Client(trust_env=False,timeout=28,follow_redirects=False) as client:
            response=client.post(endpoint,headers={'Authorization':'Bearer '+token},json=command)
            response.raise_for_status()
            data=response.json()
        value=data.get('message')
        return value[:1000] if isinstance(value,str) and value else 'MusicKit no confirmó el resultado. Revisa su conexión en Ajustes.'
    except (ValueError,OSError,httpx.HTTPError):
        return 'No pude comunicarme con MusicKit. Revisa su conexión en Ajustes.'
