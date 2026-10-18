"""Loopback-only HTTP boundary, DTOs, offline stage flow, and static UI."""
import ipaddress
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import APP_VERSION
from .backup import evaluate_passphrase, generate_passphrase, pack_project, unpack_project
from .contracts import ROOT, SCHEMA_VERSION
from .native_save import save_backup_file
from .service import Conflict, Studio
from .storage import Store
from .studio import create_studio_router
from .chatgpt_auth import ChatGPTAuth, ChatGPTAuthError
from .chatgpt_provider import ChatGPTCharacterProvider
from .chatgpt_routes import create_chatgpt_router
from .character_workers import DeterministicCharacterProvider

MAX_BACKUP = 256 * 1024 * 1024


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectInput(Input):
    name: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=1000)
    protagonist: str = Field(min_length=1, max_length=2000)
    audience: list[str] | str = Field(default_factory=list)
    tone: list[str] | str = Field(default_factory=list)
    series_direction: str = Field(min_length=1, max_length=3000)
    supported_formats: list[Literal["single_panel", "multi_panel"]] = Field(default_factory=lambda: ["single_panel", "multi_panel"], min_length=1, max_length=2)
    exclusions: list[str] | str = Field(default_factory=list)
    synthetic: Literal[True]


class SetupInput(ProjectInput):
    expected_version: str


class EpisodeInput(Input):
    title: str = Field(min_length=1, max_length=120)
    input_mode: Literal["short_topic", "developed_story"]
    supplied_material: str = Field(min_length=1, max_length=20000)
    requested_edit_scope: list[str] = Field(default_factory=list, max_length=20)
    requested_format: Literal["single_panel", "multi_panel"] | None = None
    reference_format: Literal["single_panel", "multi_panel"] | None = None
    cut_count: int = Field(ge=1, le=8)
    format_confirmed: bool = False
    synthetic: Literal[True]


class UnitInput(Input):
    unit_id: str
    order: int = Field(ge=1, le=8)
    action: str = Field(min_length=1, max_length=3000)
    dialogue: str = Field(default="", max_length=20000)
    composition: str = Field(default="주인공 중심의 간단한 구도", max_length=3000)
    continuity: str = Field(default="둥근 머리와 청록색 옷을 유지", max_length=3000)


class BoardInput(Input):
    expected_version: str | None = None
    proposal_id: str | None = None
    units: list[UnitInput] | None = Field(default=None, min_length=1, max_length=8)
    format_confirmed: bool = False


class ReviewInput(Input):
    artifact_id: str
    version: str
    gate: Literal["RG", "CG", "SG", "G2", "G3"]
    decision: Literal["approved", "rework", "rejected"]
    notes: str = Field(default="", max_length=3000)


class GenerateInput(Input):
    expected_storyboard_version: str
    expected_run_version: str | None = None
    unit_ids: list[str] | None = Field(default=None, min_length=1, max_length=8)


class SelectionInput(Input):
    expected_run_version: str
    unit_id: str
    output_id: str


class BackupInput(Input):
    encrypted: bool
    passphrase: str | None = Field(default=None, max_length=512)


def default_data_root():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "ToonStudio"


