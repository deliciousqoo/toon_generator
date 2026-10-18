"""Subscription-only app integration and the narrow OAuth callback boundary."""
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.chatgpt_auth import ChatGPTAuthError


class FakeAuth:
    def __init__(self):
        self.connected = False
        self.model = ""
        self.resumed = 0

    def status(self):
        return {"connected": self.connected, "sharing": self.connected, "login_pending": False,
                "blocked": False, "model": self.model, "models": [],
                "manage_usage_url": "https://chatgpt.com/settings/usage"}

    def start_login(self, redirect):
        self.redirect = redirect
        return {"authorization_url": "https://auth.openai.com/api/accounts/authorize?state=test", "expires_in": 600}

    def complete_login(self, query):
        if query.get("state") != "test":
            raise ChatGPTAuthError("invalid_state", "로그인 확인에 실패했습니다.")
        self.connected = True

    def list_models(self):
        return [{"slug": "gpt-6.1-sol", "display_name": "GPT-6.1 Sol"}]

    def select_model(self, model):
        self.model = model

    def resume_after_limit(self):
        self.resumed += 1

    def disconnect(self):
        self.connected = False

    def identity_key(self):
        return "fake-account-model"

    def inference_snapshot(self):
        raise ChatGPTAuthError("not_connected", "ChatGPT를 먼저 연결해 주세요.")

    def close(self):
        pass


def client_for(app):
    return TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))


def test_oauth_callback_is_the_only_cross_site_exception(tmp_path):
    auth = FakeAuth()
    with client_for(create_app(tmp_path, chatgpt_auth=auth)) as client:
        token = client.get("/api/bootstrap").json()["csrf_token"]
        path = "/api/studio/chatgpt"
        assert client.post(path + "/login").status_code == 403
        csrf = {"x-csrf-token": token}
        result = client.post(path + "/login", headers=csrf)
        assert result.status_code == 200
        assert auth.redirect == "http://127.0.0.1:8765/auth/callback"
        cross_site = {**csrf, "sec-fetch-site": "cross-site", "origin": "https://auth.openai.com"}
        assert client.post(path + "/login", headers=cross_site).status_code == 403
        assert client.get(path, headers=cross_site).status_code == 403
        assert client.post("/auth/callback", headers=cross_site).status_code == 403
        rejected = client.get("/auth/callback?state=wrong&code=never-print-this", headers=cross_site)
        assert rejected.status_code == 400
        assert "never-print-this" not in rejected.text
        assert rejected.headers["cache-control"] == "no-store"
        assert client.get("/auth/callback?state=test&state=other", headers=cross_site).status_code == 400
        result = client.get("/auth/callback?state=test&code=secret", headers=cross_site, follow_redirects=False)
        assert result.status_code == 303 and result.headers["location"] == "/"
        assert auth.model == "gpt-6.1-sol"
        current = client.get(path).json()
        assert current["connected"] and current["sharing"]
        assert not current["paid_api_fallback"] and not current["fixture"]
        assert client.post(path + "/resume", headers=csrf).status_code == 200
        assert auth.resumed == 1
        assert client.post(path + "/disconnect", headers=csrf).status_code == 200
        assert not client.get(path).json()["connected"]


def test_default_character_provider_never_falls_back_to_fixture_or_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    auth = FakeAuth()
    with client_for(create_app(tmp_path, chatgpt_auth=auth)) as client:
        assert client.app.state.character_studio.provider.name == "chatgpt_subscription"
        headers = {"x-csrf-token": client.get("/api/bootstrap").json()["csrf_token"]}
        project = client.post("/api/studio/character-projects", json={"synthetic_confirmed": True}, headers=headers).json()
        path = f"/api/studio/projects/{project['id']}/character"
        before = client.get(path).json()
        assert not before["fixture"]
        response = client.post(path + "/turns", json={"request_id": "not-connected", "expected_revision": 0,
                    "message": "가상의 검증용 캐릭터", "synthetic_confirmed": True}, headers=headers)
        assert response.status_code == 200
        state = response.json()
        assert state["status"] == "blocked" and state["brief"] is None
        assert state["provider"] == "chatgpt_subscription" and not state["fixture"]
        assert state["messages"][0]["content"] == "가상의 검증용 캐릭터"
