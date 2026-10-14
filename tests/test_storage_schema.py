import json
import os
import tempfile
import unittest
from pathlib import Path

from backend.contracts import artifact, ref
from backend.service import Studio
from backend.storage import Store


class StoredSchemaTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent.parent / ".test-data"
        root.mkdir(exist_ok=True)
        if os.name == "nt":
            root = Path("\\\\?\\" + str(root))
        self.temporary = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(self.temporary.name)
        self.studio = Studio(self.store)
        self.project = self.studio.create_project(dict(name="synthetic", topic="synthetic", protagonist="synthetic", audience=[], tone=[], series_direction="synthetic", supported_formats=["single_panel"], exclusions=[], synthetic=True))

    def test_future_stored_contract_rejected_on_read_and_exact_resolution(self):
        pid = self.project["project_id"]
        with self.store.transaction() as db:
            record = self.store.latest(db, pid, "project_brief")
            record["schema_version"] = "99.0.0"
            db.execute("UPDATE records SET data=? WHERE project_id=? AND id=? AND version=?", (json.dumps(record), pid, record["artifact_id"], record["version"]))
        with self.assertRaises(ValueError):
            self.studio.snapshot(pid)
        with self.store.connection() as db, self.assertRaises(ValueError):
            self.store.exact(db, pid, record["artifact_id"], record["version"])

    def test_exact_source_declared_schema_cannot_disagree_with_registry(self):
        pid = self.project["project_id"]
        with self.assertRaises(ValueError), self.store.transaction() as db:
            original = self.store.latest(db, pid, "project_brief")
            source = ref(original)
            source["schema_version"] = "99.0.0"
            record = artifact("reference_research", pid, "synthetic-invalid-ref", sources=[source])
            self.store.insert_record(db, record)
        with self.store.connection() as db:
            self.assertEqual(len(self.store.records(db, pid)), 4)
