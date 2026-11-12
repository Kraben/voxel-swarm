"""Shared signed-grant contract. No payment secrets are embedded in clients."""
import os,json,time,base64
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
class LicenseRequired(ValueError):pass

def verify_license(token,key=None,now=None):
    try:
        if key is None:key=json.loads((Path(__file__).parent/'commercial/license-public-key.json').read_text())['public_key']
        if not isinstance(token,str) or len(token)>8192 or not key:return {'plan':'free'}
        payload,signature=token.split('.')
        import re
        if not all(re.fullmatch(r'[A-Za-z0-9_-]+',p) for p in (payload,signature)):raise ValueError()
        decode=lambda v:base64.urlsafe_b64decode(v+'='*((-len(v))%4))
        public=load_pem_public_key(key.encode())
        if not isinstance(public,Ed25519PublicKey):raise ValueError()
        public.verify(decode(signature),payload.encode('ascii'))
        c=json.loads(decode(payload));now=int(time.time()) if now is None else now
        if type(c.get('v')) is not int or c.get('v')!=1 or c.get('product')!='voxel-swarm' or c.get('plan')!='pro' or not isinstance(c.get('id'),str) or len(c['id'])>100 or any((type(c.get(k)) is not int or abs(c[k])>9007199254740991) for k in ('iat','exp')) or c['iat']>now+300 or c['exp']<=now or c['exp']<=c['iat']:raise ValueError()
        return {'plan':'pro','expiresAt':c['exp'],'id':c['id']}
    except Exception:return {'plan':'free'}

def current():
    try:return verify_license(json.loads(Path(os.environ['GHOST_LICENSE_FILE']).read_text())['token'])
    except (KeyError,OSError,ValueError,TypeError):return {'plan':'free'}

def free_provider(provider,host):
    try:
        u=urlsplit(host)
        if u.username or u.password or u.query or u.fragment:return False
        if provider=='ollama':return u.scheme in ('http','https') and u.hostname in ('127.0.0.1','localhost','::1') and u.path in ('','/')
        return provider=='openai' and u.scheme=='https' and u.hostname=='generativelanguage.googleapis.com' and u.port in (None,443) and u.path.rstrip('/')=='/v1beta/openai'
    except ValueError:return False

def require_provider():
    if os.getenv('GHOST_LICENSE_ENFORCE','1')=='0':return
    provider=os.getenv('GHOST_PROVIDER','ollama');host=os.getenv('GHOST_API_BASE','') if provider=='openai' else os.getenv('OLLAMA_HOST','http://127.0.0.1:11434')
    if not free_provider(provider,host) and current()['plan']!='pro':raise LicenseRequired('Este proveedor requiere Vóxeles Pro. Free incluye Ollama local y Gemini. Cambia de proveedor o activa tu licencia en Ajustes.')
