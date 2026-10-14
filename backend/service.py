"""Stage 01–05 flow with immutable revisions and explicit human review."""
import copy
import hashlib
import io
import shutil

from PIL import Image

from .contracts import artifact, now, ref, validate
from .rendering import compose_preview, render_cut
from .storage import uid

SETUP_KINDS = ("project_brief", "reference_research", "character_package", "account_strategy")
GATES = {"reference_research": "RG", "character_package": "CG", "account_strategy": "SG", "storyboard_package": "G2", "image_generation_run_manifest": "G3"}


class Conflict(ValueError):
    pass


def strings(value):
    return [s.strip() for s in value.split(",") if s.strip()] if isinstance(value, str) else list(value or [])


class Studio:
    def __init__(self, store):
        self.store = store

    def projects(self):
        with self.store.connection() as db:
            import json
            return [json.loads(r[0]) for r in db.execute("SELECT data FROM projects ORDER BY rowid DESC")]

    def asset_dto(self, record):
        return {**record, "url": f"/api/projects/{record['project_id']}/assets/{record['asset_id']}"}

    def snapshot(self, pid):
        with self.store.connection() as db:
            raw = self.store.export_snapshot(db, pid)
            raw["setup"] = {kind: self.store.effective(db, self.store.latest(db, pid, kind)) for kind in SETUP_KINDS}
            raw["records"] = [self.store.effective(db, r) for r in raw["records"]]
            raw["assets"] = [self.asset_dto(r) for r in raw["records"] if r["artifact_type"] == "asset_record"]
            raw["episodes"] = [self.episode_status(db, e) for e in raw["episodes"]]
            return raw

    def episode_status(self, db, episode):
        result = dict(episode)
        board = self.store.latest(db, episode["project_id"], "storyboard_package", episode["content_id"])
        run = self.store.latest(db, episode["project_id"], "image_generation_run_manifest", episode["content_id"])
        if run and board and run["inputs"]["storyboard_package"]["version"] == board["version"]:
            decision = self.store.approval(db, run)
            result["status"] = "ai_draft" if decision and decision["decision"] == "approved" else "draft_review"
        elif board:
            decision = self.store.approval(db, board)
            result["status"] = "storyboard_approved" if decision and decision["decision"] == "approved" else "storyboard_review"
        else:
            result["status"] = "idea"
        return result

    def episode_snapshot(self, pid, cid):
        with self.store.connection() as db:
            e = self.store.episode(db, pid, cid)
            board = self.store.latest(db, pid, "storyboard_package", cid)
            run = self.store.latest(db, pid, "image_generation_run_manifest", cid)
            stale_run = bool(run and board and run["inputs"]["storyboard_package"]["version"] != board["version"])
            return dict(episode=self.episode_status(db, e), brief=self.store.latest(db, pid, "episode_brief", cid), proposals=e.get("proposals", []),
                        storyboard=self.store.effective(db, board) if board else None,
                        run=self.store.effective(db, run) if run else None, run_stale=stale_run,
                        assets=[self.asset_dto(r) for r in self.store.records(db, pid, cid) if r["artifact_type"] == "asset_record"],
                        reviews=[r for r in self.store.list_aux(db, "reviews", pid) if r.get("content_id") == cid],
                        history=[self.store.effective(db, r) for r in self.store.records(db, pid, cid)])

    def setup_records(self, db, project, references=None):
        pid = project["project_id"]
        old_ref = self.store.latest(db, pid, "reference_research")
        selected = references if references is not None else (old_ref["references"] if old_ref else [])
        records = []
        for kind in SETUP_KINDS:
            aid = f"{kind}-{pid}"
            record = artifact(kind, pid, aid, self.store.next_version(db, pid, aid), sources=[ref(r) for r in records])
            record["approval"]["gate"] = GATES.get(kind, "project-brief")
            if kind == "project_brief":
                record["brief"] = dict(account_or_series_direction=project["series_direction"], primary_character={"status": "defined", "character_id": f"character-{pid}", "description": project["protagonist"]}, audience=strings(project["audience"]), tone=strings(project["tone"]), supported_formats=project["supported_formats"], exclusions=strings(project["exclusions"]), reference_questions=[], constraints=["synthetic-only", "human-review-required"])
            elif kind == "reference_research":
                record.update(scope={"topic": project["topic"], "synthetic": True}, references=selected, patterns=[])
            elif kind == "character_package":
                record.update(character_id=f"character-{pid}", identity={"invariants": [{"description": project["protagonist"], "shape": "round-head", "outfit": "teal"}], "controlled_variations": ["pose", "expression"], "forbidden_traits": strings(project["exclusions"])}, behavior_and_voice={"tone": strings(project["tone"])}, sheet={"adapter": "geometric-mock", "synthetic": True}, rights_and_sources={"basis": "synthetic fixture", "not_to_copy": strings(project["exclusions"])})
            else:
                record.update(account_id=f"account-{pid}", account_direction={"topic": project["topic"], "audience": strings(project["audience"]), "tone": strings(project["tone"])}, content_pillars=[{"topic": project["topic"]}], selected_series={"direction": project["series_direction"]}, series=[{"direction": project["series_direction"]}], editorial_constraints={"supported_formats": project["supported_formats"], "exclusions": strings(project["exclusions"])}, experiments=[])
            self.store.insert_record(db, record)
            records.append(record)
        project["setup_version"] = records[0]["version"]
        self.store.write_project(db, project)
        return records

    def create_project(self, data):
        project = {**data, "project_id": uid("project"), "created_at": now(), "synthetic": True}
        for key in ("audience", "tone", "exclusions"):
            project[key] = strings(project[key])
        with self.store.transaction() as db:
            self.store.write_project(db, project)
            self.setup_records(db, project)
            self.store.audit(db, project["project_id"], "create", project["project_id"])
        return project

    def save_setup(self, pid, data):
        with self.store.transaction() as db:
            project = self.store.project(db, pid)
            if data.pop("expected_version") != project["setup_version"]:
                raise Conflict("다른 창에서 설정이 변경되었습니다. 새로 불러온 후 수정해주세요.")
            project.update(data)
            for key in ("audience", "tone", "exclusions"):
                project[key] = strings(project[key])
            records = self.setup_records(db, project)
            self.store.audit(db, pid, "edit", records[0]["artifact_id"], version=records[0]["version"])
        return self.snapshot(pid)

    def import_reference(self, pid, data, filename, source, use_basis, not_to_copy):
        if data.startswith(b"%PDF-"):
            media_type = "application/pdf"
        else:
            try:
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                    media_type = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}[image.format]
            except (Exception,):
                raise ValueError("레퍼런스는 PNG·JPEG·WebP·PDF 파일로 가져올 수 있습니다.") from None
        with self.store.transaction() as db:
            project = self.store.project(db, pid)
            reference = self.store.latest(db, pid, "reference_research")
            owner = dict(reference, version=self.store.next_version(db, pid, reference["artifact_id"]))
            asset = self.store.add_asset(db, owner, data, media_type=media_type, role="reference", origin={"filename": filename, "origin": source, "use_basis": use_basis, "retention_allowed": True})
            refs = reference["references"] + [dict(reference_id=uid("reference"), source={"origin": source, "filename": filename, "asset_id": asset["asset_id"], "sha256": asset["sha256"]}, use_classification="synthetic-permitted-local-copy", use_basis=use_basis, retention_allowed=True, not_to_copy=strings(not_to_copy))]
            self.setup_records(db, project, refs)
            self.store.audit(db, pid, "create", asset["artifact_id"], version=asset["version"])
        return self.snapshot(pid)

    def require_setup(self, db, pid):
        setup = [self.store.latest(db, pid, k) for k in SETUP_KINDS]
        for record in setup[1:]:
            decision = self.store.approval(db, record)
            if not decision or decision["decision"] != "approved":
                raise Conflict(f"프로젝트 설정의 {GATES[record['artifact_type']]} 사람 검토를 먼저 승인해주세요.")
        return setup

    def require_current_inputs(self, db, record):
        for source in record["source_artifact_refs"]:
            original = self.store.exact(db, record["project_id"], source["artifact_id"], source["version"])
            latest = self.store.latest(db, record["project_id"], original["artifact_type"], original.get("content_id"))
            if latest["artifact_id"] != original["artifact_id"] or latest["version"] != original["version"]:
                raise Conflict("입력 설정 또는 콘티가 새 버전으로 변경되었습니다. 콘티를 새 버전으로 저장하고 다시 검토해주세요.")

    def create_episode(self, pid, data):
        with self.store.transaction() as db:
            project = self.store.project(db, pid)
            cid = uid("episode")
            fmt = data["requested_format"] or data.get("reference_format") or ("single_panel" if data["cut_count"] == 1 else "multi_panel")
            if (fmt == "single_panel") != (data["cut_count"] == 1):
                raise ValueError("1컷 형식은 컷 수를 1로, 다컷 형식은 2개 이상으로 맞춰주세요.")
            conflict = bool(data.get("reference_format") and data["requested_format"] and data["reference_format"] != data["requested_format"])
            ambiguous = data["requested_format"] is None
            questions = ["요청과 레퍼런스의 형식을 확인해주세요."] if (conflict or ambiguous) and not data["format_confirmed"] else []
            if fmt not in project["supported_formats"]:
                raise ValueError("프로젝트에서 지원하지 않는 형식입니다.")
            proposals = []
            if data["input_mode"] == "short_topic":
                for i, title in enumerate(("작은 시행착오", "시선 바꾸기", "따뜻한 마무리")):
                    story = f"가상 주인공이 '{data['supplied_material']}' 상황을 만난다.\n작은 시도를 하며 예상과 다른 결과를 발견한다.\n{title}의 관점으로 상황을 다시 바라본다.\n변화를 받아들이며 짧게 마무리한다."
                    proposals.append({"id": f"proposal-{i+1}", "title": title, "story": story, "synthetic": True, "adapter": "mock"})
            episode = dict(**data, project_id=pid, content_id=cid, created_at=now(), status="idea", proposals=proposals, selected_format=fmt)
            self.store.write_episode(db, episode)
            brief = artifact("episode_brief", pid, f"brief-{cid}", content_id=cid, sources=[ref(self.store.latest(db, pid, k)) for k in SETUP_KINDS])
            brief.update(input={"mode": data["input_mode"], "supplied_material": data["supplied_material"], "requested_edit_scope": data["requested_edit_scope"], "requested_format": data["requested_format"], "format_confirmed": data["format_confirmed"], "reference_format": data.get("reference_format"), "episode_constraints": ["synthetic-only", "mock-only"]}, unresolved_questions=questions)
            self.store.insert_record(db, brief)
            self.store.audit(db, pid, "create", brief["artifact_id"], version=brief["version"], cid=cid)
        return {"episode": episode, "brief": brief, "proposals": proposals}

    @staticmethod
    def distribute_text(text, count):
        # Slice the exact source without stripping characters or inventing dialogue.
        lines = text.splitlines(keepends=True) or [text]
        chunks = ["" for _ in range(count)]
        for i, line in enumerate(lines):
            chunks[min(count - 1, i * count // len(lines))] += line
        return chunks

    def storyboard(self, pid, cid, data):
        with self.store.transaction() as db:
            e = self.store.episode(db, pid, cid)
            setup = self.require_setup(db, pid)
            brief = self.store.latest(db, pid, "episode_brief", cid)
            prior = self.store.latest(db, pid, "storyboard_package", cid)
            if data.get("expected_version") != (prior["version"] if prior else None):
                raise Conflict("콘티 버전이 변경되었습니다. 새로 불러온 후 수정해주세요.")
            if brief["unresolved_questions"] and not (data.get("format_confirmed") or e["format_confirmed"]):
                raise Conflict("형식이 불명확하거나 요청과 레퍼런스가 다릅니다. 사용할 형식을 확인해주세요.")
            if prior:
                selected_story = prior["story"]["selected_story"]
            elif e["input_mode"] == "developed_story":
                selected_story = e["supplied_material"]
            else:
                matches = [p for p in e["proposals"] if p["id"] == data.get("proposal_id")]
                if not matches:
                    raise ValueError("모의 이야기 방향을 하나 선택해주세요.")
                selected_story = matches[0]["story"]
            if data.get("units"):
                if not prior:
                    raise ValueError("첫 콘티를 만든 후 대사와 컷 설명을 수정해주세요.")
                units = data["units"]
                old = prior["storyboard"]["units"]
                if [(u["unit_id"], u["order"]) for u in units] != [(u["unit_id"], u["order"]) for u in old]:
                    raise ValueError("이번 범위에서는 대사와 컷 설명을 수정할 수 있습니다. 컷 순서와 ID는 유지해주세요.")
                units = [{**original, **edited} for original, edited in zip(old, units)]
            elif prior:
                units = copy.deepcopy(prior["storyboard"]["units"])
            else:
                text_chunks = self.distribute_text(selected_story, e["cut_count"])
                units = [dict(unit_id=f"unit-{cid}-{i+1}", order=i+1, beat_id=f"beat-{i+1}", action=f"가상 장면 {i+1}: 주인공의 상황과 행동을 보여준다.", dialogue=chunk, composition="주인공 중심의 간단한 구도", continuity="둥근 머리와 청록색 옷을 유지", character_id=setup[2]["character_id"]) for i, chunk in enumerate(text_chunks)]
            aid = f"storyboard-{cid}"
            board = artifact("storyboard_package", pid, aid, self.store.next_version(db, pid, aid), cid, sources=[ref(r) for r in setup] + [ref(brief)])
            board["approval"]["gate"] = "G2"
            board["story"] = {"selected_story": selected_story, "supplied_material": e["supplied_material"], "preservation_scope": e["requested_edit_scope"], "structure": {"beats": [{"beat_id": u["beat_id"], "order": u["order"], "action": u["action"]} for u in units]}, "text_objects": [{"unit_id": u["unit_id"], "text": u["dialogue"], "responsibility": "human-review"} for u in units]}
            if prior and data.get("units"):
                changes = [dict(unit_id=u["unit_id"], fields=[key for key in ("action", "dialogue", "composition", "continuity") if u[key] != old[key]]) for old, u in zip(prior["storyboard"]["units"], units)]
                board["provenance"]["human_requested_edits"] = [c for c in changes if c["fields"]]
                board["story"]["preservation_scope"] = sorted(set(e["requested_edit_scope"]) | {key for c in changes for key in c["fields"]})
            board["content_scope"] = {"format_decision": {"selected_format": e["selected_format"], "confirmed_by": "local-user", "rationale": "사용자가 선택한 요청 형식과 컷 수", "reference_conflict_confirmed": bool(data.get("format_confirmed") or e["format_confirmed"])}}
            board["source_versions"] = {r["artifact_type"]: ref(r) for r in setup}
            rough = []
            for unit in units:
                asset = self.store.add_asset(db, board, render_cut(unit, rough=True, character=setup[2]), role="storyboard_rough")
                unit["rough_asset_id"] = asset["asset_id"]
                unit["rough_asset_url"] = self.asset_dto(asset)["url"]
                rough.append(self.store.asset_bytes(asset))
            preview = self.store.add_asset(db, board, compose_preview(rough), role="storyboard_preview")
            board["storyboard"] = {"units": units, "composed_preview_asset_id": preview["asset_id"]}
            self.store.insert_record(db, board)
            self.store.audit(db, pid, "edit" if prior else "create", aid, version=board["version"], cid=cid, before=prior, after=board)
        return self.episode_snapshot(pid, cid)

    def review(self, pid, data):
        with self.store.transaction() as db:
            record = self.store.exact(db, pid, data["artifact_id"], data["version"])
            gate = GATES.get(record["artifact_type"])
            if gate != data["gate"]:
                raise ValueError("산출물에 맞는 승인 게이트를 선택해주세요.")
            latest = self.store.latest(db, pid, record["artifact_type"], record.get("content_id"))
            if latest["version"] != record["version"] or latest["artifact_id"] != record["artifact_id"]:
                raise Conflict("이전 버전은 현재 승인할 수 없습니다. 현재 버전을 검토해주세요.")
            if self.store.approval(db, record):
                raise Conflict("이미 검토한 버전입니다. 수정한 새 버전에서 다시 검토해주세요.")
            if data["decision"] != "approved" and not data["notes"].strip():
                raise ValueError("수정 또는 반려 이유를 남겨주세요.")
            if gate in ("RG", "CG", "SG"):
                self.require_current_inputs(db, record)
                dependencies = ("reference_research",) if gate == "CG" else ("reference_research", "character_package") if gate == "SG" else ()
                for kind in dependencies:
                    dependency = self.store.latest(db, pid, kind)
                    approval = self.store.approval(db, dependency)
                    if not approval or approval["decision"] != "approved":
                        raise Conflict(f"먼저 {GATES[kind]} 검토를 승인해주세요.")
            if gate == "G2":
                self.require_setup(db, pid)
                self.require_current_inputs(db, record)
            if gate == "G3":
                self.require_setup(db, pid)
                self.require_run_board(db, record)
                if data["decision"] == "approved" and any(not group.get("selected_output_id") for group in record["review_package"]["per_unit_candidate_sets"]):
                    raise Conflict("모든 컷의 후보를 선택한 후 초안을 승인해주세요.")
            decision = dict(record_type="review_decision", review_decision_id=uid("review"), project_id=pid, gate=gate, artifact_ref=ref(record), actor="local-user", decision=data["decision"], decided_at=now(), notes=data["notes"], next_state=("storyboard" if gate == "G2" else "ai_draft" if gate == "G3" else "project-setup") if data["decision"] == "approved" else "rework", synthetic=True)
            if record.get("content_id"):
                decision["content_id"] = record["content_id"]
            self.store.insert_aux(db, decision)
            self.store.audit(db, pid, "review", record["artifact_id"], version=record["version"], cid=record.get("content_id"), result=data["decision"])
        return self.snapshot(pid)

    def require_run_board(self, db, run):
        source = run["inputs"]["storyboard_package"]
        board = self.store.latest(db, run["project_id"], "storyboard_package", run["content_id"])
        if not board:
            raise Conflict("현재 콘티가 누락되었습니다.")
        decision = self.store.approval(db, board)
        if not board or board["version"] != source["version"] or board["artifact_id"] != source["artifact_id"] or not decision or decision["decision"] != "approved":
            raise Conflict("콘티의 현재 버전을 G2에서 승인한 후 다시 초안을 만들어주세요.")
        self.require_current_inputs(db, board)
        return board

    def compose_run(self, db, run):
        candidates = {o["output_id"]: o for o in run["outputs"] if o["role"] == "per_unit_candidate"}
        images = []
        selected = []
        for group in run["review_package"]["per_unit_candidate_sets"]:
            output_id = group.get("selected_output_id") or group["candidate_output_ids"][0]
            output = candidates[output_id]
            images.append(self.store.asset_bytes(self.store.asset(db, run["project_id"], output["asset_id"])))
            if group.get("selected_output_id"):
                selected.append(output_id)
        asset = self.store.add_asset(db, run, compose_preview(images), role="episode_preview")
        run["outputs"] = [o for o in run["outputs"] if o["role"] == "per_unit_candidate"] + [{"output_id": uid("output"), "role": "episode_preview", "asset_id": asset["asset_id"], "status": "candidate"}]
        run["review_package"]["composed_preview_asset_id"] = asset["asset_id"]
        run["review_package"]["selected_output_ids"] = selected

    def generate(self, pid, cid, data):
        with self.store.transaction() as db:
            self.store.episode(db, pid, cid)
            setup = self.require_setup(db, pid)
            board = self.store.latest(db, pid, "storyboard_package", cid)
            if not board or board["version"] != data["expected_storyboard_version"]:
                raise Conflict("콘티 버전이 변경되었습니다.")
            decision = self.store.approval(db, board)
            if not decision or decision["decision"] != "approved":
                raise Conflict("G2 사람 승인이 필요합니다.")
            self.require_current_inputs(db, board)
            prior = self.store.latest(db, pid, "image_generation_run_manifest", cid)
            if (prior["version"] if prior else None) != data.get("expected_run_version"):
                raise Conflict("초안 버전이 변경되었습니다. 현재 초안을 다시 불러와주세요.")
            units = board["storyboard"]["units"]
            unit_ids = data.get("unit_ids") or [u["unit_id"] for u in units]
            if len(set(unit_ids)) != len(unit_ids) or not set(unit_ids).issubset({u["unit_id"] for u in units}):
                raise ValueError("선택한 컷이 현재 에피소드에 속하지 않습니다.")
            same_board = bool(prior and prior["inputs"]["storyboard_package"]["version"] == board["version"])
            if not same_board and set(unit_ids) != {u["unit_id"] for u in units}:
                raise Conflict("새 콘티 버전은 전체 컷의 초안을 먼저 생성해주세요.")
            aid = f"manifest-{cid}"
            run = artifact("image_generation_run_manifest", pid, aid, self.store.next_version(db, pid, aid), cid, sources=[ref(board)] + ([ref(prior)] if prior else []))
            run.update(state="candidate", approval={"status": "pending", "gate": "G3"}, run={"run_id": uid("run"), "purpose": "selected_cut_regeneration" if prior else "mock_candidate", "unit_ids": unit_ids, "status": "completed"}, inputs={"storyboard_package": {**ref(board), "approval_gate": "G2", "approval_status": "approved"}}, outputs=copy.deepcopy(prior["outputs"]) if same_board else [], review_package=copy.deepcopy(prior["review_package"]) if same_board else {"per_unit_candidate_sets": [{"unit_id": u["unit_id"], "candidate_output_ids": [], "selected_output_id": None} for u in units], "composed_preview_asset_id": "pending", "selected_output_ids": []}, adapter={"kind": "mock", "synthetic": True, "version": "1.0.0"})
            groups = {g["unit_id"]: g for g in run["review_package"]["per_unit_candidate_sets"]}
            for unit in units:
                if unit["unit_id"] not in unit_ids:
                    continue
                group = groups[unit["unit_id"]]
                attempt = len(group["candidate_output_ids"]) // 2
                for variant in (attempt * 2, attempt * 2 + 1):
                    asset = self.store.add_asset(db, run, render_cut(unit, variant=variant, character=setup[2]), role="per_unit_candidate")
                    output_id = uid("output")
                    run["outputs"].append({"output_id": output_id, "role": "per_unit_candidate", "asset_id": asset["asset_id"], "unit_id": unit["unit_id"], "status": "candidate", "variant": variant + 1, "prompt_sha256": hashlib.sha256((unit["action"] + unit["dialogue"]).encode()).hexdigest(), "seed": variant})
                    group["candidate_output_ids"].append(output_id)
                group["selected_output_id"] = None
            self.compose_run(db, run)
            self.store.insert_record(db, run)
            self.store.audit(db, pid, "regenerate" if prior else "create", aid, version=run["version"], cid=cid, before=prior, after=run)
        return self.episode_snapshot(pid, cid)

    def select(self, pid, cid, data):
        with self.store.transaction() as db:
            self.store.episode(db, pid, cid)
            self.require_setup(db, pid)
            prior = self.store.latest(db, pid, "image_generation_run_manifest", cid)
            if not prior or prior["version"] != data["expected_run_version"]:
                raise Conflict("초안 버전이 변경되었습니다.")
            self.require_run_board(db, prior)
            run = copy.deepcopy(prior)
            run.update(version=self.store.next_version(db, pid, run["artifact_id"]), created_at=now(), approval={"status": "pending", "gate": "G3"}, source_artifact_refs=[ref(prior), ref(self.store.latest(db, pid, "storyboard_package", cid))])
            groups = [g for g in run["review_package"]["per_unit_candidate_sets"] if g["unit_id"] == data["unit_id"]]
            if not groups or data["output_id"] not in groups[0]["candidate_output_ids"]:
                raise ValueError("해당 컷의 이미지 후보를 선택해주세요.")
            groups[0]["selected_output_id"] = data["output_id"]
            self.compose_run(db, run)
            self.store.insert_record(db, run)
            self.store.audit(db, pid, "select", run["artifact_id"], version=run["version"], cid=cid, before=prior, after=run)
        return self.episode_snapshot(pid, cid)

    def restore_snapshot(self, snapshot, assets, manifest):
        original_pid = snapshot["project"]["project_id"]
        if snapshot["project"].get("synthetic") is not True:
            raise ValueError("현재 모드에서는 합성 프로젝트 백업만 복구할 수 있습니다.")
        records = snapshot["records"]
        keys = {(r["artifact_id"], r["version"]) for r in records}
        episodes = {e["content_id"] for e in snapshot["episodes"]}
        if len(keys) != len(records) or len(episodes) != len(snapshot["episodes"]):
            raise ValueError("중복된 산출물 또는 에피소드가 있습니다.")

        def verify_tree(value):
            if isinstance(value, dict):
                if "project_id" in value and value["project_id"] != original_pid:
                    raise ValueError("백업에 다른 프로젝트 자료가 포함되어 있습니다.")
                if "content_id" in value and value["content_id"] not in episodes:
                    raise ValueError("에피소드 참조가 누락되었습니다.")
                if "artifact_type" not in value and all(k in value for k in ("artifact_id", "version", "project_id")) and (value["artifact_id"], value["version"]) not in keys:
                    raise ValueError("정확한 입력 버전이 백업에서 누락되었습니다.")
                for v in value.values():
                    verify_tree(v)
            elif isinstance(value, list):
                for v in value:
                    verify_tree(v)
        verify_tree(snapshot)
        for r in records + snapshot["review_decisions"] + snapshot["audit_events"]:
            validate(r)
        if any(r["provenance"].get("synthetic") is not True for r in records):
            raise ValueError("실제 제작 산출물은 현재 모드에서 복구할 수 없습니다.")
        binary_records = [r for r in records if r["artifact_type"] == "asset_record"]
        if set(assets) != {r["storage_key"] for r in binary_records}:
            raise ValueError("자산 파일 목록이 일치하지 않습니다.")
        pid = uid("project")
        mapping = {original_pid: pid}
        for e in snapshot["episodes"]:
            mapping[e["content_id"]] = uid("episode")
        for r in records:
            for key in ("artifact_id", "asset_id", "character_id", "account_id"):
                if r.get(key):
                    mapping.setdefault(r[key], uid(key.replace("_id", "")))
        for r in snapshot["review_decisions"] + snapshot["audit_events"]:
            key = "review_decision_id" if r["record_type"] == "review_decision" else "event_id"
            mapping[r[key]] = uid("review" if key.startswith("review") else "event")

        def remap(value):
            if isinstance(value, dict):
                return {k: remap(v) for k, v in value.items()}
            if isinstance(value, list):
                return [remap(v) for v in value]
            return mapping.get(value, value) if isinstance(value, str) else value
        copied = remap(snapshot)
        project = copied["project"]
        project.update(name=project["name"] + " (복구본)", created_at=now(), lineage={"source_project_id": original_pid, "source_backup_id": manifest["backup_id"]})
        for review in copied["review_decisions"]:
            # Preserve historical decisions without inheriting approval authority in a new project.
            review["restored_history"] = True
        new_binary = {}
        for old, new in zip(records, copied["records"]):
            new["provenance"]["restore"] = {"source_project_id": original_pid, "source_artifact_id": old["artifact_id"], "source_version": old["version"], "source_backup_id": manifest["backup_id"]}
            if new["artifact_type"] == "asset_record":
                data = assets[old["storage_key"]]
                if hashlib.sha256(data).hexdigest() != new["sha256"] or len(data) != new["byte_size"]:
                    raise ValueError("복구 자산 체크섬 불일치")
                ext = old["storage_key"].rsplit(".", 1)[-1]
                new["storage_key"] = f"projects/{pid}/assets/{new['asset_id']}/{new['version']}/{new['sha256']}.{ext}"
                new_binary[new["storage_key"]] = data
            if new["artifact_type"] == "storyboard_package":
                for unit in new["storyboard"]["units"]:
                    unit["rough_asset_url"] = f"/api/projects/{pid}/assets/{unit['rough_asset_id']}"
        try:
            with self.store.transaction() as db:
                self.store.write_project(db, project)
                for episode in copied["episodes"]:
                    self.store.write_episode(db, episode)
                for key, data in new_binary.items():
                    self.store.write_binary(key, data)
                # Record references can include assets whose owner is registered later in the same transaction.
                for record in copied["records"]:
                    self.store.insert_record(db, record)
                for record in copied["review_decisions"] + copied["audit_events"]:
                    self.store.insert_aux(db, record)
                self.store.audit(db, pid, "restore", pid, result="copy-created-human-gates-reopened")
        except BaseException:
            target = (self.store.root / "projects" / pid).resolve()
            if target.is_relative_to((self.store.root / "projects").resolve()) and target.name == pid and target.exists():
                shutil.rmtree(target)
            raise
        return project
