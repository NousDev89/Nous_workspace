from pathlib import Path


class WorkspaceTools:
    """Ferramentas de arquivo: acessam somente o workspace configurado."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def resolve(self, relative):
        path = Path(relative)
        if path.is_absolute():
            raise ValueError("Use um caminho relativo ao workspace.")
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("O caminho está fora do workspace.")
        if any(part in {".git", ".nous", ".venv"} or part.startswith(".env")
               for part in target.relative_to(self.root).parts):
            raise ValueError("Diretório interno ou arquivo de credenciais bloqueado.")
        return target

    def read(self, relative):
        target = self.resolve(relative)
        if not target.is_file():
            raise ValueError("Arquivo não encontrado.")
        if target.stat().st_size > 256_000:
            raise ValueError("Arquivo excede o limite de leitura de 256 KB.")
        return target.read_text(encoding="utf-8")

    def list(self, relative="."):
        target = self.resolve(relative)
        if not target.is_dir():
            raise ValueError("Diretório não encontrado.")
        result = []
        for child in sorted(target.iterdir()):
            try:
                self.resolve(child.relative_to(self.root))
            except ValueError:
                continue
            result.append({"path": str(child.relative_to(self.root)), "directory": child.is_dir()})
        return result
