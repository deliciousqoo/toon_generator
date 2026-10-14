"""Package integrity and encryption checks; uses only synthetic in-memory data."""

import copy
import hashlib
import io
import json
import stat
import unittest
import warnings
import zipfile
from unittest.mock import patch

from backend.backup import (
    BackupError, SCHEMA_ID, SCHEMA_VERSION, evaluate_passphrase,
    generate_passphrase, pack_project, unpack_project,
)


def sample_project():
    content = b"synthetic image bytes"
    owner = {"project_id": "fixture-project", "artifact_id": "fixture-run", "version": "1.0.0"}
    run = {**owner, "artifact_type": "image_generation_run_manifest", "schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION}
    asset = {
        "project_id": "fixture-project", "artifact_id": "fixture-asset-record", "version": "1.0.0",
        "artifact_type": "asset_record", "schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION,
        "asset_id": "fixture-asset", "media_type": "image/png", "byte_size": len(content),
        "storage_key": "fixture-project/fixture-asset.png", "sha256": hashlib.sha256(content).hexdigest(),
        "owner_artifact_ref": owner,
    }
    snapshot = {
        "project": {"project_id": "fixture-project", "title": "Synthetic only"},
        "records": [run, asset],
        "episodes": [{"project_id": "fixture-project", "content_id": "fixture-episode"}],
        "review_decisions": [{"project_id": "fixture-project", "record_type": "review_decision", "decision": "approved", "actor": "synthetic-human", "artifact_ref": owner}],
        "audit_events": [{"project_id": "fixture-project", "record_type": "audit_event", "action": "review", "actor": "synthetic-human"}],
    }
    return snapshot, {asset["storage_key"]: content}


def rewrite_zip(data, *, modify_manifest=None, modify_snapshot=None, additions=None, omit=None, replacements=None):
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        entries = {info.filename: source.read(info) for info in source.infolist()}
    if modify_manifest:
        manifest = json.loads(entries["manifest.json"])
        modify_manifest(manifest)
        entries["manifest.json"] = json.dumps(manifest).encode()
    if modify_snapshot:
        snapshot = json.loads(entries["records/project.json"])
        modify_snapshot(snapshot)
        entries["records/project.json"] = json.dumps(snapshot).encode()
        manifest = json.loads(entries["manifest.json"])
        for entry in manifest["files"]:
            if entry["path"] == "records/project.json":
                entry["byte_size"] = len(entries[entry["path"]])
                entry["sha256"] = hashlib.sha256(entries[entry["path"]]).hexdigest()
        entries["manifest.json"] = json.dumps(manifest).encode()
    entries.update(replacements or {})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as result:
        for name, content in entries.items():
            if name != omit:
                result.writestr(name, content)
        for name, content in (additions or []):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                result.writestr(name, content)
    return buffer.getvalue()


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.assets = sample_project()
        self.filename, self.plain = pack_project(self.snapshot, self.assets)

    def test_plain_roundtrip_preserves_every_record_and_asset(self):
        restored, assets, manifest = unpack_project(self.plain)
        self.assertEqual(restored, self.snapshot)
        self.assertEqual(assets, self.assets)
        self.assertTrue(self.filename.endswith(".toonbackup"))
        self.assertEqual(manifest["source_project_id"], "fixture-project")
        self.assertEqual(manifest["package_format_version"], "1.0.0")
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(set(self.snapshot), set(restored))

    def test_encrypted_roundtrip_wrong_password_and_tamper(self):
        secret = generate_passphrase()
        name, ciphertext = pack_project(self.snapshot, self.assets, encrypted=True, passphrase=secret)
        self.assertTrue(name.endswith(".toonbackup.age"))
        self.assertTrue(ciphertext.startswith(b"age-encryption.org/v1\n"))
        self.assertNotIn(secret.encode(), ciphertext)
        self.assertEqual(unpack_project(ciphertext, passphrase=secret)[:2], (self.snapshot, self.assets))
        with self.assertRaises(BackupError):
            unpack_project(ciphertext, passphrase="wrong passphrase")
        with self.assertRaises(BackupError):
            unpack_project(ciphertext[:-1] + bytes([ciphertext[-1] ^ 1]), passphrase=secret)
        with self.assertRaises(BackupError):
            unpack_project(ciphertext)

    def test_generated_phrase_and_strength_never_return_secret(self):
        secret = generate_passphrase()
        self.assertEqual(len(secret.split("-")), 12)
        evaluation = evaluate_passphrase(secret)
        self.assertEqual(evaluation["score"], 4)
        self.assertNotIn(secret, str(evaluation))
        self.assertEqual(evaluate_passphrase("password123")["score"], 0)
        with self.assertRaises(BackupError):
            pack_project(self.snapshot, self.assets, encrypted=True, passphrase="")

    def test_changed_content_rejected(self):
        key = next(iter(self.assets))
        data = rewrite_zip(self.plain, additions=[("assets/" + key, b"bad")])
        with self.assertRaises(BackupError):
            unpack_project(data)
        with zipfile.ZipFile(io.BytesIO(self.plain)) as archive:
            contents = {entry.filename: archive.read(entry) for entry in archive.infolist()}
        contents["assets/" + key] = b"X" * len(self.assets[key])
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
        with self.assertRaisesRegex(BackupError, "체크섬"):
            unpack_project(buffer.getvalue())

    def test_unknown_version_missing_file_and_extra_file_rejected(self):
        cases = [
            rewrite_zip(self.plain, modify_manifest=lambda manifest: manifest.update(package_format_version="99.0.0")),
            rewrite_zip(self.plain, omit="records/project.json"),
            rewrite_zip(self.plain, additions=[("assets/unregistered.png", b"bad")]),
            rewrite_zip(self.plain, modify_manifest=lambda manifest: manifest["schemas"][0].update(schema_version="99.0.0")),
        ]
        for case in cases:
            with self.subTest(case=len(case)), self.assertRaises(BackupError):
                unpack_project(case)

    def test_traversal_windows_paths_and_symlinks_rejected(self):
        for path in ("../escape", "/absolute", "assets/../escape", "C:/escape", "assets\\escape", "assets/CON", "assets/trailing."):
            with self.subTest(path=path), self.assertRaises(BackupError):
                unpack_project(rewrite_zip(self.plain, additions=[(path, b"bad")]))
        link = zipfile.ZipInfo("assets/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(BackupError):
            unpack_project(rewrite_zip(self.plain, additions=[(link, b"../secret")]))

    def test_duplicate_and_case_alias_rejected(self):
        for path in ("manifest.json", "MANIFEST.JSON"):
            with self.subTest(path=path), self.assertRaises(BackupError):
                unpack_project(rewrite_zip(self.plain, additions=[(path, b"{}")]))

    def test_secret_fields_rejected_for_export_and_restore(self):
        for field in ("api_key", "accessToken", "credentials", "password", "passphrase"):
            dirty = copy.deepcopy(self.snapshot)
            dirty["project"][field] = "never print this"
            with self.subTest(field=field), self.assertRaises(BackupError) as error:
                pack_project(dirty, self.assets)
            self.assertNotIn("never print this", str(error.exception))
            with self.subTest(restore_field=field), self.assertRaises(BackupError):
                unpack_project(rewrite_zip(self.plain, modify_snapshot=lambda snapshot: snapshot["project"].update({field: "never print this"})))

    def test_cross_project_scope_and_asset_metadata_rejected(self):
        dirty = copy.deepcopy(self.snapshot)
        dirty["records"][0]["project_id"] = "different-project"
        with self.assertRaises(BackupError):
            pack_project(dirty, self.assets)
        dirty = copy.deepcopy(self.snapshot)
        dirty["records"][1]["owner_artifact_ref"]["version"] = "7.0.0"
        with self.assertRaises(BackupError):
            pack_project(dirty, self.assets)
        with self.assertRaises(BackupError):
            pack_project(self.snapshot, {})
        with self.assertRaises(BackupError):
            unpack_project(rewrite_zip(self.plain, modify_manifest=lambda manifest: manifest["files"][0].update(media_type="text/plain")))

    def test_size_bounds_and_nonfinite_json_rejected(self):
        with patch("backend.backup.MAX_PACKAGE_BYTES", 32), self.assertRaises(BackupError):
            unpack_project(self.plain)
        with patch("backend.backup.MAX_ENTRY_BYTES", 8), self.assertRaises(BackupError):
            unpack_project(self.plain)
        dirty = copy.deepcopy(self.snapshot)
        dirty["project"]["number"] = float("nan")
        with self.assertRaises(BackupError):
            pack_project(dirty, self.assets)

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(BackupError):
            unpack_project(rewrite_zip(self.plain, replacements={"manifest.json": b'{"backup_id":"a","backup_id":"b"}'}))


if __name__ == "__main__":
    unittest.main()
