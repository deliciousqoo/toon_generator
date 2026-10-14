"""Bounded end-to-end verification against an owned loopback Uvicorn process.

Uses disposable synthetic data. Passphrases exist only in memory/HTTP bodies;
neither command arguments, environment variables nor diagnostic files contain
them. Run with the repository's pinned Python environment.
"""

from __future__ import annotations

import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
STAGE = "initialization"


class SmokeFailure(RuntimeError):
    pass


def stage(name: str) -> None:
    global STAGE
    STAGE = name
    print(json.dumps({"stage": name}, ensure_ascii=False), flush=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def sanitize(text: str, secrets: list[str]) -> str:
    for value in secrets:
        if value:
            text = text.replace(value, "[redacted]")
    text = re.sub(r"(?i)(passphrase|password|api_key|csrf_token)\s*[:=]\s*[^\s,}]+", r"\1=[redacted]", text)
    return text[-10000:]


def main() -> int:
    child = None
    temporary = None
    secret_literals: list[str] = []
    completed = False
    failure = None
    stderr = b""
    stderr_buffer = bytearray()
    stdout_buffer = bytearray()
    drain_threads = []
    started = time.monotonic()
    try:
        test_root = ROOT / ".test-data"
        test_root.mkdir(exist_ok=True)
        if os.name == "nt" and not str(test_root).startswith("\\\\?\\"):
            test_root = Path("\\\\?\\" + str(test_root))
        temporary = tempfile.TemporaryDirectory(prefix="http-smoke-", dir=test_root)
        data_root = Path(temporary.name) / "store"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        require(port >= 1024, "Ephemeral loopback port is outside the launcher range.")
        stage("launch-owned-loopback-server")
        # A periodic stack dump diagnoses a blocked Python thread without locals
        # or submitted request data. The output remains in an in-memory pipe.
        launcher = (
            "import faulthandler; "
            "faulthandler.dump_traceback_later(10, repeat=True); "
            "from backend.__main__ import main; main()"
        )
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", launcher, "--no-browser", "--port", str(port), "--data-root", str(data_root)],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        def drain(stream, buffer):
            try:
                while chunk := stream.read1(4096):
                    buffer.extend(chunk)
                    if len(buffer) > 65536:
                        del buffer[:-65536]
            except (OSError, ValueError):
                pass
        # Drain immediately: Windows pipe capacity is small, and a diagnostic
        # stack dump must never block the process being verified.
        for stream, buffer in ((child.stdout, stdout_buffer), (child.stderr, stderr_buffer)):
            thread = threading.Thread(target=drain, args=(stream, buffer), daemon=True)
            thread.start()
            drain_threads.append(thread)
        base = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=base, trust_env=False, timeout=httpx.Timeout(10, connect=1, pool=2)) as client:
            deadline = time.monotonic() + 20
            health = None
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise SmokeFailure("Owned server exited before readiness.")
                try:
                    response = client.get("/api/health")
                    if response.status_code == 200:
                        health = response.json()
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.1)
            require(health is not None, "Loopback health did not become ready within 20 seconds.")
            require(health["mode"] == "platform_build" and health["adapter"] == "mock", "Unexpected execution mode or adapter.")
            token = client.get("/api/bootstrap").json()["csrf_token"]
            secret_literals.append(token)

            def request(method, path, expected=200, **kwargs):
                headers = {"x-csrf-token": token, **kwargs.pop("headers", {})}
                response = client.request(method, path, headers=headers, **kwargs)
                if response.status_code != expected:
                    # Report the endpoint and status; never echo request bodies.
                    raise SmokeFailure(f"{method} {path} returned {response.status_code}; expected {expected}.")
                return response

            def snapshot(pid):
                return request("GET", f"/api/projects/{pid}").json()

            def review(pid, record, gate):
                request("POST", f"/api/projects/{pid}/reviews", json={
                    "artifact_id": record["artifact_id"], "version": record["version"],
                    "gate": gate, "decision": "approved", "notes": "Synthetic real HTTP smoke review",
                })

            stage("health-and-request-boundary")
            require(client.get("/api/health", headers={"host": "outside.invalid"}).status_code == 403, "Foreign Host was accepted.")
            require(client.get("/api/health", headers={"origin": "https://outside.invalid"}).status_code == 403, "Foreign Origin was accepted.")
            require(client.post("/api/projects", json={}).status_code == 403, "Missing CSRF token was accepted.")
            require(client.post("/api/projects", headers={"x-csrf-token": "wrong"}, json={}).status_code == 403, "Wrong CSRF token was accepted.")

            stage("synthetic-project-and-setup-gates")
            project = request("POST", "/api/projects", 201, json={
                "name": "합성 HTTP 검증 프로젝트", "topic": "가상의 관찰", "protagonist": "합성 둥근 주인공",
                "series_direction": "합성 단편", "audience": ["synthetic"], "tone": ["차분함"],
                "supported_formats": ["single_panel", "multi_panel"], "exclusions": ["실제 자료"], "synthetic": True,
            }).json()
            pid = project["project_id"]
            setup = snapshot(pid)["setup"]
            for kind, gate in (("reference_research", "RG"), ("character_package", "CG"), ("account_strategy", "SG")):
                review(pid, setup[kind], gate)

            stage("developed-story-and-level-one-storyboard")
            raw_story = "  합성 첫 장면 그대로  \r\n합성 둘째 장면\n합성 마지막 장면\n"
            episode = request("POST", f"/api/projects/{pid}/episodes", 201, json={
                "title": "합성 HTTP 에피소드", "input_mode": "developed_story", "supplied_material": raw_story,
                "requested_edit_scope": [], "requested_format": "multi_panel", "reference_format": None,
                "cut_count": 2, "format_confirmed": False, "synthetic": True,
            }).json()
            cid = episode["episode"]["content_id"]
            path = f"/api/projects/{pid}/episodes/{cid}"
            board_result = request("POST", path + "/storyboard", json={}).json()
            board = board_result["storyboard"]
            require("".join(u["dialogue"] for u in board["storyboard"]["units"]) == raw_story, "Developed story source changed.")
            require(board["story"]["selected_story"] == raw_story, "Selected story source changed.")
            for asset in board_result["assets"]:
                response = request("GET", asset["url"])
                with Image.open(io.BytesIO(response.content)) as image:
                    require(image.info.get("synthetic") == "true", "Storyboard asset lacks synthetic label.")

            stage("g2-generation-selection-and-g3")
            generation = {"expected_storyboard_version": board["version"], "expected_run_version": None, "unit_ids": None}
            request("POST", path + "/generate", 409, json=generation)
            review(pid, board, "G2")
            result = request("POST", path + "/generate", json=generation).json()
            run = result["run"]
            request("POST", f"/api/projects/{pid}/reviews", 409, json={
                "artifact_id": run["artifact_id"], "version": run["version"], "gate": "G3", "decision": "approved", "notes": "",
            })
            for group in list(run["review_package"]["per_unit_candidate_sets"]):
                run = request("POST", path + "/selection", json={
                    "expected_run_version": run["version"], "unit_id": group["unit_id"], "output_id": group["candidate_output_ids"][0],
                }).json()["run"]
            review(pid, run, "G3")
            require(request("GET", path).json()["episode"]["status"] == "ai_draft", "Explicit G3 did not complete the synthetic cycle.")

            stage("plain-backup-and-nondestructive-restore")
            plain = request("POST", f"/api/projects/{pid}/backup", json={"encrypted": False, "passphrase": None}).content
            original_after_export = snapshot(pid)
            restored = request("POST", "/api/restore", 201, files={"file": ("synthetic.toonbackup", plain, "application/octet-stream")}).json()
            require(restored["project_id"] != pid and restored["lineage"]["source_project_id"] == pid, "Restore did not create a separate copy.")
            copy_snapshot = snapshot(restored["project_id"])
            require(len(copy_snapshot["records"]) == len(original_after_export["records"]), "Restored record history is incomplete.")
            require(len(copy_snapshot["assets"]) == len(original_after_export["assets"]), "Restored binary history is incomplete.")
            require(all(record["approval"]["status"] == "pending" for record in copy_snapshot["setup"].values()), "Copy inherited approval authority.")
            require(snapshot(pid) == original_after_export, "Restore modified its source project.")

            stage("age-backup-failures-and-copy-restore")
            phrase = request("GET", "/api/passphrase").json()["passphrase"]
            secret_literals.append(phrase)
            encrypted = request("POST", f"/api/projects/{pid}/backup", json={"encrypted": True, "passphrase": phrase}).content
            require(encrypted.startswith(b"age-encryption.org/v1\n"), "Encrypted output is not binary age format.")
            require(phrase.encode() not in encrypted, "Passphrase appeared in the encrypted file.")
            projects_before = request("GET", "/api/projects").json()
            source_before = snapshot(pid)
            request("POST", "/api/restore", 400, files={"file": ("encrypted.toonbackup.age", encrypted, "application/octet-stream")}, data={"passphrase": "wrong synthetic phrase"})
            damaged = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
            request("POST", "/api/restore", 400, files={"file": ("encrypted.toonbackup.age", damaged, "application/octet-stream")}, data={"passphrase": phrase})
            request("POST", "/api/restore", 400, files={"file": ("damaged.toonbackup", b"invalid archive", "application/octet-stream")})
            require(request("GET", "/api/projects").json() == projects_before and snapshot(pid) == source_before, "Failed restores changed projects.")
            encrypted_copy = request("POST", "/api/restore", 201, files={"file": ("encrypted.toonbackup.age", encrypted, "application/octet-stream")}, data={"passphrase": phrase}).json()
            require(encrypted_copy["project_id"] not in {pid, restored["project_id"]}, "Encrypted restore reused an existing project.")
            require(snapshot(pid) == source_before, "Encrypted restore changed its source.")
            require(phrase not in json.dumps(snapshot(pid), ensure_ascii=False), "Passphrase persisted in project metadata.")

            stage("owned-server-shutdown")
            request("POST", "/api/shutdown")
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise SmokeFailure("Owned server did not honor its shutdown callback.") from None
            require(child.returncode == 0, "Owned server exited with an error after shutdown.")
            completed = True
    except Exception as exc:
        # Application/user errors are reported by stage and type, not arbitrary
        # exception repr that could expose submitted passphrases or body data.
        failure = str(exc) if isinstance(exc, SmokeFailure) else f"{type(exc).__name__} during {STAGE}"
    finally:
        if child is not None:
            if child.poll() is None:
                if os.name == "nt":
                    # A Windows virtual-environment Python redirector may own
                    # the interpreter as a descendant. Kill only this spawned
                    # PID's tree so a failed smoke cannot leave a listener alive.
                    subprocess.run(
                        ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            for thread in drain_threads:
                thread.join(timeout=2)
            stderr = bytes(stderr_buffer)
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    stream.close()
        if temporary is not None:
            try:
                temporary.cleanup()
            except OSError:
                failure = failure or "Disposable test data cleanup failed."
                completed = False
    if completed:
        print(json.dumps({"result": "passed", "transport": "real-loopback-http", "adapter": "mock", "elapsed_seconds": round(time.monotonic() - started, 2)}), flush=True)
        return 0
    print(json.dumps({"result": "failed", "stage": STAGE, "detail": failure}, ensure_ascii=False), flush=True)
    if stderr:
        print(sanitize(stderr.decode("utf-8", "replace"), secret_literals), file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
