"""Búsqueda explícita con motores definidos, filtro de términos y caché breve."""
import html
import logging
import re
import time
from urllib.parse import urlsplit,urlunsplit,parse_qs,unquote
import httpx
from lxml import html as html_parser
import xml.etree.ElementTree as ET
from desktop_actions import normalized

LOGGER=logging.getLogger(__name__)
ENGINES=('duckduckgo','duckduckgo_lite','bing_rss')
STOPWORDS=set('que qué es son quien quién como cómo cuando cuándo donde dónde cual cuál cuales cuáles para por de del la el los las un una unos unas en sobre me mi mis al a y o u se si con sin informacion información acerca the what is are who how when where of a an to and for in about information'.split())
STOPWORDS.update({'dime','explicame','favor','puedes','esta','hace','hay','hoy','ahora','actual','actuales','recientes','ultimas','ultimos'})
CACHE={}

class SearchUnavailable(RuntimeError):pass

def route(text):
    """Decisión local: búsqueda explícita o pregunta informativa, sin otra API."""
    clean=normalized(text)
    # Una instrucción de privacidad prevalece sobre la detección automática.
    if re.search(r'\b(?:sin (?:usar |consultar )?(?:internet|web)|no (?:uses|utilices|consultes) (?:internet|la web)|solo (?:conocimiento )?local)\b',clean):return None
    if re.search(r'\b(?:no|nunca)\b.{0,35}\b(?:busc|investig|averigu)',clean):return None
    if re.match(r'^\s*(?:busca|buscar)\s+(?:(?:el|un|mi|los|mis)\s+)?archivo',clean):return None
    match=re.search(r'\b(?:busca|buscar|investiga|investigar|averigua)\s+(?:en\s+)?(?:internet|la web|web)\s*[:;,]?\s*(.+)$',text,re.I)
    if not match:match=re.match(r'^\s*(?:busca|buscar|investiga|investigar|averigua)\s+(.+)$',text,re.I)
    if match:
        query=match.group(1).strip(' \t\n¿?')
        return {'query':query,'automatic':False} if query else None
    # Conversaciones personales, código y datos identificables no se convierten
    # en consultas públicas por una coincidencia de palabras.
    if len(text)>500 or '```' in text or '\n' in text:return None
    if re.search(r'(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|sk-[A-Za-z0-9_-]{10,}|Bearer\s+\S+|/Users/|/home/|[A-Za-z]:\\)',text,re.I):return None
    if re.search(r'\b(?:mi|mis|me llamo|mi nombre|contrasena|password|clave api|api key|token|recuerdas|memoria|escritorio|archivo)\b',clean):return None
    query=text.strip(' \t\n¿?')
    query=re.sub(r'^(?:por favor[, ]+)?(?:dime|expl[ií]came|puedes decirme|podr[ií]as decirme|me puedes explicar|quiero saber|quisiera saber|sabes)\s+', '',query,flags=re.I).strip(' ¿?')
    candidate=normalized(query)
    factual=re.match(r'^(?:que (?:es|son|significa|significan|se sabe)|quien(?:es)? (?:es|son|fue|fueron)|como (?:funciona|funcionan)|donde (?:esta|estan|queda|quedan))\b',candidate)
    timely=re.search(r'\b(?:noticias|clima|pronostico|cotizacion|tipo de cambio|precio(?:s)?|ultima version|ultimas novedades)\b',candidate)
    requested=bool(re.search(r'[¿?]',text) or re.match(r'^(?:dime|consulta|cual|que|como|hay|noticias|clima|pronostico|cotizacion|precio|ultimas)',clean))
    if factual or (timely and requested):return {'query':query,'automatic':True}
    return None

def query_from(text):
    decision=route(text)
    return decision['query'] if decision else None

def terms(text):
    return {normalized(word) for word in re.findall(r'[^\W_]+(?:\+\+|#)?',text,flags=re.UNICODE)
            if normalized(word) not in STOPWORDS and (len(word)>=3 or word.isupper() or word.endswith(('++','#')))}

