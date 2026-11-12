#!/bin/zsh
set -e
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements-mac.txt
.venv/bin/python desktop/build_overlay.py
print '\nVoxelSwarm.app está en desktop/release/mac-arm64 o mac, según tu Mac.'
