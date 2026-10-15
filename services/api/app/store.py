import json
import os
import sqlite3
from pathlib import Path

from .ontology import initial_ontology


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("DATABASE_PATH", "data/poc.sqlite3")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO settings VALUES ('ontology', ?)",
                       (initial_ontology().model_dump_json(),))
            # A dev reload cannot resume in-process model calls.
            rows = db.execute("SELECT id, body FROM runs").fetchall()
            for id_, body in rows:
                run = json.loads(body)
                if run["status"] in ("outline_pending", "slides_pending"):
                    run.update(status="failed", error="서버 재시작으로 생성이 중단되었습니다.")
                    db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run, ensure_ascii=False), id_))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def get(self, id_: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (id_,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, run: dict):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?)",
                       (run["id"], json.dumps(run, ensure_ascii=False)))

    def claim(self, id_: str, outline: dict, ontology: dict) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM runs WHERE id=?", (id_,)).fetchone()
            if row is None:
                raise KeyError(id_)
            run = json.loads(row[0])
            if run["status"] != "outline_ready":
                raise ValueError("확정 가능한 개요 상태가 아닙니다.")
            run.update(status="slides_pending", stage="슬라이드 생성 시작", confirmed_outline=outline,
                       ontology=ontology, error=None)
            db.execute("UPDATE runs SET body=? WHERE id=?", (json.dumps(run, ensure_ascii=False), id_))
        return run

    def list(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY rowid DESC LIMIT 50").fetchall()
        return [{k: run[k] for k in ("id", "status", "stage", "text")} for run in (json.loads(r[0]) for r in rows)]

    def ontology(self) -> dict:
        with self.connect() as db:
            return json.loads(db.execute("SELECT body FROM settings WHERE id='ontology'").fetchone()[0])

    def save_ontology(self, value: dict):
        with self.connect() as db:
            db.execute("UPDATE settings SET body=? WHERE id='ontology'", (json.dumps(value, ensure_ascii=False),))
