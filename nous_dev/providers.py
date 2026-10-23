import json
import subprocess
import sys


class DemoProvider:
    def complete(self, request):
        return (
            "[DEMONSTRAÇÃO — sem chamada de IA]\n"
            f"Etapa: {request['stage']}\n"
            f"Pedido: {request['prompt']}\n"
            f"Memórias recebidas: {len(request['memories'])}\n"
            f"Etapas anteriores recebidas: {len(request['previous'])}\n"
            "Fluxo e persistência exercitados; nenhum trabalho de programação foi executado."
        )


class CommandProvider:
    def __init__(self, spec, cwd, allowed=False):
        if not allowed:
            raise ValueError("Adaptadores de processo exigem --allow-commands.")
        if not spec.get("enabled", False):
            raise ValueError("Provedor desativado na configuração.")
        argv = spec.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv):
            raise ValueError("Configure argv como uma lista não vazia de argumentos.")
        self.argv = [sys.executable if x == "{python}" else x for x in argv]
        self.cwd = cwd
        self.timeout = float(spec.get("timeout_seconds", 120))
        if not 0 < self.timeout <= 600:
            raise ValueError("timeout_seconds deve estar entre 0 e 600.")

    def complete(self, request):
        try:
            result = subprocess.run(
                self.argv, input=json.dumps(request, ensure_ascii=False),
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", shell=False, timeout=self.timeout, cwd=self.cwd)
        except subprocess.TimeoutExpired:
            raise RuntimeError("O adaptador excedeu o tempo limite.") from None
        except OSError:
            raise RuntimeError("Não foi possível iniciar o adaptador. Confira argv.") from None
        if result.returncode:
            # stderr pode conter segredos. Não o persistir ou imprimir.
            raise RuntimeError(f"O adaptador terminou com código {result.returncode}.")
        try:
            response = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("O adaptador deve retornar JSON com o campo text.") from None
        if not isinstance(response, dict) or not isinstance(response.get("text"), str):
            raise RuntimeError("Resposta do adaptador sem campo text válido.")
        if not response["text"].strip():
            raise RuntimeError("O adaptador retornou texto vazio.")
        return response["text"]


def get_provider(name, config, allowed=False):
    spec = config.get("providers", {}).get(name)
    if spec is None:
        raise ValueError(f"Provedor desconhecido: {name}")
    if spec.get("kind") == "demo":
        return DemoProvider()
    if spec.get("kind") == "command":
        return CommandProvider(spec, config["base_dir"], allowed)
    raise ValueError("Tipo de provedor não suportado.")
