"""Local, CSRF-protected controls for this application's own ChatGPT connection."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .chatgpt_auth import ChatGPTAuthError


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=200)


def create_chatgpt_router(auth, *, port: int, fixture: bool):
    router = APIRouter(prefix="/api/studio/chatgpt")

    def call(method, *args):
        try:
            return method(*args)
        except ChatGPTAuthError as error:
            status = 429 if error.code in ("subscription_limit", "subscription_sharing_usage_limit_exceeded") else 409
            raise HTTPException(status, str(error)) from None

    def current():
        return {**auth.status(), "fixture": fixture, "paid_api_fallback": False}

    @router.get("")
    def status():
        return current()

    @router.post("/login")
    def login():
        return call(auth.start_login, f"http://127.0.0.1:{port}/auth/callback")

    @router.get("/models")
    def models():
        return {"models": call(auth.list_models)}

    @router.post("/model")
    def model(choice: ModelChoice):
        call(auth.select_model, choice.model)
        return current()

    @router.post("/resume")
    def resume():
        call(auth.resume_after_limit)
        return current()

    @router.post("/disconnect")
    def disconnect():
        call(auth.disconnect)
        return current()

    return router
