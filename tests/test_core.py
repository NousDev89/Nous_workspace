import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nous_dev.cli import main
from nous_dev.config import load_config
from nous_dev.orchestrator import run_task
from nous_dev.providers import CommandProvider
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

    def test_workflow_passes_memory_and_prior_outputs(self):
        self.store.add_memory("a", "contexto compartilhado")
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
        self.assertEqual(provider.complete({"prompt": "Olá"}), "Olá")

    def test_config_paths_are_relative_to_config_file(self):
        path = self.root / "nous.config.json"
        path.write_text('{"version": 1, "providers": {"demo": {"kind": "demo"}}}', encoding="utf-8")
        config = load_config(str(path))
        self.assertEqual(config["workspace"], self.root)

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
