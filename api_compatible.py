import licensing
"""Adaptador de chat/completions. Admite selección de herramientas; la ejecución pertenece a Ghost."""
import os
import httpx
from urllib.parse import urlsplit

def request_headers():
    key = os.getenv("GHOST_API_KEY", "")
    headers = {"Authorization":"Bearer "+key} if key else {}
    if urlsplit(os.getenv("GHOST_API_BASE", "")).hostname == "generativelanguage.googleapis.com":
        headers["x-goog-api-client"] = "ghost-overlay/0.3.2"
    return headers

def chat(model, messages, *, tools=None):
    licensing.require_provider()
    base = os.environ['GHOST_API_BASE'].rstrip('/')
    key = os.getenv('GHOST_API_KEY', '')
    payload={'model':model,'messages':messages,'stream':False}
    if tools:payload.update(tools=tools,tool_choice='auto')
    response = httpx.post(base + '/chat/completions', headers=request_headers(), json=payload,timeout=90,follow_redirects=False)
    response.raise_for_status()
    data = response.json()
    try:
        message=data['choices'][0]['message'];content=message.get('content')
        if tools and message.get('tool_calls'):
            return {'message':{'role':'assistant','content':content or '', 'tool_calls':message['tool_calls']}}
        if not isinstance(content,str) or not content.strip(): raise ValueError()
    except (KeyError,IndexError,TypeError,ValueError):
        raise ValueError('La API no devolvió una respuesta de chat compatible.') from None
    return {'message':{'role':'assistant','content':content}}

def generate(model, prompt):
    answer = chat(model,[{'role':'user','content':prompt}])
    return {'response':answer['message']['content']}
