#!/bin/zsh
set -e
cd -- "${0:A:h}"
PYTHON_GHOST=${GHOST_PYTHON:-python3}
if [[ ! -x .venv/bin/python ]]; then "$PYTHON_GHOST" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-mac.txt
export PYINSTALLER_CONFIG_DIR="$PWD/work/pyinstaller-cache"
.venv/bin/python -m PyInstaller --noconfirm --clean --onedir --name VoxelBackend --distpath work/backend-dist --workpath work/pyinstaller --specpath work --add-data "$PWD/index.html:." --add-data "$PWD/static:static" --add-data "$PWD/servidor.py:." --hidden-import cerebro_ghost --hidden-import skills_mac --collect-all ddgs --collect-all uvicorn backend_entry.py
mkdir -p macos/GhostAI/Backend
rsync -a --delete work/backend-dist/VoxelBackend/ macos/GhostAI/Backend/
print '\nMotor preparado. Abre macos/GhostAI.xcodeproj y pulsa ▶.'
