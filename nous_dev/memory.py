"""Memória compartilhada entre os nós do grafo.

O banco SQLite continua sendo o registro local e auditável do projeto.  Quando
configurada explicitamente, a plataforma Mem0 fornece uma segunda camada de
busca semântica.  Nenhum dado é enviado ao Mem0 sem que o backend ``mem0``
esteja selecionado e uma chave esteja presente no ambiente.
"""

import os


class SharedMemory:
    """Fachada de memória que preserva o escopo de cada projeto."""

    def __init__(self, store, config):
        self.store = store
        memory_config = config.get("memory", {})
        self.backend = memory_config.get("backend", "sqlite")
        self.api_key_env = memory_config.get("api_key_env", "MEM0_API_KEY")
        self.namespace = memory_config.get("namespace", "nous-workstation")
        self.client = None
        self.detail = "Memória local SQLite"

        if self.backend == "sqlite":
            return
        if self.backend != "mem0":
            raise ValueError("memory.backend deve ser 'sqlite' ou 'mem0'.")

        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise ValueError(
                f"Defina {self.api_key_env} antes de ativar memory.backend=mem0."
            )
        try:
            from mem0 import MemoryClient
        except ImportError:
            raise ValueError(
                "Instale o extra de memória: python -m pip install -e .[mem0]"
            ) from None
        self.client = MemoryClient(api_key=api_key)
        self.detail = "Mem0 Platform (busca semântica)"

    def _user_id(self, project):
        """O user_id é estável e impede mistura de memórias entre projetos."""
        return f"{self.namespace}:{project}"

    def status(self):
        return {"backend": self.backend, "detail": self.detail}

    def add(self, project, content, source="user"):
        if self.backend == "sqlite":
            return self.store.add_memory(project, content, source)
        response = self.client.add(
            [{"role": "user", "content": content}],
            user_id=self._user_id(project),
            metadata={"project": project, "source": source},
        )
        if isinstance(response, dict):
            return response.get("id") or response.get("message") or "mem0"
        return "mem0"

    def search(self, project, query="", limit=10):
        if self.backend == "sqlite":
            # A busca literal oferece relevância semântica limitada no modo
            # offline. Complete-a com contexto recente do mesmo projeto para
            # que os nós compartilhem decisões importantes mesmo quando a
            # formulação atual não repete as mesmas palavras.
            relevant = self.store.search(project, query, limit)
            if not query or len(relevant) >= limit:
                return relevant
            recent = self.store.search(project, "", limit)
            known = {item["id"] for item in relevant}
            return (relevant + [item for item in recent if item["id"] not in known])[:limit]
        # O filtro mantém o namespace mesmo que a API altere a estratégia de
        # resolução do user_id no futuro.
        response = self.client.search(
            query or "contexto do projeto",
            filters={"user_id": self._user_id(project)},
            limit=max(1, min(limit, 100)),
        )
        records = response.get("results", []) if isinstance(response, dict) else []
        normalized = []
        for item in records:
            if not isinstance(item, dict):
                continue
            content = item.get("memory") or item.get("content")
            if isinstance(content, str) and content.strip():
                normalized.append({
                    "id": str(item.get("id", "mem0")),
                    "project": project,
                    "content": content,
                    "source": item.get("metadata", {}).get("source", "mem0"),
                    "created_at": item.get("created_at"),
                    "score": item.get("score"),
                })
        return normalized
