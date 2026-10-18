"""Explicit SIWC public-client OAuth. Credentials stay in protected server-side storage.

Official protocol: developers.openai.com/siwc/token-sharing-open-source/sign-in
No API-key fallback, Codex credential lookup, ambient auth, or browser token storage.
"""
import base64
import copy
import ctypes
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx


ISSUER = "https://auth.openai.com"
AUTHORIZE_URL = ISSUER + "/api/accounts/authorize"
TOKEN_URL = ISSUER + "/api/accounts/oauth/token"
REVOCATION_URL = ISSUER + "/api/accounts/oauth/revoke"
JWKS_URL = ISSUER + "/.well-known/jwks.json"
MODELS_URL = "https://api.openai.com/v1/models"
RESOURCE = "https://api.openai.com/v1"
MANAGE_USAGE_URL = "https://chatgpt.com/settings/usage"
SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
SCHEMA = "toon-chatgpt-auth-v1"
LOGIN_SECONDS = 600
_DPAPI_PREFIX = b"TOON-DPAPI-1\0"
_UNIX_PREFIX = b"TOON-PRIVATE-1\0"
_TERMINAL_REFRESH = {"invalid_grant", "invalid_refresh_token", "token_expired", "refresh_token_expired",
                     "refresh_token_invalidated", "refresh_token_reused"}
_RETRYABLE_LIMITS = {"subscription_sharing_usage_limit_exceeded", "subscription_sharing_usage_unavailable",
                     "subscription_sharing_user_unavailable", "rate_limit_exceeded", "http_429", "insufficient_quota"}
_AUTH_LOSS_CODES = _TERMINAL_REFRESH | {"authentication_required", "subscription_sharing_invalid_user"}
_SAFE_CODES = _TERMINAL_REFRESH | _RETRYABLE_LIMITS | {
    "invalid_client", "access_denied", "subscription_sharing_invalid_user", "subscription_sharing_user_not_eligible",
    "subscription_sharing_unsupported_capability", "subscription_sharing_route_not_supported",
    "chatpass_v2_scope_not_authorized", "chatpass_v2_invalid_authorization_context", "authentication_required",
    "sharing_not_authorized", "inference_blocked", "direct_route_unavailable", "permission_denied"}
_PROCESS_LOCKS = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


class ChatGPTAuthError(ValueError):
    def __init__(self, code, message="ChatGPT 연결을 확인한 후 다시 시도해주세요."):
        super().__init__(message)
        self.code = code


def _dpapi(data: bytes, *, decrypt=False) -> bytes:
    """Windows current-user DPAPI with UI disabled; no plaintext temporary file."""
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), buffer)
    result = Blob()
    if decrypt:
        function = crypt.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        arguments = (ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result))
    else:
        function = crypt.CryptProtectData
        function.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
                             ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        arguments = (ctypes.byref(source), "Toon Studio ChatGPT", None, None, None, 1, ctypes.byref(result))
    function.restype = wintypes.BOOL
    if not function(*arguments):
        raise ChatGPTAuthError("credential_protection_failed", "로그인 정보를 안전하게 저장하거나 읽을 수 없습니다.")
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel.LocalFree(result.pbData)


