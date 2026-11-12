"""Ejecutor común: solo funciones conocidas; nunca comandos o rutas del modelo."""
import os
from pathlib import Path
import agent_tools,desktop_actions,file_actions,group_actions,skills_mac,web_actions

def execute(call,session,data,*,confirmed=False,public=False,request_text=None):
    # Se vuelve a validar contra permisos actuales, también al confirmar.
    tools=agent_tools.available(local=not public,skills=os.getenv('GHOST_ENABLE_SKILLS','0')=='1',web=os.getenv('GHOST_ENABLE_WEB','1')=='1',text='')
    call=agent_tools.validate({'function':{'name':call['name'],'arguments':call['arguments']}},tools)
    name=call['name'];args=call['arguments']
    if name=='core_find_files' and not confirmed:
        return {'requiere_confirmacion':True,'respuesta':'Buscaré por nombre o extensión: '+args['term']}
    result={'accion':None,'fuentes':None,'busqueda':None}
    if name=='core_search_web':
        sources=web_actions.search(args['query']);result.update(fuentes=sources,busqueda={'query':args['query'],'automatic':True})
        result['respuesta']='Fuentes relacionadas con tu búsqueda (extractos del buscador):\n\n'+'\n\n'.join(f"{i}. {r['title']}\n{r['body']}" for i,r in enumerate(sources,1)) if sources else 'No encontré fuentes relacionadas. No inventaré resultados.'
    elif name=='core_find_files':
        found=[];result['respuesta']=file_actions.search(args['term'],capture=found)
        group_actions.GroupActions(data).remember(session,found)
    elif name in ('core_group_results','core_undo_group'):
        manager=group_actions.GroupActions(data)
        result['accion']=manager.undo_plan(session) if name=='core_undo_group' else manager.plan(session,os.getenv('GHOST_DESKTOP_ROOT',str(Path.home()/'Desktop')))
        result['respuesta']='Vista previa local: revisa los archivos y confirma los movimientos. Todavía no he movido nada.'
    elif name=='core_desktop_plan':
        manager=desktop_actions.DesktopActions(os.getenv('GHOST_DESKTOP_ROOT',str(Path.home()/'Desktop')),data)
        result['accion']=manager.undo_plan(session) if args['operation']=='undo' else manager.plan(session)
        result['respuesta']='Vista previa local: revisa el plan del Escritorio y confirma los movimientos. Todavía no he movido nada.'
    elif name=='core_close_app':
        if not skills_mac.cierre_pedido(request_text or '',args['name']):
            result['respuesta']='Pide cerrar una app autorizada directamente, por ejemplo: «cierra Notas». No cerré ninguna aplicación.'
        else:result['respuesta']=skills_mac.ejecutar_skill('cierra '+args['name'])
    elif name=='core_open_app':
        if not skills_mac.apertura_pedida(request_text or '',args['name']):
            result['respuesta']='Para abrir una app autorizada, pídemelo directamente, por ejemplo: «abre Safari». No abrí ninguna aplicación.'
        else:result['respuesta']=skills_mac.ejecutar_skill('abre '+args['name'])
    return result
