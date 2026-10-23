import json
import os
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _post_json(url, headers, payload, timeout):
    request = Request(
        url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as error:
        # A resposta pode refletir credenciais, prompts ou detalhes privados.
        raise RuntimeError(f"A API respondeu com HTTP {error.code}.") from None
    except URLError:
        raise RuntimeError("Não foi possível conectar à API configurada.") from None
    try:
        parsed = json.loads(body)
    except ValueError:
        raise RuntimeError("A API retornou uma resposta inválida.") from None
    if not isinstance(parsed, dict):
        raise RuntimeError("A API retornou uma resposta em formato inesperado.")
    return parsed


def _require_enabled_network(spec, name, network_allowed):
    if not network_allowed:
        raise ValueError(f"O provedor {name} exige --allow-network.")
    if not spec.get("enabled", False):
        raise ValueError("Provedor desativado na configuração.")
    key_env = spec.get("api_key_env")
    if not isinstance(key_env, str) or not key_env:
        raise ValueError("Configure api_key_env para o provedor.")
    api_key = os.getenv(key_env)
    if not api_key:
        raise ValueError(f"Defina {key_env} no ambiente ou no arquivo .env local.")
    timeout = float(spec.get("timeout_seconds", 120))
    if not 0 < timeout <= 900:
        raise ValueError("timeout_seconds deve estar entre 0 e 900.")
    return api_key, timeout


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


class GrokProvider:
    """Cliente para a Responses API da xAI, sem SDK adicional."""

    def __init__(self, spec, network_allowed=False):
        self.api_key, self.timeout = _require_enabled_network(spec, "grok", network_allowed)
        self.base_url = str(spec.get("base_url", "https://api.x.ai/v1")).rstrip("/")
        self.model = str(spec.get("model", "grok-4.7"))

    def complete(self, request):
        context = {
            "pedido": request["prompt"],
            "memorias": request["memories"],
            "saidas_anteriores": request["previous"],
            "habilidades": request["skills"],
        }
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": request["instructions"]},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        }
        result = _post_json(
            f"{self.base_url}/responses", {"Authorization": f"Bearer {self.api_key}"},
            payload, self.timeout)
        texts = []
        for item in result.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        texts.append(text)
        text = "\n".join(texts).strip()
        if not text:
            raise RuntimeError("Grok não retornou texto de saída.")
        return text


class ManusProvider:
    """Cria uma tarefa Manus v2 e devolve sua URL; não confirma ações externas."""

    def __init__(self, spec, network_allowed=False):
        self.api_key, self.timeout = _require_enabled_network(spec, "manus", network_allowed)
        self.endpoint = str(spec.get("endpoint", "https://api.manus.ai/v2/task.create"))
        self.locale = str(spec.get("locale", "pt-BR"))
        self.agent_profile = str(spec.get("agent_profile", "standard"))

    def complete(self, request):
        context = {
            "instrucoes": request["instructions"],
            "memorias": request["memories"],
            "saidas_anteriores": request["previous"],
            "habilidades": request["skills"],
        }
        payload = {
            "message": {"content": [{
                "type": "text",
                "text": f"{request['prompt']}\n\nContexto:\n{json.dumps(context, ensure_ascii=False)}",
                "visibility": "visible",
            }]},
            "locale": self.locale,
            "interactive_mode": False,
            "share_visibility": "private",
            "agent_profile": self.agent_profile,
            "title": f"Nous: {request['stage']}",
        }
        result = _post_json(
            self.endpoint, {"x-manus-api-key": self.api_key}, payload, self.timeout)
        if not result.get("ok") or not isinstance(result.get("task_id"), str):
            raise RuntimeError("A API Manus não confirmou a criação da tarefa.")
        url = result.get("task_url")
        suffix = f" Abra: {url}" if isinstance(url, str) and url else ""
        return f"Tarefa Manus criada: {result['task_id']}.{suffix}"


def get_provider(name, config, allowed=False, network_allowed=False):
    spec = config.get("providers", {}).get(name)
    if spec is None:
        raise ValueError(f"Provedor desconhecido: {name}")
    if spec.get("kind") == "demo":
        return DemoProvider()
    if spec.get("kind") == "command":
        return CommandProvider(spec, config["base_dir"], allowed)
    if spec.get("kind") == "grok":
        return GrokProvider(spec, network_allowed)
    if spec.get("kind") == "manus":
        return ManusProvider(spec, network_allowed)
    raise ValueError("Tipo de provedor não suportado.")
