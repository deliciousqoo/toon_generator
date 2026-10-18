"""SIWC OAuth tests use signed synthetic JWTs and HTTPX MockTransport only."""
import base64
import copy
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.chatgpt_auth import (AUTHORIZE_URL, ISSUER, JWKS_URL, MANAGE_USAGE_URL, MODELS_URL,
                                 RESOURCE, REVOCATION_URL, SCOPES, TOKEN_URL, ChatGPTAuth, ChatGPTAuthError)


class MockOpenAI:
    def __init__(self):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.jwk = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.key.public_key())), "kid": "synthetic-key", "use": "sig", "alg": "RS256"}
        self.auth = None
        self.nonce = ""
        self.client = "oaiapp_synthetic_client"
        self.subject = "synthetic-subject"
        self.claim_overrides = {}
        self.scope = SCOPES
        self.token_error = None
        self.refresh_error = None
        self.refreshes = 0
        self.calls = []
        self.models_error = None
        self.models = [{"slug": "synthetic-model", "display_name": "합성 모델", "visibility": "list"},
                       {"slug": "hidden", "display_name": "hidden", "visibility": "hide"}]
        self.revoke_error = None
        self.transport = httpx.MockTransport(self.handle)

    def id_token(self):
        claims = {"iss": ISSUER, "aud": self.client, "sub": self.subject, "nonce": self.nonce,
                  "exp": int(time.time()) + 3600, "iat": int(time.time()), **self.claim_overrides}
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "synthetic-key"})

    def handle(self, request):
        self.calls.append((request.method, str(request.url)))
        if str(request.url) == JWKS_URL:
            return httpx.Response(200, json={"keys": [self.jwk]})
        if str(request.url) == TOKEN_URL:
            values = {key: value[0] for key, value in parse_qs(request.content.decode()).items()}
            assert values["client_id"] == self.client
            assert values["resource"] == RESOURCE and "client_secret" not in values
            if values["grant_type"] == "authorization_code":
                # The issued client is already durably saved when code exchange starts.
                stored = self.auth._load()
                assert stored["registration"]["client_id"] == self.client
                assert stored["pending"]["exchange_started"]
                assert values["redirect_uri"] == stored["pending"]["redirect_uri"]
                assert values["code_verifier"] == stored["pending"]["verifier"]
                if self.token_error:
                    return httpx.Response(400, json={"error": self.token_error, "error_description": "must never leak"})
                return httpx.Response(200, json={"access_token": "synthetic-access-1", "refresh_token": "synthetic-refresh-1",
                    "id_token": self.id_token(), "expires_in": 3600, "token_type": "Bearer", "scope": self.scope})
            assert values["grant_type"] == "refresh_token" and "scope" not in values
            self.refreshes += 1
            if self.refresh_error:
                return httpx.Response(self.refresh_error[0], json={"error": self.refresh_error[1]})
            assert values["refresh_token"] == "synthetic-refresh-1"
            return httpx.Response(200, json={"access_token": "synthetic-access-2", "refresh_token": "synthetic-refresh-2",
                "expires_in": 3600, "token_type": "Bearer"})
        if str(request.url) == MODELS_URL:
            assert request.headers["Authorization"].startswith("Bearer synthetic-access-")
            if self.models_error:
                return httpx.Response(self.models_error, json={"detail": "must never leak"})
            return httpx.Response(200, json={"models": self.models})
        if str(request.url) == REVOCATION_URL:
            if self.revoke_error:
                raise httpx.ConnectError("must never leak", request=request)
            return httpx.Response(200)
        raise AssertionError("unexpected request destination")


@pytest.fixture
def setup_auth(tmp_path):
    server = MockOpenAI()
    auth = ChatGPTAuth(tmp_path, transport=server.transport)
    server.auth = auth
    return auth, server


def login(auth, server, *, port=8877):
    begun = auth.start_login(f"http://127.0.0.1:{port}/auth/callback")
    parts = urlsplit(begun["authorization_url"])
    query = {key: value[0] for key, value in parse_qs(parts.query).items()}
    server.nonce = query["nonce"]
    auth.complete_login({"state": query["state"], "code": "synthetic-code", "client_id": server.client})
    return query


def expire(auth):
    with auth._locked() as record:
        record["credentials"]["expires_at"] = 0
        auth._save(record)


