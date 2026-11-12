"""Descubrimiento y catálogo local de aplicaciones en macOS, Windows y Linux."""
from pathlib import Path
import json
import os
import system_adapters

SPANISH_NAMES = system_adapters.SPANISH_NAMES
ALIASES = system_adapters.ALIASES
normalize = system_adapters.normalize


def default_roots():
    return system_adapters.get_adapter().default_roots()


def installed_apps(roots=None):
    return system_adapters.get_adapter().installed_apps(roots=roots)


def allowed_ids():
    raw = os.getenv('GHOST_ALLOWED_APPS_JSON')
    if raw is None:
        return [item.strip() for item in os.getenv('GHOST_ALLOWED_APPS', 'calculator,notes').split(',') if item.strip()]
    try:
        data = json.loads(raw)
        if (
            not isinstance(data, list)
            or len(data) > 256
            or any(not isinstance(item, str) or len(item) > 1024 or any(ord(c) < 32 for c in item) for item in data)
        ):
            return []
        return data
    except (ValueError, TypeError):
        return []


def permitted(app, selection=None):
    selection = allowed_ids() if selection is None else selection
    return any(item == app['id'] if (item.startswith('/') or (len(item) > 2 and item[1] == ':')) else normalize(item) in app['aliases'] for item in selection)


def resolve_app(name, apps=None):
    apps = installed_apps() if apps is None else apps
    wanted = normalize(name)
    for suffix in (' por favor', ' porfa'):
        if wanted.endswith(suffix):
            wanted = wanted[:-len(suffix)].strip(' ,')
    wanted = ALIASES.get(wanted, wanted)
    matches = [row for row in apps if wanted in row['aliases']]
    if not matches:
        return None, 'No encontré esa aplicación instalada. Usa el nombre que aparece en Ajustes.'
    selected = [row for row in matches if permitted(row)]
    if not selected:
        return None, 'Aplicación fuera de tu lista permitida. Márcala en Ajustes → Aplicaciones permitidas.'
    if len(selected) > 1:
        return None, 'Hay varias aplicaciones con ese nombre. Deja seleccionada solo la que quieres abrir en Ajustes.'
    return selected[0], None
