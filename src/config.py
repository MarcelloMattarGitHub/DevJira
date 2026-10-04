"""Configuração de acesso ao Jira (URL, e-mail e API token).

Fica em ~/Library/Application Support/Jira/config.json, para funcionar tanto
rodando o script quanto dentro do Jira.app.
"""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Jira"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(url: str, email: str, token: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"url": url, "email": email, "token": token}, indent=2),
        encoding="utf-8",
    )
    CONFIG_FILE.chmod(0o600)  # contém o token
