"""SQLite metadata and immutable project-scoped local binary storage."""
import contextlib
import hashlib
import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path

from .contracts import artifact, now, ref, validate


def uid(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


class Store:
    def __init__(self, root):
        resolved = Path(root).resolve()
        # Windows' default MAX_PATH limit otherwise breaks deep project/asset keys.
        # Logical storage keys stay portable; only local I/O uses the extended path.
        if os.name == "nt" and not str(resolved).startswith("\\\\?\\"):
            if str(resolved).startswith("\\\\"):
                raise ValueError("활성 저장소는 PC의 로컬 폴더를 사용해주세요.")
            resolved = Path("\\\\?\\" + str(resolved))
        self.root = resolved
        self.root.mkdir(parents=True, exist_ok=True)
        self.staging = self.root / "staging"
        self.staging.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("지원하지 않는 데이터베이스 버전입니다. 원본을 보존했습니다.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS episodes (id TEXT NOT NULL, project_id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(project_id,id), FOREIGN KEY(project_id) REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS records (project_id TEXT NOT NULL, id TEXT NOT NULL, version TEXT NOT NULL, kind TEXT NOT NULL, content_id TEXT, data TEXT NOT NULL, PRIMARY KEY(project_id,id,version), FOREIGN KEY(project_id) REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS reviews (project_id TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(project_id,id), FOREIGN KEY(project_id) REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS audits (project_id TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(project_id,id), FOREIGN KEY(project_id) REFERENCES projects(id));
                CREATE INDEX IF NOT EXISTS records_scope ON records(project_id,content_id,kind);
                PRAGMA user_version=1;
            """)
        # Only unregistered temporary writes are cleaned; registered history is retained.
        for f in self.staging.iterdir():
            if f.is_file() and f.suffix == ".tmp":
                f.unlink()

    @contextlib.contextmanager
    def connection(self):
        db = sqlite3.connect(self.root / "studio.sqlite3", timeout=30)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @contextlib.contextmanager
    def transaction(self):
        with self.lock, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    @staticmethod
    def encode(data):
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def project(self, db, project_id):
        row = db.execute("SELECT data FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise LookupError("프로젝트를 찾을 수 없습니다.")
        return json.loads(row[0])

    def episode(self, db, project_id, content_id):
        self.project(db, project_id)
        row = db.execute("SELECT data FROM episodes WHERE project_id=? AND id=?", (project_id, content_id)).fetchone()
        if not row:
            raise LookupError("에피소드를 찾을 수 없습니다.")
        return json.loads(row[0])

    def write_project(self, db, project):
        db.execute("INSERT INTO projects(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (project["project_id"], self.encode(project)))

    def write_episode(self, db, episode):
        db.execute("INSERT INTO episodes(id,project_id,data) VALUES(?,?,?) ON CONFLICT(project_id,id) DO UPDATE SET data=excluded.data", (episode["content_id"], episode["project_id"], self.encode(episode)))

    def records(self, db, pid, cid=None):
        self.project(db, pid)
        rows = db.execute("SELECT data FROM records WHERE project_id=?" + (" AND content_id=?" if cid else "") + " ORDER BY rowid", (pid, cid) if cid else (pid,)).fetchall()
        result = [json.loads(r[0]) for r in rows]
        for record in result:
            validate(record)
            if record["project_id"] != pid or (cid and record.get("content_id") != cid):
                raise ValueError("저장된 산출물의 프로젝트 범위가 일치하지 않습니다.")
        return result

    def latest(self, db, pid, kind, cid=None):
        self.project(db, pid)
        row = db.execute("SELECT data FROM records WHERE project_id=? AND kind=?" + (" AND content_id=?" if cid else " AND content_id IS NULL") + " ORDER BY rowid DESC LIMIT 1", (pid, kind, cid) if cid else (pid, kind)).fetchone()
        if not row:
            return None
        record = json.loads(row[0])
        validate(record)
        if record["project_id"] != pid or (cid and record.get("content_id") != cid):
            raise ValueError("저장된 산출물 범위가 일치하지 않습니다.")
        return record

    def exact(self, db, pid, aid, version):
        row = db.execute("SELECT data FROM records WHERE project_id=? AND id=? AND version=?", (pid, aid, version)).fetchone()
        if not row:
            raise LookupError("해당 프로젝트의 정확한 산출물 버전을 찾을 수 없습니다.")
        record = json.loads(row[0])
        validate(record)
        if record["project_id"] != pid or record["artifact_id"] != aid or record["version"] != version:
            raise ValueError("정확한 산출물 참조가 일치하지 않습니다.")
        return record

    def next_version(self, db, pid, aid):
        row = db.execute("SELECT version FROM records WHERE project_id=? AND id=? ORDER BY rowid DESC LIMIT 1", (pid, aid)).fetchone()
        return f"1.0.{int(row[0].split('.')[2]) + 1}" if row else "1.0.0"

    def insert_record(self, db, record):
        validate(record)
        pid, cid = record["project_id"], record.get("content_id")
        self.project(db, pid)
        if cid:
            self.episode(db, pid, cid)
        for source in record.get("source_artifact_refs", []):
            if source["project_id"] != pid or (source.get("content_id") and source["content_id"] != cid):
                raise ValueError("프로젝트 또는 에피소드 입력 범위가 다릅니다.")
            resolved = self.exact(db, pid, source["artifact_id"], source["version"])
            if any(source.get(key, resolved[key]) != resolved[key] for key in ("schema_id", "schema_version")):
                raise ValueError("입력 산출물의 계약 버전이 일치하지 않습니다.")
        db.execute("INSERT INTO records VALUES(?,?,?,?,?,?)", (pid, record["artifact_id"], record["version"], record["artifact_type"], cid, self.encode(record)))

    def list_aux(self, db, table, pid):
        if table not in ("reviews", "audits"):
            raise ValueError("Unsupported registry")
        return [json.loads(r[0]) for r in db.execute(f"SELECT data FROM {table} WHERE project_id=? ORDER BY rowid", (pid,)).fetchall()]

    def insert_aux(self, db, record):
        validate(record)
        table, key = ("reviews", "review_decision_id") if record["record_type"] == "review_decision" else ("audits", "event_id")
        db.execute(f"INSERT INTO {table} VALUES(?,?,?)", (record["project_id"], record[key], self.encode(record)))

    def audit(self, db, pid, action, aid, *, version=None, cid=None, result="completed", before=None, after=None):
        event = dict(record_type="audit_event", event_id=uid("event"), project_id=pid, actor="local-user", action=action,
                     occurred_at=now(), scope={"record_type": "artifact", "record_id": aid}, result=result, synthetic=True)
        if version:
            event["scope"]["version"] = version
        if cid:
            event["content_id"] = cid
        if before:
            event["before_ref"] = ref(before)
        if after:
            event["after_ref"] = ref(after)
        self.insert_aux(db, event)
        return event

    def approval(self, db, record):
        reviews = self.list_aux(db, "reviews", record["project_id"])
        decisions = [d for d in reviews if not d.get("restored_history") and d["artifact_ref"]["artifact_id"] == record["artifact_id"] and d["artifact_ref"]["version"] == record["version"]]
        return decisions[-1] if decisions else None

    def effective(self, db, record):
        result = json.loads(self.encode(record))
        decision = self.approval(db, record)
        if decision:
            result["approval"] = dict(status=decision["decision"], gate=decision["gate"], review_decision_id=decision["review_decision_id"], approver=decision["actor"], approved_version=record["version"], decision_at=decision["decided_at"], notes=decision.get("notes", ""))
        return result

    def safe_path(self, key):
        if "\\" in key or not key or ":" in key:
            raise ValueError("자산 경로가 올바르지 않습니다.")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise ValueError("자산 저장소 범위를 벗어났습니다.")
        return path

    def asset(self, db, pid, asset_id):
        items = [r for r in self.records(db, pid) if r["artifact_type"] == "asset_record" and r["asset_id"] == asset_id]
        if not items:
            raise LookupError("해당 프로젝트의 자산을 찾을 수 없습니다.")
        return items[-1]

    def asset_bytes(self, record):
        validate(record)
        path = self.safe_path(record["storage_key"])
        if not path.is_file():
            raise ValueError("자산 파일이 누락되었습니다.")
        data = path.read_bytes()
        if len(data) != record["byte_size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("자산 체크섬이 일치하지 않습니다.")
        return data

    def write_binary(self, key, data):
        target = self.safe_path(key)
        digest = hashlib.sha256(data).hexdigest()
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError("이미 저장된 자산 버전을 덮어쓸 수 없습니다.")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.staging / (uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                raise ValueError("파일 저장 무결성 확인 실패")
            # A single database writer owns registration; no mutable asset replacement.
            with target.open("xb") as f:
                f.write(temporary.read_bytes())
                f.flush()
                os.fsync(f.fileno())
        finally:
            temporary.unlink(missing_ok=True)

    def add_asset(self, db, owner, data, *, media_type="image/png", role="candidate", origin=None):
        aid = uid("asset")
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "application/pdf": "pdf"}[media_type]
        digest = hashlib.sha256(data).hexdigest()
        key = f"projects/{owner['project_id']}/assets/{aid}/1.0.0/{digest}.{ext}"
        self.write_binary(key, data)
        record = artifact("asset_record", owner["project_id"], uid("asset-record"), content_id=owner.get("content_id"))
        record.update(asset_id=aid, media_type=media_type, byte_size=len(data), storage_key=key, sha256=digest,
                      owner_artifact_ref=ref(owner), role=role)
        if origin:
            record["provenance"]["source"] = origin
        self.insert_record(db, record)
        return record

    def export_snapshot(self, db, pid):
        return {"project": self.project(db, pid), "records": self.records(db, pid),
                "episodes": [json.loads(r[0]) for r in db.execute("SELECT data FROM episodes WHERE project_id=? ORDER BY rowid", (pid,)).fetchall()],
                "review_decisions": self.list_aux(db, "reviews", pid), "audit_events": self.list_aux(db, "audits", pid)}
