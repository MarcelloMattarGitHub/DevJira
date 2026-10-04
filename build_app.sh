#!/bin/zsh
# Gera dist/Jira.app
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/pyinstaller --noconfirm --windowed --name Jira \
  --osx-bundle-identifier com.marcellomattar.jira \
  --paths src src/main.py
echo "Pronto: $(pwd)/dist/Jira.app"