def test_initial_dynamic_registration_pkce_state_and_redacted_status(setup_auth):
    auth, server = setup_auth
    initial = auth.status()
    assert not initial["connected"] and server.calls == []
    query = login(auth, server)
    assert query["client_id"] == "dynamic_agent_client" and query["agent_name_hint"] == "Toon Studio"
    assert query["ext_agent_host_id"].startswith("urn:uuid:")
    assert query["scope"] == SCOPES and query["code_challenge_method"] == "S256"
    assert "id_token_hint" not in query and "client_secret" not in query
    stored = auth._load()
    # Derive verifier from the exchange test's persisted pending record in a separate start.
    fresh = auth.start_login("http://127.0.0.1:8877/auth/callback")
    pending = auth._load()["pending"]
    expected_challenge = base64.urlsafe_b64encode(hashlib.sha256(pending["verifier"].encode()).digest()).rstrip(b"=").decode()
    fresh_query = parse_qs(urlsplit(fresh["authorization_url"]).query)
    assert fresh_query["code_challenge"] == [expected_challenge]
    status = auth.status()
    assert status["connected"] and status["sharing"] and status["login_pending"]
    serialized = json.dumps(status)
    for secret in (stored["credentials"]["access_token"], stored["credentials"]["refresh_token"], stored["credentials"]["id_token"], server.subject):
        assert secret not in serialized and secret not in fresh["authorization_url"]
    assert status["manage_usage_url"] == MANAGE_USAGE_URL
    assert status["account_label"].startswith("ChatGPT 연결 ") and server.subject not in status["account_label"]
    raw = auth.path.read_bytes()
    if os.name == "nt":
        assert b"synthetic-access-1" not in raw and b"synthetic-refresh-1" not in raw
    else:
        assert auth.path.stat().st_mode & 0o077 == 0


def test_callback_state_expiry_and_declined_consent_do_not_exchange(setup_auth):
    auth, server = setup_auth
    query = parse_qs(urlsplit(auth.start_login("http://127.0.0.1:8877/auth/callback")["authorization_url"]).query)
    with pytest.raises(ChatGPTAuthError) as error:
        auth.complete_login({"state": "not-the-pending-state", "code": "synthetic-code", "client_id": server.client})
    assert error.value.code == "invalid_oauth_state" and server.calls == []
    with pytest.raises(ChatGPTAuthError) as error:
        auth.complete_login({"state": "일치하지 않는 상태", "code": "synthetic-code", "client_id": server.client})
    assert error.value.code == "invalid_oauth_state" and server.calls == []
    with pytest.raises(ChatGPTAuthError) as error:
        auth.complete_login({"state": query["state"][0], "error": "access_denied"})
    assert error.value.code == "access_denied" and not auth.status()["login_pending"]
    assert server.calls == []
    auth.start_login("http://127.0.0.1:8877/auth/callback")
    with auth._locked() as record:
        original_state = record["pending"]["state"]
        record["pending"]["expires_at"] = 0
        auth._save(record)
    with pytest.raises(ChatGPTAuthError):
        auth.complete_login({"state": original_state, "code": "synthetic-code", "client_id": server.client})
    assert server.calls == []


@pytest.mark.parametrize("override", [{"iss": "https://untrusted.example"}, {"aud": "another-client"},
                                    {"exp": 1}, {"nonce": "different-nonce"}, {"sub": ""},
                                    {"aud": ["oaiapp_synthetic_client", "other"], "azp": "other"}])
def test_identity_signature_claims_fail_closed(setup_auth, override):
    auth, server = setup_auth
    server.claim_overrides = override
    with pytest.raises(ChatGPTAuthError) as error:
        login(auth, server)
    assert error.value.code == "invalid_id_token"
    assert not auth.status()["connected"]
    assert auth._load()["registration"]["client_id"] == server.client
    assert "must never leak" not in str(error.value)


def test_wrong_signature_and_algorithm_are_rejected(setup_auth):
    auth, server = setup_auth
    original = server.id_token
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server.id_token = lambda: jwt.encode(jwt.decode(original(), options={"verify_signature": False}), wrong_key,
                                       algorithm="RS256", headers={"kid": "synthetic-key"})
    with pytest.raises(ChatGPTAuthError) as error:
        login(auth, server)
    assert error.value.code == "invalid_id_token"
    server.id_token = lambda: jwt.encode({"sub": "synthetic"}, "synthetic-secret-long-enough-for-hs256", algorithm="HS256", headers={"kid": "synthetic-key"})
    with pytest.raises(ChatGPTAuthError):
        login(auth, server)
    assert not auth.status()["connected"]


