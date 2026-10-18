"""Additive episode endpoints; no fixture run semantics are changed."""
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .character_visuals import MAX_IMAGE_BYTES, VisualConflict
from .character_service import CharacterNotFound
from .episode_contracts import CreateEpisodeRequest, DecisionRequest, FormatRequest, Request, RoughJobRequest, TurnRequest
from .episode_service import EpisodeConflict, EpisodeService


def create_episode_router(root, characters):
    service = EpisodeService(root, characters)
    router = APIRouter(prefix="/api/studio/projects/{pid}/episodes")
    router.service = service

    def call(method, *args):
        try:
            return method(*args)
        except (KeyError, CharacterNotFound):
            raise HTTPException(404, "현재 프로젝트의 이야기를 찾을 수 없습니다.") from None
        except (EpisodeConflict, VisualConflict) as error:
            raise HTTPException(409, str(error)) from None
        except ValueError:
            raise HTTPException(409, "저장된 이야기나 입력 계약을 확인하지 못했습니다. 이전 결과는 보존했습니다.") from None

    @router.get("")
    def episodes(pid: str):
        return {"episodes": call(service.list_episodes, pid)}

    @router.post("", status_code=201)
    def create(pid: str, request: CreateEpisodeRequest):
        return call(service.create_episode, pid, request.model_dump())

    @router.get("/{eid}")
    def state(pid: str, eid: str):
        return call(service.get_state, pid, eid)

    @router.post("/{eid}/turns")
    def turn(pid: str, eid: str, request: TurnRequest):
        return call(service.submit_turn, pid, eid, request.model_dump())

    @router.post("/{eid}/decisions")
    def decision(pid: str, eid: str, request: DecisionRequest):
        return call(service.decision, pid, eid, request.model_dump())

    @router.post("/{eid}/format")
    def format_choice(pid: str, eid: str, request: FormatRequest):
        return call(service.save_format, pid, eid, request.model_dump())

    @router.post("/{eid}/rough/jobs")
    def rough_job(pid: str, eid: str, request: RoughJobRequest):
        return call(service.create_rough_job, pid, eid, request.model_dump())

    @router.post("/{eid}/rough/jobs/{jid}/cancel")
    def rough_cancel(pid: str, eid: str, jid: str, request: Request):
        return call(service.cancel_rough_job, pid, eid, jid, request.model_dump())

    @router.post("/{eid}/rough/jobs/{jid}/image")
    async def rough_image(pid: str, eid: str, jid: str, request: str = Form(...), file: UploadFile = File(...)):
        try:
            if len(request) > 32000:
                raise ValueError("metadata too large")
            metadata = json.loads(request)
            data = await file.read(MAX_IMAGE_BYTES + 1)
        except (ValueError, TypeError):
            raise HTTPException(422, "이미지 출처와 현재 콘티 버전을 확인해 주세요.") from None
        finally:
            await file.close()
        return call(service.upload_rough, pid, eid, jid, metadata, data)

    @router.get("/{eid}/rough/assets/{aid}")
    def asset(pid: str, eid: str, aid: str):
        return Response(call(service.rough_asset_bytes, pid, eid, aid), media_type="image/png")

    @router.get("/{eid}/export")
    def export(pid: str, eid: str):
        return Response(call(service.export_episode, pid, eid), media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="episode-storyboard.zip"'})

    return router
