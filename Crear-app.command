#!/bin/zsh
set -e
cd -- "${0:A:h}"
./Preparar-motor.command
# Usa Xcode instalado sin cambiar la selección global del sistema.
export DEVELOPER_DIR=${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}
xcodebuild -project macos/GhostAI.xcodeproj -scheme GhostAI -configuration Release -derivedDataPath work/xcode CODE_SIGNING_ALLOWED=NO build
mkdir -p dist
 ditto 'work/xcode/Build/Products/Release/Enjambre de Vóxeles.app' 'dist/Enjambre de Vóxeles.app'
print '\nApp creada en dist/Enjambre de Vóxeles.app. Compilación local sin firma de distribución.'
