import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, prompt TEXT NOT NULL,
                status TEXT NOT NULL, result TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, content TEXT NOT NULL,
                source TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS memories_project ON memories(project);
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                stage TEXT NOT NULL, provider TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL
            );
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def add_memory(self, project, content, source="user"):
        if not project.strip() or not content.strip():
            raise ValueError("Projeto e memória não podem ser vazios.")
        memory_id = uuid.uuid4().hex
        self.db.execute("INSERT INTO memories VALUES (?, ?, ?, ?, ?)",
                        (memory_id, project, content, source, now()))
        self.db.commit()
        return memory_id

    def search(self, project, query="", limit=10):
        # instr trata %, _ e aspas como texto, e não como padrão SQL.
        rows = self.db.execute(
            """SELECT * FROM memories WHERE project = ?
               AND instr(lower(content), lower(?)) > 0
               ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (project, query, max(1, min(limit, 100)))).fetchall()
        return [dict(row) for row in rows]

    def create_task(self, project, prompt):
        task_id = uuid.uuid4().hex
        self.db.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)",
                        (task_id, project, prompt, "running", None, now()))
        self.db.commit()
        return task_id

    def finish_task(self, task_id, status, result):
        self.db.execute("UPDATE tasks SET status = ?, result = ? WHERE id = ?",
                        (status, json.dumps(result, ensure_ascii=False), task_id))
        self.db.commit()

    def event(self, task_id, stage, provider, status):
        self.db.execute(
            "INSERT INTO events(task_id, stage, provider, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, stage, provider, status, now()))
        self.db.commit()

    def task(self, task_id):
        row = self.db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Tarefa não encontrada.")
        result = dict(row)
        result["result"] = json.loads(result["result"]) if result["result"] else None
        result["events"] = [dict(r) for r in self.db.execute(
            "SELECT stage, provider, status, created_at FROM events WHERE task_id = ? ORDER BY seq",
            (task_id,))]
        return result
