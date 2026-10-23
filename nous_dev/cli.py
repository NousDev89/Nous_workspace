import argparse
import json
import sys
from .config import load_config
from .skills import list_skills
from .store import Store
from .tools import WorkspaceTools


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser():
    p = argparse.ArgumentParser(description="Nous Dev — agentes e memória por projeto")
    p.add_argument("--config", default="nous.config.json")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("status")
    commands.add_parser("skills")
    memory = commands.add_parser("memory").add_subparsers(dest="action", required=True)
    add = memory.add_parser("add")
    add.add_argument("--project", required=True)
    add.add_argument("content")
    search = memory.add_parser("search")
    search.add_argument("--project", required=True)
    search.add_argument("--query", default="")
    run = commands.add_parser("run")
    run.add_argument("--project", required=True)
    run.add_argument("--prompt", required=True)
    run.add_argument("--planner", default="demo")
    run.add_argument("--worker", default="demo")
    run.add_argument("--reviewer", default="demo")
    run.add_argument("--skill", action="append", default=[])
    run.add_argument("--allow-commands", action="store_true")
    task = commands.add_parser("task")
    task.add_argument("id")
    tool = commands.add_parser("tool")
    tool.add_argument("action", choices=["list", "read"])
    tool.add_argument("path", nargs="?", default=".")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    store = None
    try:
        config = load_config(args.config)
        if args.command == "tool":
            tools = WorkspaceTools(config["workspace"])
            emit(getattr(tools, args.action)(args.path))
            return 0
        if args.command == "skills":
            emit(list_skills(config["skills_dir"]))
            return 0
        store = Store(config["data_dir"] / "nous.sqlite3")
        if args.command == "init":
            emit({"status": "initialized", "database": str(config["data_dir"] / "nous.sqlite3")})
        elif args.command == "status":
            emit({"version": "0.1.0", "database": str(config["data_dir"] / "nous.sqlite3"),
                  "providers": {
                      name: {
                          "kind": spec.get("kind"),
                          "status": ("demo" if spec.get("kind") == "demo" else
                                     "configured_not_tested" if spec.get("enabled") and spec.get("argv")
                                     else "not_configured")
                      } for name, spec in config.get("providers", {}).items()
                  }})
        elif args.command == "memory" and args.action == "add":
            emit({"id": store.add_memory(args.project, args.content)})
        elif args.command == "memory":
            emit(store.search(args.project, args.query))
        elif args.command == "task":
            emit(store.task(args.id))
        elif args.command == "run":
            from .orchestrator import run_task
            emit(run_task(store, config, args.project, args.prompt,
                          {"plan": args.planner, "work": args.worker, "review": args.reviewer},
                          args.skill, args.allow_commands))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1
    finally:
        if store:
            store.close()
