import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nous_dev.cli import main
from nous_dev.config import load_config
from nous_dev.env import load_dotenv
from nous_dev.orchestrator import run_task
from nous_dev.memory import SharedMemory
from nous_dev.providers import CommandProvider, get_provider
from nous_dev.store import Store
from nous_dev.tools import WorkspaceTools


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / ".nous" / "test.sqlite3")
        self.config = {
            "base_dir": self.root,
            "skills_dir": self.root / "skills",
            "providers": {"demo": {"kind": "demo"}},
        }

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_memory_is_project_scoped(self):
        self.store.add_memory("a", "usar Python", "user")
        self.store.add_memory("b", "usar outra ferramenta", "other")
        self.assertEqual(len(self.store.search("a", "Python")), 1)
        self.assertEqual(self.store.search("b", "Python"), [])

    def test_shared_memory_defaults_to_local_sqlite(self):
        memory = SharedMemory(self.store, self.config)
        memory.add("a", "memória compartilhada", "user")
        self.assertEqual(memory.status()["backend"], "sqlite")
        self.assertEqual(memory.search("a", "compartilhada")[0]["content"], "memória compartilhada")

    def test_local_shared_memory_includes_recent_project_context(self):
        memory = SharedMemory(self.store, self.config)
        memory.add("a", "a interface será em português", "user")
        self.assertEqual(len(memory.search("a", "criar painel")), 1)

    def test_workflow_passes_memory_and_prior_outputs(self):
        self.store.add_memory("a", "construir com contexto compartilhado")
        seen = []

        class Recording:
            def complete(self, request):
                seen.append(request)
                return request["stage"] + " concluída"

        with patch("nous_dev.orchestrator.get_provider", return_value=Recording()):
            result = run_task(self.store, self.config, "a", "construir")
        self.assertEqual(result["status"], "completed")
        self.assertEqual([r["stage"] for r in seen], ["plan", "work", "review"])
        self.assertEqual([len(r["previous"]) for r in seen], [0, 1, 2])
        self.assertTrue(all(len(r["memories"]) == 1 for r in seen))

    def test_workspace_blocks_traversal_and_credentials(self):
        (self.root / "ok.txt").write_text("olá", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=secret", encoding="utf-8")
        tools = WorkspaceTools(self.root)
        self.assertEqual(tools.read("ok.txt"), "olá")
        for path in ("../escape", ".env"):
            with self.assertRaises(ValueError):
                tools.read(path)

    def test_command_requires_explicit_permission(self):
        with self.assertRaisesRegex(ValueError, "allow-commands"):
            CommandProvider({"enabled": True, "argv": ["ignored"]}, self.root)

    def test_command_protocol_uses_json(self):
        bridge = self.root / "bridge.py"
        bridge.write_text(
            "import json,sys\nrequest=json.load(sys.stdin)\n"
            "print(json.dumps({'text': request['prompt']}))\n",
            encoding="utf-8",
        )
        provider = CommandProvider(
            {"enabled": True, "argv": ["{python}", str(bridge)]},
            self.root,
            allowed=True,
        )
        self.assertEqual(provider.complete({"prompt": "hello"}), "hello")

    def test_config_paths_are_relative_to_config_file(self):
        path = self.root / "nous.config.json"
        path.write_text('{"version": 1, "providers": {"demo": {"kind": "demo"}}}', encoding="utf-8")
        config = load_config(str(path))
        self.assertEqual(config["workspace"], self.root)

    def test_dotenv_loads_missing_values_without_overwriting_environment(self):
        path = self.root / ".env"
        path.write_text("FIRST=value\nSECOND='two words'\n", encoding="utf-8")
        with patch.dict(os.environ, {"FIRST": "existing"}, clear=True):
            self.assertEqual(load_dotenv(path), 1)
            self.assertEqual(os.environ["FIRST"], "existing")
            self.assertEqual(os.environ["SECOND"], "two words")

    def test_grok_provider_uses_responses_api_only_when_network_is_allowed(self):
        self.config["providers"]["grok"] = {
            "kind": "grok", "enabled": True, "api_key_env": "TEST_GROK_KEY",
            "base_url": "https://example.test/v1", "model": "test-model",
        }
        with patch.dict(os.environ, {"TEST_GROK_KEY": "key"}, clear=False):
            with self.assertRaisesRegex(ValueError, "allow-network"):
                get_provider("grok", self.config)
            with patch("nous_dev.providers._post_json", return_value={
                "output": [{"content": [{"type": "output_text", "text": "ideia"}]}]
            }) as post:
                provider = get_provider("grok", self.config, network_allowed=True)
                self.assertEqual(provider.complete({
                    "prompt": "criar", "instructions": "responda", "memories": [],
                    "previous": [], "skills": [],
                }), "ideia")
                self.assertEqual(post.call_args.args[0], "https://example.test/v1/responses")

    def test_manus_provider_creates_private_async_task(self):
        self.config["providers"]["manus"] = {
            "kind": "manus", "enabled": True, "api_key_env": "TEST_MANUS_KEY",
            "endpoint": "https://example.test/task.create",
        }
        with patch.dict(os.environ, {"TEST_MANUS_KEY": "key"}, clear=False):
            with patch("nous_dev.providers._post_json", return_value={
                "ok": True, "task_id": "task-1", "task_url": "https://manus.example/task-1",
            }) as post:
                provider = get_provider("manus", self.config, network_allowed=True)
                text = provider.complete({
                    "stage": "work", "prompt": "pesquisar", "instructions": "responda",
                    "memories": [], "previous": [], "skills": [],
                })
                self.assertIn("task-1", text)
                self.assertEqual(post.call_args.args[0], "https://example.test/task.create")
                self.assertEqual(post.call_args.args[2]["share_visibility"], "private")

    def test_anthropic_provider_requires_network_and_parses_text(self):
        self.config["providers"]["claude-api"] = {
            "kind": "anthropic", "enabled": True, "api_key_env": "TEST_ANTHROPIC_KEY",
            "endpoint": "https://example.test/messages", "model": "test-model",
        }
        with patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "key"}, clear=False):
            with self.assertRaisesRegex(ValueError, "allow-network"):
                get_provider("claude-api", self.config)
            with patch("nous_dev.providers._post_json", return_value={
                "content": [{"type": "text", "text": "implementação"}]
            }) as post:
                provider = get_provider("claude-api", self.config, network_allowed=True)
                self.assertEqual(provider.complete({
                    "prompt": "implementar", "instructions": "responda", "memories": [],
                    "previous": [], "skills": [],
                }), "implementação")
                self.assertEqual(post.call_args.args[0], "https://example.test/messages")
                self.assertEqual(post.call_args.args[1]["anthropic-version"], "2023-06-01")

    def test_gemini_provider_requires_network_and_parses_text(self):
        self.config["providers"]["gemini"] = {
            "kind": "gemini", "enabled": True, "api_key_env": "TEST_GEMINI_KEY",
            "base_url": "https://example.test/models", "model": "test-model",
        }
        with patch.dict(os.environ, {"TEST_GEMINI_KEY": "key"}, clear=False):
            with self.assertRaisesRegex(ValueError, "allow-network"):
                get_provider("gemini", self.config)
            with patch("nous_dev.providers._post_json", return_value={
                "candidates": [{"content": {"parts": [{"text": "rota"}]}}]
            }) as post:
                provider = get_provider("gemini", self.config, network_allowed=True)
                self.assertEqual(provider.complete({
                    "prompt": "classificar", "instructions": "responda", "memories": [],
                    "previous": [], "skills": [],
                }), "rota")
                self.assertEqual(post.call_args.args[0],
                                 "https://example.test/models/test-model:generateContent")
                self.assertEqual(post.call_args.args[1]["x-goog-api-key"], "key")

    def test_cli_roundtrip(self):
        path = self.root / "nous.config.json"
        path.write_text('{"version": 1, "providers": {"demo": {"kind": "demo"}}}', encoding="utf-8")
        prefix = ["--config", str(path)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(prefix + ["memory", "add", "--project", "a", "preferência"]), 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(prefix + ["run", "--project", "a", "--prompt", "teste"]), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "completed")


if __name__ == "__main__":
    unittest.main()
