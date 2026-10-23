"""Carregamento mínimo de .env sem dependência externa.

Valores já presentes no ambiente têm precedência. Isso permite usar secrets de
CI, do Windows ou de um gerenciador de credenciais sem sobrescrita acidental.
"""

import os
import re
from pathlib import Path


_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_dotenv(path: Path) -> int:
    """Carrega pares ``NOME=valor`` se o arquivo existir e retorna a quantidade."""
    if not path.is_file():
        return 0
    loaded = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not _NAME.fullmatch(name):
            raise ValueError(f"Linha inválida no arquivo de ambiente: {name or '<vazia>'}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name not in os.environ:
            os.environ[name] = value
            loaded += 1
    return loaded