def test_failed_exchange_keeps_issued_client_and_host_for_new_attempt(setup_auth):
    auth, server = setup_auth
    server.token_error = "invalid_grant"
    with pytest.raises(ChatGPTAuthError) as error:
        login(auth, server)
    assert error.value.code == "invalid_grant"
    before = auth._load()
    assert before["registration"]["client_id"] == server.client and before["pending"] is None
    reopened = ChatGPTAuth(auth.root.parent.parent, transport=server.transport)
    query = parse_qs(urlsplit(reopened.start_login("http://127.0.0.1:9988/auth/callback")["authorization_url"]).query)
    assert query["client_id"] == [server.client]
    assert query["ext_agent_host_id"] == [before["host_id"]]
    assert "agent_name_hint" not in query and "id_token_hint" not in query


def test_returning_account_and_client_cannot_be_replaced(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    before = copy.deepcopy(auth._load()["credentials"])
    query = parse_qs(urlsplit(auth.start_login("http://127.0.0.1:9988/auth/callback")["authorization_url"]).query)
    count = len(server.calls)
    with pytest.raises(ChatGPTAuthError) as error:
        auth.complete_login({"state": query["state"][0], "code": "synthetic-code", "client_id": "oaiapp_different"})
    assert error.value.code == "invalid_issued_client" and len(server.calls) == count
    server.subject = "different-synthetic-account"
    with pytest.raises(ChatGPTAuthError) as error:
        login(auth, server)
    assert error.value.code == "invalid_id_token"
    assert auth._load()["credentials"] == before


def test_valid_identity_without_granted_direct_scope_never_infers(setup_auth):
    auth, server = setup_auth
    server.scope = "openid email profile offline_access"
    login(auth, server)
    assert auth.status()["connected"] and not auth.status()["sharing"]
    count = len(server.calls)
    with pytest.raises(ChatGPTAuthError) as error:
        auth.access_token()
    assert error.value.code == "sharing_not_authorized" and len(server.calls) == count


def test_models_are_account_specific_visible_ordered_and_explicitly_selected(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    assert auth.list_models() == [{"slug": "synthetic-model", "display_name": "합성 모델"}]
    with pytest.raises(ChatGPTAuthError):
        auth.get_selected_model()
    with pytest.raises(ChatGPTAuthError):
        auth.select_model("hidden")
    auth.select_model("synthetic-model")
    snapshot = auth.inference_snapshot()
    assert snapshot["access_token"] == "synthetic-access-1"
    assert snapshot["model"] == "synthetic-model" and snapshot["identity_key"] == auth.identity_key()
    assert server.subject not in auth.identity_key()
    server.models = [{"slug": "new-model", "display_name": "새 합성 모델", "visibility": "list"}]
    auth.list_models()
    with pytest.raises(ChatGPTAuthError):
        auth.inference_snapshot()
    auth.select_model("new-model")
    assert auth.identity_key() != snapshot["identity_key"]


def test_verified_reauthentication_clears_catalog_and_old_model_selection_together(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    auth.list_models()
    auth.select_model("synthetic-model")
    before = auth.identity_key()
    login(auth, server)
    assert auth.status()["connected"] and auth.status()["models"] == []
    assert auth.status()["model"] is None and auth.identity_key() != before
    server.models_error = 503
    with pytest.raises(ChatGPTAuthError):
        auth.list_models()
    with pytest.raises(ChatGPTAuthError) as error:
        auth.inference_snapshot()
    assert error.value.code == "model_not_selected"


def test_serialized_refresh_rotates_credentials_atomically_across_instances(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    auth.list_models()
    auth.select_model("synthetic-model")
    identity = auth.identity_key()
    expire(auth)
    second = ChatGPTAuth(auth.root.parent.parent, transport=server.transport)
    barrier = threading.Barrier(2)

    def get_token(engine):
        barrier.wait()
        return engine.access_token()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(get_token, engine) for engine in (auth, second)]
        assert [future.result() for future in futures] == ["synthetic-access-2", "synthetic-access-2"]
    assert server.refreshes == 1
    credentials = second._load()["credentials"]
    assert credentials["refresh_token"] == "synthetic-refresh-2"
    assert credentials["access_token"] == "synthetic-access-2" and credentials["expires_at"] > time.time()
    assert auth.identity_key() == identity


def test_terminal_refresh_clears_only_invalid_tokens_and_retains_registration(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    expire(auth)
    server.refresh_error = (400, "invalid_grant")
    with pytest.raises(ChatGPTAuthError) as error:
        auth.access_token()
    assert error.value.code == "invalid_grant" and not auth.status()["connected"]
    assert auth._load()["registration"]["client_id"] == server.client
    count = len(server.calls)
    with pytest.raises(ChatGPTAuthError):
        auth.access_token()
    assert len(server.calls) == count


def test_temporary_refresh_failure_preserves_credentials_without_fallback(setup_auth, monkeypatch):
    auth, server = setup_auth
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    login(auth, server)
    expire(auth)
    before = copy.deepcopy(auth._load()["credentials"])
    server.refresh_error = (503, "temporary_infrastructure_failure")
    with pytest.raises(ChatGPTAuthError):
        auth.access_token()
    assert auth._load()["credentials"] == before
    assert auth.status()["connected"]


def test_limit_latch_survives_restart_relogin_and_only_explicit_retry_clears(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    auth.stop_for_limit("subscription_sharing_usage_limit_exceeded")
    count = len(server.calls)
    resumed = ChatGPTAuth(auth.root.parent.parent, transport=server.transport)
    assert resumed.status()["blocked"] and resumed.status()["reason"] == "subscription_sharing_usage_limit_exceeded"
    with pytest.raises(ChatGPTAuthError):
        resumed.access_token()
    assert len(server.calls) == count
    login(auth, server)
    assert auth.status()["blocked"]
    auth.resume_after_limit()
    assert not auth.status()["blocked"] and auth.access_token() == "synthetic-access-1"


@pytest.mark.parametrize("code", ["http_429", "insufficient_quota", "subscription_sharing_usage_unavailable",
                                 "subscription_sharing_user_unavailable", "rate_limit_exceeded"])
def test_each_usage_latch_keeps_exact_code_across_reauthentication(setup_auth, code):
    auth, server = setup_auth
    login(auth, server)
    label = auth.status()["account_label"]
    auth.stop_for_limit(code)
    login(auth, server)
    assert auth.status()["blocked"] and auth.status()["reason"] == code
    assert auth.status()["account_label"] == label
    with pytest.raises(ChatGPTAuthError) as error:
        auth.access_token()
    assert error.value.code == code
    auth.resume_after_limit()
    assert auth.access_token() == "synthetic-access-1"


def test_catalog_auth_loss_stops_further_token_use_until_verified_login(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    auth.list_models()
    auth.select_model("synthetic-model")
    server.models_error = 401
    with pytest.raises(ChatGPTAuthError) as error:
        auth.list_models()
    assert error.value.code == "authentication_required"
    assert auth.status()["blocked"] and auth.status()["reason"] == "authentication_required"
    count = len(server.calls)
    with pytest.raises(ChatGPTAuthError):
        auth.inference_snapshot()
    with pytest.raises(ChatGPTAuthError):
        auth.resume_after_limit()
    assert len(server.calls) == count
    login(auth, server)
    assert not auth.status()["blocked"] and auth.access_token() == "synthetic-access-1"


def test_disconnect_revokes_and_retains_registration_for_reauthentication(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    before = auth._load()
    auth.disconnect()
    assert not auth.status()["connected"] and ("POST", REVOCATION_URL) in server.calls
    after = auth._load()
    assert after["registration"] == before["registration"] and after["host_id"] == before["host_id"]
    assert after["credentials"] is None and after["pending"] is None
    query = parse_qs(urlsplit(auth.start_login("http://127.0.0.1:8877/auth/callback")["authorization_url"]).query)
    assert query["client_id"] == [server.client] and "id_token_hint" not in query


def test_failed_remote_revocation_still_stops_locally_and_reports_safe_reason(setup_auth):
    auth, server = setup_auth
    login(auth, server)
    server.revoke_error = True
    auth.disconnect()
    assert not auth.status()["connected"] and auth.status()["reason"] == "remote_revocation_unconfirmed"
    with pytest.raises(ChatGPTAuthError):
        auth.access_token()


@pytest.mark.parametrize("redirect", ["http://localhost:8877/auth/callback", "https://127.0.0.1:8877/auth/callback",
                                     "http://127.0.0.1.evil.example:8877/auth/callback", "http://user@127.0.0.1:8877/auth/callback",
                                     "http://127.0.0.1:8877/auth/callback?token=x", "http://127.0.0.1/auth/callback"])
def test_only_exact_loopback_callback_is_allowed(setup_auth, redirect):
    auth, server = setup_auth
    with pytest.raises(ChatGPTAuthError):
        auth.start_login(redirect)
    assert server.calls == []


def test_callback_path_remains_bound_and_corrupt_store_is_not_overwritten(setup_auth):
    auth, server = setup_auth
    auth.start_login("http://127.0.0.1:8877/auth/callback")
    with pytest.raises(ChatGPTAuthError):
        auth.start_login("http://127.0.0.1:8877/different/callback")
    auth.path.write_bytes(b"invalid-unprotected-synthetic-data")
    with pytest.raises(ChatGPTAuthError) as error:
        ChatGPTAuth(auth.root.parent.parent, transport=server.transport)
    assert error.value.code == "credential_store_invalid"
    assert auth.path.read_bytes() == b"invalid-unprotected-synthetic-data"
