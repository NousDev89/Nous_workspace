from pathlib import Path


def list_skills(root):
    root = Path(root).resolve()
    if not root.exists():
        return []
    result = []
    for path in sorted(root.glob("*/SKILL.md")):
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or resolved.stat().st_size > 64_000:
            continue
        result.append({"id": path.parent.name, "instructions": resolved.read_text(encoding="utf-8")})
    return result


def select_skills(root, names):
    catalog = {item["id"]: item for item in list_skills(root)}
    missing = set(names) - catalog.keys()
    if missing:
        raise ValueError("Habilidades não encontradas: " + ", ".join(sorted(missing)))
    return [catalog[name] for name in dict.fromkeys(names)]
