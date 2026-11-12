"""Importaciones explícitas para empaquetar todas las dependencias del servidor."""
import os
import sqlite3
import servidor
import uvicorn
if __name__ == '__main__':
    uvicorn.run(servidor.app, host=servidor.BIND, port=int(os.getenv('GHOST_PORT','8000')), proxy_headers=False, workers=1)
