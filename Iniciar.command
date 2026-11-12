#!/bin/zsh
set -e
cd -- "${0:A:h}"
if [[ ! -d 'dist/Ghost AI.app' ]]; then ./Crear-app.command; fi
open 'dist/Ghost AI.app'