class ChatGPTAuth:
    def __init__(self, root: Path, *, transport=None):
        self.root = Path(root).resolve() / "private" / "chatgpt"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ChatGPTAuthError("credential_store_invalid")
        if os.name != "nt":
            self.root.chmod(0o700)
        self.path = self.root / "session.bin"
        self.lock_path = self.root / "session.lock"
        self.transport = transport
        with _PROCESS_LOCKS_GUARD:
            self._thread_lock = _PROCESS_LOCKS.setdefault(str(self.path), threading.RLock())
        with self._locked() as record:
            if not self.path.exists():
                self._save(record)

    def close(self):
        pass

    @contextmanager
    def _locked(self):
        with self._thread_lock:
            if self.lock_path.is_symlink():
                raise ChatGPTAuthError("credential_store_invalid")
            flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(self.lock_path, flags, 0o600)
            with os.fdopen(descriptor, "r+b") as lock_file:
                if os.fstat(lock_file.fileno()).st_size == 0:
                    lock_file.write(b"0")
                    lock_file.flush()
                lock_file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield self._load()
                finally:
                    lock_file.seek(0)
                    if os.name == "nt":
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load(self):
        if not self.path.exists():
            return {"schema_id": SCHEMA, "host_id": f"urn:uuid:{uuid.uuid4()}", "registration": None,
                    "credentials": None, "pending": None, "models": [], "selected_model": None,
                    "blocked": None, "last_error": None, "login_epoch": uuid.uuid4().hex, "callback_path": None}
        try:
            if self.path.is_symlink() or self.path.stat().st_size > 1_000_000:
                raise ValueError("invalid credential file")
            if os.name != "nt" and self.path.stat().st_mode & 0o077:
                raise ValueError("credential file permissions")
            raw = self.path.read_bytes()
            if os.name == "nt":
                if not raw.startswith(_DPAPI_PREFIX):
                    raise ValueError("unprotected credential file")
                raw = _dpapi(raw[len(_DPAPI_PREFIX):], decrypt=True)
            else:
                if not raw.startswith(_UNIX_PREFIX):
                    raise ValueError("invalid credential file")
                raw = raw[len(_UNIX_PREFIX):]
            record = json.loads(raw)
            if not isinstance(record, dict) or record.get("schema_id") != SCHEMA:
                raise ValueError("unsupported credential schema")
            if not re.fullmatch(r"urn:uuid:[0-9a-f-]{36}", record["host_id"]):
                raise ValueError("invalid host identity")
            for field in ("registration", "credentials", "pending", "blocked"):
                if record.get(field) is not None and not isinstance(record[field], dict):
                    raise ValueError("invalid credential record")
            return record
        except (OSError, ValueError, TypeError, KeyError, ChatGPTAuthError):
            raise ChatGPTAuthError("credential_store_invalid", "보관된 ChatGPT 연결 정보를 안전하게 읽을 수 없습니다.") from None

    def _save(self, record):
        raw = json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        raw = _DPAPI_PREFIX + _dpapi(raw) if os.name == "nt" else _UNIX_PREFIX + raw
        temporary = self.root / f".session-{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(temporary, flags, 0o600)
            with os.fdopen(descriptor, "wb") as file:
                file.write(raw)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
            if os.name != "nt":
                self.path.chmod(0o600)
        except OSError:
            raise ChatGPTAuthError("credential_store_unavailable", "ChatGPT 연결 정보를 안전하게 저장할 수 없습니다.") from None
        finally:
            temporary.unlink(missing_ok=True)

    def _request(self, method, url, **kwargs):
        if url not in {TOKEN_URL, REVOCATION_URL, JWKS_URL, MODELS_URL}:
            raise ChatGPTAuthError("endpoint_not_allowed")
        try:
            with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, transport=self.transport) as client:
                response = client.request(method, url, **kwargs)
            if len(response.content) > 1_000_000:
                raise ChatGPTAuthError("invalid_provider_response")
            if not 200 <= response.status_code < 300:
                try:
                    body = response.json()
                    error = body.get("error", "") if isinstance(body, dict) else ""
                    code = error.get("code") if isinstance(error, dict) else error
                except ValueError:
                    code = None
                if code not in _SAFE_CODES:
                    code = "authentication_required" if response.status_code == 401 else "auth_request_failed"
                raise ChatGPTAuthError(code)
            if not response.content:
                return {}
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("expected object")
            return value
        except (httpx.HTTPError, ValueError) as error:
            if isinstance(error, ChatGPTAuthError):
                raise
            raise ChatGPTAuthError("auth_connection_unavailable", "ChatGPT 연결을 확인할 수 없습니다. 잠시 후 다시 시도해주세요.") from None

    @staticmethod
    def _sharing(record):
        credentials = record.get("credentials") or {}
        return {"chatgpt.tokens.use.direct", "resource.invoke"}.issubset(credentials.get("scopes", []))

    def status(self):
        with self._locked() as record:
            credentials = record.get("credentials") or {}
            connected = bool(credentials.get("access_token"))
            pending = record.get("pending")
            blocked = record.get("blocked")
            result = {"connected": connected, "sharing": connected and self._sharing(record),
                      "login_pending": bool(pending and pending.get("expires_at", 0) > time.time()),
                      "blocked": bool(blocked), "model": record.get("selected_model"),
                      "models": copy.deepcopy(record.get("models", [])), "manage_usage_url": MANAGE_USAGE_URL}
            registration = record.get("registration") or {}
            result["account_label"] = ("ChatGPT 연결 " + hashlib.sha256(registration["client_id"].encode()).hexdigest()[:8]
                                       if registration.get("subject") else None)
            reason = blocked.get("code") if blocked else record.get("last_error")
            if reason:
                result["reason"] = reason
            return result

    def start_login(self, redirect_uri):
        try:
            parsed = urlsplit(redirect_uri)
            if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password
                    or not parsed.port or parsed.query or parsed.fragment or not parsed.path.startswith("/")
                    or parsed.netloc != f"127.0.0.1:{parsed.port}"):
                raise ValueError("not a loopback callback")
        except (ValueError, TypeError):
            raise ChatGPTAuthError("invalid_callback_uri", "127.0.0.1의 로컬 로그인 콜백이 필요합니다.") from None
        with self._locked() as record:
            if record.get("callback_path") not in (None, parsed.path):
                raise ChatGPTAuthError("invalid_callback_uri", "기존 로그인 콜백 경로를 유지해야 합니다.")
            record["callback_path"] = parsed.path
            registration = record.get("registration") or {}
            client_id = registration.get("client_id") or "dynamic_agent_client"
            verifier = secrets.token_urlsafe(64)
            pending = {"state": secrets.token_urlsafe(32), "nonce": secrets.token_urlsafe(32), "verifier": verifier,
                       "redirect_uri": redirect_uri, "client_id": client_id,
                       "expected_subject": registration.get("subject"), "expires_at": time.time() + LOGIN_SECONDS,
                       "exchange_started": False}
            record["pending"] = pending
            self._save(record)
            query = {"client_id": client_id, "ext_agent_host_id": record["host_id"], "response_type": "code",
                     "redirect_uri": redirect_uri, "scope": SCOPES, "resource": RESOURCE,
                     "state": pending["state"], "nonce": pending["nonce"], "code_challenge_method": "S256",
                     "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()}
            if client_id == "dynamic_agent_client":
                query["agent_name_hint"] = "Toon Studio"
            # ID tokens are deliberately not returned in authorization_url; the optional hint is omitted.
            return {"authorization_url": AUTHORIZE_URL + "?" + urlencode(query), "expires_in": LOGIN_SECONDS}

    def _verify_id_token(self, token, client_id, *, nonce=None, expected_subject=None, refresh=False):
        try:
            import jwt
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise ValueError("unsupported signing algorithm")
            jwks = self._request("GET", JWKS_URL)
            keys = jwks.get("keys")
            if not isinstance(keys, list) or len(keys) > 100:
                raise ValueError("invalid signing keys")
            matches = [key for key in keys if isinstance(key, dict) and key.get("kid") == header["kid"]
                       and key.get("kty") == "RSA" and key.get("use", "sig") == "sig" and key.get("alg", "RS256") == "RS256"]
            if len(matches) != 1:
                raise ValueError("unknown signing key")
            key = jwt.PyJWK.from_dict(matches[0], algorithm="RS256").key
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=client_id, issuer=ISSUER, leeway=15,
                                options={"require": ["sub", "iss", "aud", "exp", "iat"] + ([] if refresh else ["nonce"])})
            if not isinstance(claims["sub"], str) or not claims["sub"]:
                raise ValueError("missing identity")
            if nonce is not None and (not refresh or "nonce" in claims) and (
                    not isinstance(claims.get("nonce"), str) or not hmac.compare_digest(claims["nonce"], nonce)):
                raise ValueError("nonce mismatch")
            if isinstance(claims["aud"], list) and len(claims["aud"]) > 1 and claims.get("azp") != client_id:
                raise ValueError("authorized party mismatch")
            if expected_subject is not None and claims["sub"] != expected_subject:
                raise ValueError("account mismatch")
            return claims
        except ImportError:
            raise ChatGPTAuthError("jwt_verifier_unavailable", "ChatGPT 로그인 서명 검증 구성 요소가 없습니다.") from None
        except ChatGPTAuthError:
            raise
        except Exception:
            raise ChatGPTAuthError("invalid_id_token", "ChatGPT 로그인 서명이나 계정 정보를 확인할 수 없습니다.") from None

    @staticmethod
    def _tokens(data, *, previous=None):
        previous = previous or {}
        access = data.get("access_token")
        refresh = data.get("refresh_token", previous.get("refresh_token"))
        seconds = data.get("expires_in")
        scope = data.get("scope")
        if scope is None and previous:
            scopes = previous["scopes"]
        elif isinstance(scope, str):
            scopes = scope.split()
        else:
            raise ChatGPTAuthError("invalid_token_response")
        if (not isinstance(access, str) or not 1 <= len(access) <= 64000
                or (refresh is not None and (not isinstance(refresh, str) or not 1 <= len(refresh) <= 64000))
                or str(data.get("token_type", "")).lower() != "bearer"
                or type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 31536000):
            raise ChatGPTAuthError("invalid_token_response")
        return {"access_token": access, "refresh_token": refresh, "scopes": scopes,
                "token_type": "Bearer", "expires_at": time.time() + seconds}

    def complete_login(self, query: dict):
        if not isinstance(query, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in query.items()):
            raise ChatGPTAuthError("invalid_oauth_callback")
        with self._locked() as record:
            pending = record.get("pending")
            if (not pending or pending.get("expires_at", 0) <= time.time()
                    or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", query.get("state", ""))
                    or not hmac.compare_digest(query["state"], pending["state"])):
                raise ChatGPTAuthError("invalid_oauth_state", "로그인 요청이 만료됐거나 일치하지 않습니다. 다시 연결해주세요.")
            if pending.get("exchange_started"):
                raise ChatGPTAuthError("oauth_exchange_already_started", "이 로그인 코드는 다시 사용할 수 없습니다. 새로 연결해주세요.")
            if query.get("error"):
                record["pending"], record["last_error"] = None, "consent_declined"
                self._save(record)
                raise ChatGPTAuthError("access_denied", "ChatGPT 연결 동의가 취소됐습니다.")
            if not query.get("code") or len(query["code"]) > 10000:
                raise ChatGPTAuthError("invalid_oauth_callback")
            original_client = pending["client_id"]
            issued = query.get("client_id") or (original_client if original_client != "dynamic_agent_client" else "")
            if (not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", issued) or issued == "dynamic_agent_client"
                    or (original_client != "dynamic_agent_client" and issued != original_client)):
                raise ChatGPTAuthError("invalid_issued_client", "발급된 ChatGPT 앱 정보를 확인할 수 없습니다.")
            # Retain callback-issued client BEFORE code exchange, including an invalid_grant or process exit.
            if not record.get("registration"):
                record["registration"] = {"client_id": issued, "subject": None, "issuer": ISSUER}
            pending.update(client_id=issued, exchange_started=True)
            self._save(record)
            try:
                data = self._request("POST", TOKEN_URL, data={"grant_type": "authorization_code", "client_id": issued,
                    "code": query["code"], "code_verifier": pending["verifier"], "redirect_uri": pending["redirect_uri"], "resource": RESOURCE})
                tokens = self._tokens(data)
                if not isinstance(data.get("id_token"), str):
                    raise ChatGPTAuthError("invalid_id_token")
                claims = self._verify_id_token(data["id_token"], issued, nonce=pending["nonce"], expected_subject=pending["expected_subject"])
            except ChatGPTAuthError:
                record["pending"] = None
                record["last_error"] = "login_failed"
                self._save(record)
                raise
            tokens.update(id_token=data["id_token"], nonce=pending["nonce"])
            record["registration"] = {"client_id": issued, "subject": claims["sub"], "issuer": ISSUER}
            record["credentials"], record["pending"], record["last_error"] = tokens, None, None
            record["login_epoch"] = uuid.uuid4().hex
            record["models"] = []
            record["selected_model"] = None
            if record.get("blocked") and record["blocked"]["code"] in _AUTH_LOSS_CODES:
                record["blocked"] = None
            self._save(record)

    def _access_token(self, record):
        if record.get("blocked"):
            raise ChatGPTAuthError(record["blocked"]["code"], "ChatGPT 사용이 일시 중지됐습니다. 상태를 확인한 후 직접 재개해주세요.")
        credentials = record.get("credentials")
        if not credentials:
            raise ChatGPTAuthError("authentication_required", "ChatGPT 계정을 먼저 연결해주세요.")
        if not self._sharing(record):
            raise ChatGPTAuthError("sharing_not_authorized", "ChatGPT 구독 사용 동의가 필요합니다.")
        if credentials["expires_at"] > time.time() + 30:
            return credentials["access_token"]
        if not credentials.get("refresh_token"):
            record["credentials"] = None
            record["last_error"] = "authentication_required"
            self._save(record)
            raise ChatGPTAuthError("authentication_required")
        try:
            registration = record["registration"]
            data = self._request("POST", TOKEN_URL, data={"grant_type": "refresh_token", "client_id": registration["client_id"],
                                     "refresh_token": credentials["refresh_token"], "resource": RESOURCE})
            updated = self._tokens(data, previous=credentials)
            updated.update(id_token=credentials.get("id_token"), nonce=credentials.get("nonce"))
            if "id_token" in data:
                self._verify_id_token(data["id_token"], registration["client_id"], nonce=credentials.get("nonce"),
                                      expected_subject=registration["subject"], refresh=True)
                updated["id_token"] = data["id_token"]
        except ChatGPTAuthError as error:
            if error.code in _TERMINAL_REFRESH or error.code == "invalid_id_token":
                record["credentials"] = None
                record["models"] = []
                record["last_error"] = "authentication_required"
                self._save(record)
            raise
        record["credentials"] = updated
        self._save(record)  # rotating refresh token, access, scopes and expiry replace atomically.
        if not self._sharing(record):
            raise ChatGPTAuthError("sharing_not_authorized")
        return updated["access_token"]

    def access_token(self):
        with self._locked() as record:
            return self._access_token(record)

    def list_models(self):
        with self._locked() as record:
            token = self._access_token(record)
            try:
                data = self._request("GET", MODELS_URL, headers={"Authorization": f"Bearer {token}"})
            except ChatGPTAuthError as error:
                if error.code in _AUTH_LOSS_CODES:
                    record["blocked"] = {"code": error.code, "at": time.time()}
                    self._save(record)
                raise
            models = data.get("models")
            if not isinstance(models, list) or len(models) > 1000:
                raise ChatGPTAuthError("invalid_model_catalog")
            result = []
            seen = set()
            for model in models:
                if not isinstance(model, dict) or model.get("visibility") != "list":
                    continue
                slug, name = model.get("slug"), model.get("display_name")
                if (not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", slug)
                        or not isinstance(name, str) or not 1 <= len(name) <= 200 or slug in seen):
                    raise ChatGPTAuthError("invalid_model_catalog")
                seen.add(slug)
                result.append({"slug": slug, "display_name": name})
            record["models"] = result
            if record.get("selected_model") not in seen:
                record["selected_model"] = None
            self._save(record)
            return copy.deepcopy(result)

    def select_model(self, slug):
        with self._locked() as record:
            if not isinstance(slug, str) or slug not in [item["slug"] for item in record.get("models", [])]:
                raise ChatGPTAuthError("model_not_available", "현재 연결한 계정의 모델 목록에서 선택해주세요.")
            if not record.get("credentials") or not self._sharing(record):
                raise ChatGPTAuthError("sharing_not_authorized")
            record["selected_model"] = slug
            self._save(record)

    def get_selected_model(self):
        with self._locked() as record:
            model = record.get("selected_model")
            if not model or model not in [item["slug"] for item in record.get("models", [])]:
                raise ChatGPTAuthError("model_not_selected", "연결한 계정에서 사용할 모델을 선택해주세요.")
            return model

    @staticmethod
    def _identity(record):
        registration = record.get("registration") or {}
        value = [registration.get("subject"), registration.get("client_id"), record.get("selected_model"), record.get("login_epoch")]
        return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()

    def identity_key(self):
        with self._locked() as record:
            return self._identity(record)

    def inference_snapshot(self):
        """Server-only atomic snapshot. NEVER return this object through an HTTP/UI route."""
        with self._locked() as record:
            token = self._access_token(record)
            model = record.get("selected_model")
            if not model or model not in [item["slug"] for item in record.get("models", [])]:
                raise ChatGPTAuthError("model_not_selected", "사용할 모델을 먼저 선택해주세요.")
            return {"access_token": token, "model": model, "identity_key": self._identity(record)}

    def stop_for_limit(self, code):
        with self._locked() as record:
            record["blocked"] = {"code": code if code in _SAFE_CODES else "inference_blocked", "at": time.time()}
            self._save(record)

    def resume_after_limit(self):
        """Only an explicit human retry action may call this; no automatic timer resets."""
        with self._locked() as record:
            if record.get("blocked") and record["blocked"]["code"] not in _RETRYABLE_LIMITS:
                raise ChatGPTAuthError("connection_action_required", "연결 상태와 사용 권한을 먼저 확인해주세요.")
            record["blocked"] = None
            self._save(record)

    def disconnect(self):
        with self._locked() as record:
            credentials = record.get("credentials") or {}
            registration = record.get("registration") or {}
            remote_confirmed = True
            if credentials.get("refresh_token"):
                try:
                    self._request("POST", REVOCATION_URL, data={"token": credentials["refresh_token"],
                                  "token_type_hint": "refresh_token", "client_id": registration["client_id"]})
                except ChatGPTAuthError:
                    remote_confirmed = False
            record.update(credentials=None, pending=None, models=[], selected_model=None, login_epoch=uuid.uuid4().hex,
                          last_error=None if remote_confirmed else "remote_revocation_unconfirmed")
            self._save(record)
