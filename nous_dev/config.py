import json
from pathlib import Path
from .env import load_dotenv


def load_config(path: str = "nous.config.json") -> dict:
    location = Path(path).resolve()
    load_dotenv(location.parent / ".env")
    raw = json.loads(location.read_text(encoding="utf-8"))
    if raw.get("version") != 1:
        raise ValueError("Versão de configuração não suportada.")
    base = location.parent
    for key, default in (("data_dir", ".nous"), ("workspace", "."), ("skills_dir", "skills")):
        raw[key] = (base / raw.get(key, default)).resolve()
    raw["base_dir"] = base
    return raw
