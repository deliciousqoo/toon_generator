"""Local browser/API/storage acceptance using synthetic fixtures only."""

import copy
import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app
from backend.backup import unpack_project
from backend.contracts import SCHEMA_VERSION, validate, validate_fixtures

BASE_URL = "http://127.0.0.1:8765"


class PlatformTests(unittest.TestCase):
    def setUp(self):
        # Explicitly keep disposable data inside the workspace; Windows sandbox
        # temporary directories can deny creation of application subdirectories.
        test_root = Path(__file__).resolve().parent.parent / ".test-data"
        test_root.mkdir(exist_ok=True)
        if os.name == "nt" and not str(test_root).startswith("\\\\?\\"):
            test_root = Path("\\\\?\\" + str(test_root))
        self.temporary = tempfile.TemporaryDirectory(prefix="toon-studio-test-", dir=test_root)
        self.addCleanup(self.temporary.cleanup)
        self.data_root = Path(self.temporary.name) / "app-data"
        self.app = create_app(self.data_root)
        self.client = self.new_client(self.app)
        self.csrf = self.client.get("/api/bootstrap").json()["csrf_token"]

    def new_client(self, app):
        client = TestClient(app, base_url=BASE_URL, client=("127.0.0.1", 50000))
        client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        return client

    def request(self, method, path, expected=200, **kwargs):
        kwargs.setdefault("headers", {})
        kwargs["headers"].setdefault("x-csrf-token", self.csrf)
        response = self.client.request(method, path, **kwargs)
        self.assertEqual(response.status_code, expected, (method, path, response.text[:2000]))
        return response

    def project(self, **overrides):
        data = {
            "name": "합성 프로젝트", "topic": "가상의 작은 관찰", "protagonist": "가상의 둥근 주인공",
            "audience": ["synthetic"], "tone": ["차분함"], "series_direction": "합성 단편 시리즈",
            "supported_formats": ["single_panel", "multi_panel"], "exclusions": ["실제 캐릭터 복제"], "synthetic": True,
        }
        data.update(overrides)
        return self.request("POST", "/api/projects", 201, json=data).json()

    def snapshot(self, pid):
        return self.request("GET", f"/api/projects/{pid}").json()

    def review(self, pid, record, gate, *, decision="approved", expected=200, notes=""):
        return self.request("POST", f"/api/projects/{pid}/reviews", expected, json={
            "artifact_id": record["artifact_id"], "version": record["version"],
            "gate": gate, "decision": decision, "notes": notes,
        })

    def approve_setup(self, pid):
        setup = self.snapshot(pid)["setup"]
        for kind, gate in (("reference_research", "RG"), ("character_package", "CG"), ("account_strategy", "SG")):
            self.review(pid, setup[kind], gate)

    def episode(self, pid, **overrides):
        data = {
            "title": "합성 에피소드", "input_mode": "developed_story",
            "supplied_material": "합성 첫 장면\n합성 다음 장면\n합성 마지막 장면",
            "requested_edit_scope": [], "requested_format": "multi_panel", "reference_format": None,
            "cut_count": 2, "format_confirmed": False, "synthetic": True,
        }
        data.update(overrides)
        return self.request("POST", f"/api/projects/{pid}/episodes", 201, json=data).json()

    def episode_snapshot(self, pid, cid):
        return self.request("GET", f"/api/projects/{pid}/episodes/{cid}").json()

    def board(self, pid, cid, *, expected=200, **data):
        return self.request("POST", f"/api/projects/{pid}/episodes/{cid}/storyboard", expected, json=data)

    def generate(self, pid, cid, board, *, run=None, units=None, expected=200):
        return self.request("POST", f"/api/projects/{pid}/episodes/{cid}/generate", expected, json={
            "expected_storyboard_version": board["version"],
            "expected_run_version": run["version"] if run else None, "unit_ids": units,
        })

    def working_board(self, *, cuts=2, **episode_options):
        project = self.project()
        pid = project["project_id"]
        self.approve_setup(pid)
        episode = self.episode(pid, cut_count=cuts, requested_format="single_panel" if cuts == 1 else "multi_panel", **episode_options)
        cid = episode["episode"]["content_id"]
        board = self.board(pid, cid).json()["storyboard"]
        return pid, cid, board

    def working_run(self, *, cuts=2):
        pid, cid, board = self.working_board(cuts=cuts)
        self.review(pid, board, "G2")
        run = self.generate(pid, cid, board).json()["run"]
        return pid, cid, board, run

    def select(self, pid, cid, run, unit_id, output_id, expected=200):
        return self.request("POST", f"/api/projects/{pid}/episodes/{cid}/selection", expected, json={
            "expected_run_version": run["version"], "unit_id": unit_id, "output_id": output_id,
        })

    def select_all(self, pid, cid, run):
        for group in list(run["review_package"]["per_unit_candidate_sets"]):
            run = self.select(pid, cid, run, group["unit_id"], group["candidate_output_ids"][0]).json()["run"]
        return run

    def png_bytes(self):
        data = io.BytesIO()
        Image.new("RGB", (12, 12), "teal").save(data, format="PNG")
        return data.getvalue()

    def reference(self, pid, data=None, expected=200, **overrides):
        form = {"source": "synthetic fixture", "use_basis": "synthetic-owned", "not_to_copy": "기존 캐릭터, 기존 대사", "synthetic": "true", "retention_allowed": "true"}
        form.update(overrides)
        return self.request("POST", f"/api/projects/{pid}/references", expected, data=form,
                            files={"file": ("synthetic-reference.png", data or self.png_bytes(), "image/png")})

    def backup(self, pid, *, encrypted=False, passphrase=None):
        return self.request("POST", f"/api/projects/{pid}/backup", json={"encrypted": encrypted, "passphrase": passphrase})

    def restore(self, content, *, passphrase=None, expected=201):
        return self.request("POST", "/api/restore", expected, data={"passphrase": passphrase} if passphrase else {},
                            files={"file": ("synthetic.toonbackup", content, "application/octet-stream")})

    def test_contract_fixtures_and_created_records_validate_offline(self):
        self.assertEqual(validate_fixtures(), 10)
        project = self.project()
        snapshot = self.snapshot(project["project_id"])
        self.assertEqual(len(snapshot["records"]), 4)
        for record in snapshot["records"] + snapshot["audit_events"]:
            validate(record)
        bad = copy.deepcopy(snapshot["records"][0])
        bad["schema_version"] = "99.0.0"
        with self.assertRaises(ValueError):
            validate(bad)

    def test_project_data_persists_restart_and_temp_cleanup_keeps_assets(self):
        pid, cid, board = self.working_board(cuts=1)
        before = self.snapshot(pid)
        asset = next(r for r in before["assets"] if r["role"] == "storyboard_rough")
        self.request("GET", asset["url"])
        unregistered = self.data_root / "staging" / "abandoned.tmp"
        unregistered.write_bytes(b"transient")
        restarted = self.new_client(create_app(self.data_root))
        after = restarted.get(f"/api/projects/{pid}").json()
        self.assertEqual(before, after)
        self.assertEqual(restarted.get(asset["url"]).status_code, 200)
        self.assertFalse(unregistered.exists())
        self.assertNotEqual(self.csrf, restarted.get("/api/bootstrap").json()["csrf_token"])

    def test_setup_human_gates_and_dependency_order_are_required(self):
        project = self.project()
        pid = project["project_id"]
        episode = self.episode(pid)
        cid = episode["episode"]["content_id"]
        setup = self.snapshot(pid)["setup"]
        self.board(pid, cid, expected=409)
        self.review(pid, setup["character_package"], "CG", expected=409)
        self.review(pid, setup["account_strategy"], "SG", expected=409)
        self.review(pid, setup["reference_research"], "RG")
        self.board(pid, cid, expected=409)
        self.review(pid, setup["character_package"], "CG")
        self.board(pid, cid, expected=409)
        self.review(pid, setup["account_strategy"], "SG")
        board = self.board(pid, cid).json()["storyboard"]
        self.assertEqual(board["approval"]["status"], "pending")
        self.assertEqual(self.episode_snapshot(pid, cid)["run"], None)
        self.assertTrue(all(r["actor"] == "local-user" for r in self.snapshot(pid)["review_decisions"]))

    def test_developed_story_initial_dialogue_is_exact_source(self):
        raw = "  첫 장면 그대로  \r\n\n두 번째 장면!\n마지막 장면\n"
        pid, cid, board = self.working_board(supplied_material=raw)
        self.assertEqual(board["story"]["selected_story"], raw)
        self.assertEqual(board["story"]["supplied_material"], raw)
        self.assertEqual("".join(u["dialogue"] for u in board["storyboard"]["units"]), raw)
        self.assertEqual(board["story"]["preservation_scope"], [])
        self.assertEqual(self.episode_snapshot(pid, cid)["brief"]["input"]["supplied_material"], raw)

    def test_short_topic_proposals_require_selection_and_keep_input(self):
        pid = self.project()["project_id"]
        self.approve_setup(pid)
        raw = "합성 소재: 작은 구름 관찰"
        result = self.episode(pid, input_mode="short_topic", supplied_material=raw)
        cid = result["episode"]["content_id"]
        self.assertEqual(len(result["proposals"]), 3)
        self.board(pid, cid, expected=400)
        proposal = result["proposals"][1]
        board = self.board(pid, cid, proposal_id=proposal["id"]).json()["storyboard"]
        self.assertEqual(board["story"]["selected_story"], proposal["story"])
        self.assertEqual(board["story"]["supplied_material"], raw)
        self.assertEqual("".join(u["dialogue"] for u in board["storyboard"]["units"]), proposal["story"])

    def test_single_panel_and_multicut_formats_and_conflicts(self):
        pid = self.project()["project_id"]
        self.approve_setup(pid)
        single = self.episode(pid, cut_count=1, requested_format="single_panel")
        cid = single["episode"]["content_id"]
        board = self.board(pid, cid).json()["storyboard"]
        self.assertEqual(len(board["storyboard"]["units"]), 1)
        self.assertEqual(board["content_scope"]["format_decision"]["selected_format"], "single_panel")
        conflict = self.episode(pid, requested_format="multi_panel", reference_format="single_panel")
        cid = conflict["episode"]["content_id"]
        self.assertTrue(conflict["brief"]["unresolved_questions"])
        self.board(pid, cid, expected=409)
        confirmed = self.board(pid, cid, format_confirmed=True).json()["storyboard"]
        self.assertTrue(confirmed["content_scope"]["format_decision"]["reference_conflict_confirmed"])
        ambiguous = self.episode(pid, requested_format=None)
        cid = ambiguous["episode"]["content_id"]
        self.board(pid, cid, expected=409)
        self.board(pid, cid, format_confirmed=True)
        invalid = {**single["episode"], "requested_format": "single_panel", "cut_count": 2}
        for key in ("project_id", "content_id", "created_at", "status", "proposals", "selected_format"):
            invalid.pop(key, None)
        self.request("POST", f"/api/projects/{pid}/episodes", 400, json=invalid)

    def test_g2_rejection_rework_and_edit_reopen_approval(self):
        for decision in ("rejected", "rework"):
            with self.subTest(decision=decision):
                pid, cid, board = self.working_board(cuts=1)
                self.review(pid, board, "G2", decision=decision, expected=400)
                self.review(pid, board, "G2", decision=decision, notes="합성 대사 설명 수정")
                self.generate(pid, cid, board, expected=409)
                units = [{k: u[k] for k in ("unit_id", "order", "action", "dialogue", "composition", "continuity")} for u in board["storyboard"]["units"]]
                units[0]["dialogue"] = "사람이 수정한 합성 대사"
                edited = self.board(pid, cid, expected_version=board["version"], units=units).json()["storyboard"]
                self.assertNotEqual(edited["version"], board["version"])
                self.assertEqual(edited["approval"]["status"], "pending")
                self.assertEqual(edited["storyboard"]["units"][0]["dialogue"], units[0]["dialogue"])
                self.review(pid, board, "G2", expected=409)
                self.review(pid, edited, "G2")
                self.generate(pid, cid, edited)
                history = self.episode_snapshot(pid, cid)["history"]
                original = next(r for r in history if r["artifact_id"] == board["artifact_id"] and r["version"] == board["version"])
                self.assertEqual(original["storyboard"]["units"][0]["dialogue"], board["storyboard"]["units"][0]["dialogue"])

    def test_generation_and_g3_are_explicit_human_decisions(self):
        pid, cid, board = self.working_board()
        self.generate(pid, cid, board, expected=409)
        self.review(pid, board, "G2")
        result = self.generate(pid, cid, board).json()
        run = result["run"]
        self.assertEqual(run["adapter"]["kind"], "mock")
        self.assertTrue(run["adapter"]["synthetic"])
        self.assertEqual(run["approval"]["status"], "pending")
        self.assertEqual(result["episode"]["status"], "draft_review")
        self.assertEqual(len(run["review_package"]["per_unit_candidate_sets"]), 2)
        self.assertTrue(all(len(g["candidate_output_ids"]) == 2 for g in run["review_package"]["per_unit_candidate_sets"]))
        self.review(pid, run, "G3", expected=409)
        run = self.select_all(pid, cid, run)
        self.assertEqual(len(run["review_package"]["selected_output_ids"]), 2)
        self.assertEqual(self.episode_snapshot(pid, cid)["episode"]["status"], "draft_review")
        self.review(pid, run, "G3")
        self.assertEqual(self.episode_snapshot(pid, cid)["episode"]["status"], "ai_draft")
        snapshot = self.snapshot(pid)
        for record in snapshot["records"] + snapshot["review_decisions"] + snapshot["audit_events"]:
            validate(record)
        self.assertTrue(all(r["provenance"]["synthetic"] for r in snapshot["records"]))
        for asset in self.episode_snapshot(pid, cid)["assets"]:
            png = self.request("GET", asset["url"])
            with Image.open(io.BytesIO(png.content)) as image:
                self.assertEqual(image.info["synthetic"], "true")

    def test_selected_cut_regeneration_keeps_history_and_other_selection(self):
        pid, cid, board, run = self.working_run()
        selected = self.select_all(pid, cid, run)
        groups = selected["review_package"]["per_unit_candidate_sets"]
        changed_unit, kept_unit = groups[0]["unit_id"], groups[1]["unit_id"]
        before_groups = {g["unit_id"]: copy.deepcopy(g) for g in groups}
        before_assets = {a["asset_id"]: self.request("GET", a["url"]).content for a in self.episode_snapshot(pid, cid)["assets"]}
        regenerated = self.generate(pid, cid, board, run=selected, units=[changed_unit]).json()["run"]
        after_groups = {g["unit_id"]: g for g in regenerated["review_package"]["per_unit_candidate_sets"]}
        self.assertEqual(after_groups[kept_unit], before_groups[kept_unit])
        self.assertEqual(after_groups[changed_unit]["candidate_output_ids"][:2], before_groups[changed_unit]["candidate_output_ids"])
        self.assertEqual(len(after_groups[changed_unit]["candidate_output_ids"]), 4)
        self.assertIsNone(after_groups[changed_unit]["selected_output_id"])
        history = self.episode_snapshot(pid, cid)
        self.assertEqual(next(r for r in history["history"] if r["artifact_id"] == selected["artifact_id"] and r["version"] == selected["version"])["review_package"], selected["review_package"])
        current_assets = {a["asset_id"]: a for a in history["assets"]}
        for asset_id, content in before_assets.items():
            self.assertEqual(self.request("GET", current_assets[asset_id]["url"]).content, content)
        self.assertTrue(any(a["action"] == "regenerate" for a in self.snapshot(pid)["audit_events"]))

    def test_stale_run_storyboard_and_setup_writes_fail_without_new_versions(self):
        pid, cid, board, run = self.working_run()
        group = run["review_package"]["per_unit_candidate_sets"][0]
        selected = self.select(pid, cid, run, group["unit_id"], group["candidate_output_ids"][0]).json()["run"]
        self.select(pid, cid, run, group["unit_id"], group["candidate_output_ids"][1], expected=409)
        self.generate(pid, cid, board, run=run, expected=409)
        edited = self.board(pid, cid, expected_version=board["version"]).json()["storyboard"]
        count = len(self.snapshot(pid)["records"])
        self.board(pid, cid, expected=409, expected_version=board["version"])
        self.generate(pid, cid, board, run=selected, expected=409)
        self.review(pid, selected, "G3", expected=409)
        self.assertTrue(self.episode_snapshot(pid, cid)["run_stale"])
        self.assertEqual(count, len(self.snapshot(pid)["records"]))
        project = self.snapshot(pid)["project"]
        setup_data = {k: project[k] for k in ("name", "topic", "protagonist", "audience", "tone", "series_direction", "supported_formats", "exclusions", "synthetic")}
        setup_data["expected_version"] = project["setup_version"]
        self.request("PUT", f"/api/projects/{pid}/setup", json=setup_data)
        self.request("PUT", f"/api/projects/{pid}/setup", 409, json=setup_data)
        self.review(pid, edited, "G2", expected=409)
        self.assertTrue(all(r["approval"]["status"] == "pending" for r in self.snapshot(pid)["setup"].values()))

    def test_cross_project_episode_asset_and_output_selection_are_isolated(self):
        pid, cid, board, run = self.working_run()
        other = self.project(name="합성 다른 프로젝트")["project_id"]
        self.approve_setup(other)
        second = self.episode(other)["episode"]["content_id"]
        other_board = self.board(other, second).json()["storyboard"]
        self.review(other, other_board, "G2")
        other_run = self.generate(other, second, other_board).json()["run"]
        asset_id = self.episode_snapshot(pid, cid)["assets"][0]["asset_id"]
        self.request("GET", f"/api/projects/{other}/assets/{asset_id}", 404)
        self.request("GET", f"/api/projects/{other}/episodes/{cid}", 404)
        self.board(other, cid, expected=404)
        self.review(other, board, "G2", expected=404)
        own_group = run["review_package"]["per_unit_candidate_sets"][0]
        foreign_group = other_run["review_package"]["per_unit_candidate_sets"][0]
        self.select(pid, cid, run, own_group["unit_id"], foreign_group["candidate_output_ids"][0], expected=400)
        self.generate(pid, cid, board, run=run, units=[foreign_group["unit_id"]], expected=400)
        self.assertEqual(self.episode_snapshot(pid, cid)["run"]["version"], run["version"])

    def test_reference_copy_retains_source_and_blocks_disallowed_retention(self):
        pid = self.project()["project_id"]
        self.approve_setup(pid)
        source = Path(self.temporary.name) / "source-reference.png"
        content = self.png_bytes()
        source.write_bytes(content)
        imported = self.reference(pid, source.read_bytes()).json()
        self.assertTrue(all(record["approval"]["status"] == "pending" for record in imported["setup"].values()))
        asset = next(a for a in imported["assets"] if a["role"] == "reference")
        self.assertEqual(source.read_bytes(), content)
        source.write_bytes(b"original path changed by user")
        self.assertEqual(self.request("GET", asset["url"]).content, content)
        self.assertEqual(asset["sha256"], hashlib.sha256(content).hexdigest())
        reference = imported["setup"]["reference_research"]["references"][0]
        self.assertEqual(reference["use_basis"], "synthetic-owned")
        self.assertEqual(reference["not_to_copy"], ["기존 캐릭터", "기존 대사"])
        record_count = len(imported["records"])
        self.reference(pid, expected=400, retention_allowed="false")
        self.reference(pid, expected=422, use_basis="")
        self.reference(pid, expected=400, use_basis="   ")
        self.reference(pid, expected=400, synthetic="false")
        self.reference(pid, b"invalid raster content", expected=400)
        self.assertEqual(record_count, len(self.snapshot(pid)["records"]))

    def test_plain_backup_restores_complete_copy_with_new_ids_and_reopened_gates(self):
        pid, cid, board, run = self.working_run(cuts=1)
        run = self.select_all(pid, cid, run)
        self.review(pid, run, "G3")
        before = self.snapshot(pid)
        export = self.backup(pid)
        self.assertIn(".toonbackup", export.headers["content-disposition"])
        archived, binary, manifest = unpack_project(export.content)
        self.assertEqual(len(archived["records"]), len(before["records"]))
        self.assertEqual(archived["review_decisions"], before["review_decisions"])
        self.assertEqual(archived["audit_events"], before["audit_events"])
        self.assertEqual(set(binary), {a["storage_key"] for a in before["assets"]})
        source_after_export = self.snapshot(pid)
        copy_project = self.restore(export.content).json()
        restored_pid = copy_project["project_id"]
        self.assertNotEqual(restored_pid, pid)
        self.assertEqual(copy_project["lineage"], {"source_project_id": pid, "source_backup_id": manifest["backup_id"]})
        self.assertEqual(self.snapshot(pid), source_after_export)
        restored = self.snapshot(restored_pid)
        self.assertEqual(len(restored["records"]), len(before["records"]))
        self.assertEqual(len(restored["review_decisions"]), len(before["review_decisions"]))
        self.assertEqual(len(restored["audit_events"]), len(before["audit_events"]) + 1)
        self.assertEqual(len(restored["assets"]), len(before["assets"]))
        self.assertTrue(all(r.get("restored_history") is True for r in restored["review_decisions"]))
        self.assertTrue(all(r["approval"]["status"] == "pending" for r in restored["setup"].values()))
        self.assertTrue({r["artifact_id"] for r in before["records"]}.isdisjoint({r["artifact_id"] for r in restored["records"]}))
        new_cid = restored["episodes"][0]["content_id"]
        self.assertNotEqual(new_cid, cid)
        self.assertEqual(self.episode_snapshot(restored_pid, new_cid)["storyboard"]["approval"]["status"], "pending")
        for old, new in zip(before["assets"], restored["assets"]):
            self.assertNotEqual(old["asset_id"], new["asset_id"])
            self.assertEqual(self.request("GET", old["url"]).content, self.request("GET", new["url"]).content)
        self.generate(restored_pid, new_cid, self.episode_snapshot(restored_pid, new_cid)["storyboard"], expected=409)

    def test_encrypted_backup_wrong_secret_and_damage_do_not_change_projects(self):
        pid = self.project()["project_id"]
        phrase = self.request("GET", "/api/passphrase").json()["passphrase"]
        export = self.backup(pid, encrypted=True, passphrase=phrase)
        self.assertIn(".toonbackup.age", export.headers["content-disposition"])
        self.assertNotIn(phrase.encode(), export.content)
        projects_before = self.request("GET", "/api/projects").json()
        snapshot_before = self.snapshot(pid)
        self.restore(export.content, passphrase="wrong phrase", expected=400)
        self.restore(export.content[:-1] + bytes([export.content[-1] ^ 1]), passphrase=phrase, expected=400)
        self.restore(export.content, expected=400)
        self.assertEqual(self.request("GET", "/api/projects").json(), projects_before)
        self.assertEqual(self.snapshot(pid), snapshot_before)
        restored = self.restore(export.content, passphrase=phrase).json()
        self.assertNotEqual(restored["project_id"], pid)
        archived, _, _ = unpack_project(export.content, passphrase=phrase)
        serialized = json.dumps(archived, ensure_ascii=False)
        self.assertNotIn(phrase, serialized)
        self.assertNotIn(phrase, self.snapshot(pid).__repr__())
        self.assertNotIn(phrase.encode(), (self.data_root / "studio.sqlite3").read_bytes())
        self.assertNotIn(phrase.encode(), self.backup(pid).content)

    def test_plain_damage_missing_asset_and_unsupported_schema_restore_are_atomic(self):
        pid, cid, board = self.working_board(cuts=1)
        export = self.backup(pid)
        projects_before = self.request("GET", "/api/projects").json()
        original = self.snapshot(pid)
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
            files = {r.filename: archive.read(r) for r in archive.infolist()}
        for mode in ("tamper", "missing", "unsupported"):
            mutated = dict(files)
            if mode == "tamper":
                key = next(k for k in files if k.startswith("assets/"))
                mutated[key] = b"changed"
            elif mode == "missing":
                del mutated[next(k for k in files if k.startswith("assets/"))]
            else:
                manifest = json.loads(mutated["manifest.json"])
                manifest["schemas"][0]["schema_version"] = "99.0.0"
                mutated["manifest.json"] = json.dumps(manifest).encode()
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                for name, content in mutated.items():
                    archive.writestr(name, content)
            self.restore(buffer.getvalue(), expected=400)
            self.assertEqual(self.request("GET", "/api/projects").json(), projects_before)
            self.assertEqual(self.snapshot(pid), original)

    def test_asset_checksum_and_stored_schema_mismatch_are_not_served(self):
        pid, cid, board = self.working_board(cuts=1)
        asset = self.snapshot(pid)["assets"][0]
        path = self.app.state.store.safe_path(asset["storage_key"])
        content = path.read_bytes()
        path.write_bytes(b"changed checksum")
        self.request("GET", asset["url"], 400)
        path.write_bytes(content)
        with self.app.state.store.transaction() as db:
            bad = dict(asset)
            bad.pop("url", None)
            bad["schema_version"] = "99.0.0"
            db.execute("UPDATE records SET data=? WHERE project_id=? AND id=? AND version=?", (json.dumps(bad), pid, asset["artifact_id"], asset["version"]))
        self.request("GET", asset["url"], 400)

    def test_host_origin_peer_and_csrf_boundary(self):
        self.assertEqual(self.client.get("/api/bootstrap", headers={"host": "evil.example:8765"}).status_code, 403)
        self.assertEqual(self.client.get("/api/bootstrap", headers={"origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/bootstrap", headers={"sec-fetch-site": "cross-site"}).status_code, 403)
        self.assertEqual(self.client.post("/api/projects", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/projects", headers={"x-csrf-token": "bad"}, json={}).status_code, 403)
        remote = TestClient(self.app, base_url=BASE_URL, client=("192.0.2.8", 50000))
        self.addCleanup(remote.close)
        self.assertEqual(remote.get("/api/bootstrap").status_code, 403)
        accepted = self.request("GET", "/api/health", headers={"origin": BASE_URL})
        self.assertEqual(accepted.json()["adapter"], "mock")
        self.assertEqual(accepted.headers["cache-control"], "no-store")
        self.assertEqual(accepted.headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)

    def test_real_content_and_unrequested_fields_fail_closed(self):
        for data in ({"synthetic": False}, {"synthetic": True, "api_key": "never-persist-this"}):
            response = self.request("POST", "/api/projects", 422, json={
                "name": "합성", "topic": "합성", "protagonist": "합성", "series_direction": "합성", **data,
            })
            self.assertNotIn("never-persist-this", response.text)
        self.assertEqual(self.request("GET", "/api/projects").json(), [])


if __name__ == "__main__":
    unittest.main()