def clean_results(rows,query):
    wanted=terms(query);ranked=[];seen=set()
    for row in rows:
        value=str(row.get('href',''))
        try:parsed=urlsplit(value)
        except ValueError:continue
        if parsed.scheme not in ('https','http') or not parsed.hostname or parsed.username or parsed.password:continue
        url=urlunsplit(parsed._replace(fragment=''))
        if url in seen:continue
        title=html.unescape(re.sub(r'<[^>]*>',' ',str(row.get('title','Sin título'))))[:250]
        body=html.unescape(re.sub(r'<[^>]*>',' ',str(row.get('body',''))))
        found=terms(title+' '+body+' '+url)
        overlap=len(wanted & found)/len(wanted) if wanted else 1
        if overlap<0.5:continue
        seen.add(url)
        title_match=len(wanted & terms(title))
        # Son extractos del buscador, no respuestas completas ni afirmaciones verificadas.
        excerpt=re.sub(r'\s+',' ',body).strip()
        if len(excerpt)>420:excerpt=excerpt[:420].rsplit(' ',1)[0]+'…'
        ranked.append((overlap,title_match,{'title':title,'body':excerpt,'url':url}))
    ranked.sort(key=lambda entry:(entry[0],entry[1]),reverse=True)
    return [row for _,__,row in ranked[:5]]

def decode_link(value):
    if value.startswith('//'):value='https:'+value
    parsed=urlsplit(value)
    if parsed.hostname and parsed.hostname.endswith('duckduckgo.com'):
        target=parse_qs(parsed.query).get('uddg')
        if target:return target[0]
    return value

def parse_engine(engine,content):
    if engine=='bing_rss':
        root=ET.fromstring(content)
        return [{'title':row.findtext('title') or '', 'href':row.findtext('link') or '', 'body':row.findtext('description') or ''} for row in root.findall('.//item')]
    tree=html_parser.fromstring(content)
    rows=[]
    if engine=='duckduckgo':
        for block in tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," result ")]'):
            links=block.xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," result__a ")]')
            if not links:continue
            snippet=block.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," result__snippet ")]')
            rows.append({'title':links[0].text_content(),'href':decode_link(links[0].get('href','')),'body':' '.join(node.text_content() for node in snippet)})
    else:
        for link in tree.xpath('//a[contains(concat(" ",normalize-space(@class)," ")," result-link ")]'):
            parent=link.getparent()
            while parent is not None and parent.tag!='tr':parent=parent.getparent()
            snippets=parent.xpath('following-sibling::tr[position()<=2]//*[contains(@class,"result-snippet")]') if parent is not None else []
            rows.append({'title':link.text_content(),'href':decode_link(link.get('href','')),'body':' '.join(node.text_content() for node in snippets)})
    return rows

def fetch_engine(engine,query):
    targets={'duckduckgo':('https://html.duckduckgo.com/html/',{'q':query,'kl':'es-es'}),
             'duckduckgo_lite':('https://lite.duckduckgo.com/lite/',{'q':query,'kl':'es-es'}),
             'bing_rss':('https://www.bing.com/search',{'q':query,'format':'rss','setlang':'es'})}
    url,params=targets[engine]
    with httpx.stream('GET',url,params=params,headers={'User-Agent':'Mozilla/5.0 GhostDesktop/0.4.1','Accept-Language':'es,en;q=0.6'},timeout=8,follow_redirects=True) as response:
        response.raise_for_status();parts=[];size=0
        for part in response.iter_bytes():
            size+=len(part)
            if size>2_000_000:raise ValueError('La respuesta del buscador supera el límite.')
            parts.append(part)
    return parse_engine(engine,b''.join(parts))

def search(query):
    if not query or len(query)>500:raise ValueError('Escribe una búsqueda de hasta 500 caracteres.')
    key=' '.join(normalized(query).split())
    now=time.monotonic();cached=CACHE.get(key)
    if cached and now-cached[0]<300:return [dict(row) for row in cached[1]]
    for engine in ENGINES:
        try:
            rows=fetch_engine(engine,query)
            clean=clean_results(rows,query)
            if clean:
                if len(CACHE)>=128:CACHE.pop(next(iter(CACHE)))
                CACHE[key]=(now,clean)
                return [dict(row) for row in clean]
        except Exception as error:
            LOGGER.warning('Buscador %s no disponible (%s)',engine,type(error).__name__)
    raise SearchUnavailable('No se obtuvieron resultados relacionados con la consulta.')