def create_app(data_root=None, *, port=8765, dev=False, character_fixture=False, chatgpt_auth=None):
    store = Store(data_root or default_data_root())
    studio = Studio(store)
    auth = chatgpt_auth or ChatGPTAuth(store.root)
    provider = DeterministicCharacterProvider() if character_fixture else ChatGPTCharacterProvider(auth)
    try:
        studio_router = create_studio_router(store.root, character_provider=provider)
    except Exception:
        auth.close()
        raise

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            try:
                studio_router.characters.close()
            finally:
                try:
                    studio_router.service.close()
                finally:
                    auth.close()

    app = FastAPI(title="Toon Studio local", version=APP_VERSION, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.studio = store, studio
    app.state.workflow_studio = studio_router.service
    app.state.character_studio = studio_router.characters
    app.state.chatgpt_auth = auth
    app.include_router(studio_router)
    app.include_router(create_chatgpt_router(auth, port=port, fixture=character_fixture))
    token = secrets.token_urlsafe(32)
    ports = {port} | ({5173} if dev else set())
    allowed_hosts = {f"{host}:{p}" for host in ("127.0.0.1", "localhost") for p in ports}

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        host = request.headers.get("host", "").lower()
        try:
            local_client = ipaddress.ip_address(request.client.host).is_loopback
        except (ValueError, AttributeError):
            local_client = False
        if not local_client or host not in allowed_hosts:
            return JSONResponse({"detail": "이 앱은 현재 PC에서만 접속할 수 있습니다."}, status_code=403)
        # OAuth alone returns from an external origin. State/nonce/PKCE are checked
        # by this exact GET callback; every other route keeps the local boundary.
        oauth_callback = request.method == "GET" and request.url.path == "/auth/callback"
        origin = request.headers.get("origin")
        if origin and not oauth_callback:
            parsed = urlsplit(origin)
            if parsed.scheme != "http" or parsed.netloc.lower() != host:
                return JSONResponse({"detail": "현재 앱에서 보낸 요청만 허용합니다."}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site" and not oauth_callback:
            return JSONResponse({"detail": "외부 페이지의 요청은 허용하지 않습니다."}, status_code=403)
        try:
            length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "요청 크기가 올바르지 않습니다."}, status_code=400)
        if length > MAX_BACKUP + 1024 * 1024:
            return JSONResponse({"detail": "요청 파일이 너무 큽니다."}, status_code=413)
        if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(request.headers.get("x-csrf-token", ""), token):
            return JSONResponse({"detail": "앱을 새로 불러온 후 다시 시도해주세요."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith("/api") or oauth_callback:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def input_error(request, exc):
        paths = [".".join(str(v) for v in e["loc"]) for e in exc.errors()]
        return JSONResponse({"detail": "입력 항목을 확인해주세요: " + ", ".join(paths)}, status_code=422)

    @app.exception_handler(LookupError)
    async def missing_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValueError)
    async def value_error(request, exc):
        # All application errors are sanitized; never expose submitted values.
        return JSONResponse({"detail": str(exc)}, status_code=409 if isinstance(exc, Conflict) else 400)

    def attempt(pid, callback):
        try:
            return callback()
        except ValueError as exc:
            with store.transaction() as db:
                store.project(db, pid)
                store.audit(db, pid, "failure", pid, result="conflict" if isinstance(exc, Conflict) else "validation-failed")
            raise

    @app.get("/api/health")
    def health():
        return {"app": "toon-studio", "version": APP_VERSION, "mode": "platform_build", "adapter": "mock",
                "orchestrator": "langgraph_sqlite", "studio_schema_version": "2.0.0",
                "character_adapter": studio_router.characters.provider.name}

    @app.get("/auth/callback", include_in_schema=False)
    def chatgpt_callback(request: Request):
        from fastapi.responses import HTMLResponse, RedirectResponse
        try:
            pairs = list(request.query_params.multi_items())
            if len(pairs) != len(dict(pairs)) or len(str(request.url.query)) > 24000:
                raise ChatGPTAuthError("invalid_callback", "로그인 응답을 확인할 수 없습니다. 앱에서 다시 연결해 주세요.")
            auth.complete_login(dict(pairs))
        except ChatGPTAuthError:
            return HTMLResponse("<html lang='ko'><meta charset='utf-8'><title>ChatGPT 연결</title><p>ChatGPT 연결을 완료하지 못했습니다. 앱으로 돌아가 연결 상태를 확인해 주세요.</p><a href='/'>Toon Studio로 돌아가기</a></html>", status_code=400)
        try:
            models = auth.list_models()
            if models and not auth.status().get("model"):
                selected = next((item["slug"] for item in models if item["slug"] == "gpt-6.1-sol"), models[0]["slug"])
                auth.select_model(selected)
        except ChatGPTAuthError:
            # The verified connection is preserved when model discovery is unavailable.
            pass
        return RedirectResponse("/", status_code=303)

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"mode": "platform_build", "csrf_token": token, "schema_version": SCHEMA_VERSION, "projects": studio.projects()}

    @app.get("/api/projects")
    def projects():
        return studio.projects()

    @app.post("/api/projects", status_code=201)
    def create_project(data: ProjectInput):
        return studio.create_project(data.model_dump())

    @app.get("/api/projects/{pid}")
    def project(pid: str):
        return studio.snapshot(pid)

    @app.put("/api/projects/{pid}/setup")
    def setup(pid: str, data: SetupInput):
        return attempt(pid, lambda: studio.save_setup(pid, data.model_dump()))

    @app.post("/api/projects/{pid}/references")
    async def reference(pid: str, file: UploadFile = File(), source: str = Form(), use_basis: str = Form(), not_to_copy: str = Form(""), synthetic: str = Form(), retention_allowed: str = Form("true")):
        if synthetic != "true" or retention_allowed != "true" or not source.strip() or not use_basis.strip():
            raise ValueError("합성 자료의 출처·사용 근거와 프로젝트 복사본 보관 허용을 확인해주세요.")
        data = await file.read(20 * 1024 * 1024 + 1)
        await file.close()
        if not data or len(data) > 20 * 1024 * 1024:
            raise ValueError("레퍼런스 파일은 0바이트보다 크고 20MB 이하여야 합니다.")
        filename = (file.filename or "reference").replace("\\", "/").rsplit("/", 1)[-1][:120]
        return attempt(pid, lambda: studio.import_reference(pid, data, filename, source[:3000], use_basis[:3000], not_to_copy[:3000]))

    @app.post("/api/projects/{pid}/episodes", status_code=201)
    def new_episode(pid: str, data: EpisodeInput):
        return attempt(pid, lambda: studio.create_episode(pid, data.model_dump()))

    @app.get("/api/projects/{pid}/episodes/{cid}")
    def episode(pid: str, cid: str):
        return studio.episode_snapshot(pid, cid)

    @app.post("/api/projects/{pid}/episodes/{cid}/storyboard")
    def storyboard(pid: str, cid: str, data: BoardInput):
        return attempt(pid, lambda: studio.storyboard(pid, cid, data.model_dump()))

    @app.post("/api/projects/{pid}/reviews")
    def review(pid: str, data: ReviewInput):
        return attempt(pid, lambda: studio.review(pid, data.model_dump()))

    @app.post("/api/projects/{pid}/episodes/{cid}/generate")
    def generate(pid: str, cid: str, data: GenerateInput):
        return attempt(pid, lambda: studio.generate(pid, cid, data.model_dump()))

    @app.post("/api/projects/{pid}/episodes/{cid}/selection")
    def selection(pid: str, cid: str, data: SelectionInput):
        return attempt(pid, lambda: studio.select(pid, cid, data.model_dump()))

    @app.get("/api/projects/{pid}/assets/{asset_id}")
    def asset(pid: str, asset_id: str):
        with store.connection() as db:
            record = store.asset(db, pid, asset_id)
            data = store.asset_bytes(record)
        # PDFs are download-only; they cannot execute in the application's origin.
        headers = {"Content-Disposition": f'attachment; filename="{asset_id}.pdf"'} if record["media_type"] == "application/pdf" else {}
        return Response(data, media_type=record["media_type"], headers=headers)

    @app.get("/api/projects/{pid}/history")
    def history(pid: str):
        return studio.snapshot(pid)

    @app.get("/api/passphrase")
    def passphrase():
        phrase = generate_passphrase()
        return {"passphrase": phrase, "strength": evaluate_passphrase(phrase)}

    @app.post("/api/projects/{pid}/backup")
    def backup(pid: str, data: BackupInput):
        def operation():
            with store.transaction() as db:
                snapshot = store.export_snapshot(db, pid)
                assets = [r for r in snapshot["records"] if r["artifact_type"] == "asset_record"]
                if sum(r["byte_size"] for r in assets) > 230 * 1024 * 1024:
                    raise ValueError("이 MVP의 전체 백업 제한은 256MB입니다.")
                payloads = {r["storage_key"]: store.asset_bytes(r) for r in assets}
                filename, archive = pack_project(snapshot, payloads, encrypted=data.encrypted, passphrase=data.passphrase)
                store.audit(db, pid, "export", pid, result="encrypted-backup" if data.encrypted else "plain-backup")
            return Response(archive, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
        return attempt(pid, operation)

    @app.post("/api/projects/{pid}/backup/save")
    def backup_native(pid: str, data: BackupInput):
        def operation():
            with store.transaction() as db:
                snapshot = store.export_snapshot(db, pid)
                assets = [r for r in snapshot["records"] if r["artifact_type"] == "asset_record"]
                if sum(r["byte_size"] for r in assets) > 230 * 1024 * 1024:
                    raise ValueError("이 MVP의 전체 백업 제한은 256MB입니다.")
                payloads = {r["storage_key"]: store.asset_bytes(r) for r in assets}
                filename, archive = pack_project(snapshot, payloads, encrypted=data.encrypted, passphrase=data.passphrase)
            # Release the database writer while the user chooses a destination.
            result = save_backup_file(archive, filename, data.encrypted)
            if result["saved"]:
                with store.transaction() as db:
                    store.audit(db, pid, "export", pid, result="encrypted-backup" if data.encrypted else "plain-backup")
            return result
        return attempt(pid, operation)

    @app.post("/api/restore", status_code=201)
    async def restore(file: UploadFile = File(), passphrase: str | None = Form(None)):
        data = await file.read(MAX_BACKUP + 1)
        await file.close()
        if len(data) > MAX_BACKUP or (passphrase and len(passphrase) > 512):
            raise ValueError("백업 파일 또는 암호문구가 너무 큽니다.")
        snapshot, assets, manifest = unpack_project(data, passphrase=passphrase)
        return studio.restore_snapshot(snapshot, assets, manifest)

    @app.post("/api/shutdown")
    def shutdown():
        callback = getattr(app.state, "shutdown_callback", None)
        if callback:
            callback()
        return {"status": "stopping"}

    frontend = ROOT / "frontend/dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    else:
        @app.get("/")
        def unbuilt():
            return JSONResponse({"detail": "화면 빌드가 필요합니다. 설치 스크립트를 실행해주세요."}, status_code=503)
    return app
