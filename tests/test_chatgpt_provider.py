"""The subscription inference adapter is exercised with mock HTTP only."""
import asyncio
import json
import time

import httpx
import pytest

from backend.character_contracts import DirectionFields
from backend.chatgpt_auth import ChatGPTAuthError
from backend.chatgpt_provider import (MAX_BODY_BYTES, RESPONSES_URL, ChatGPTCharacterProvider,
                                      ChatGPTProviderError, ChatGPTUsageStopped)


class FakeAuth:
    def __init__(self):
        self.identity = "synthetic-account-client-model-login"
        self.model = "selected-account-model"
        self.stop_code = None
        self.snapshots = 0

    def identity_key(self):
        return self.identity

    def inference_snapshot(self):
        self.snapshots += 1
        if self.stop_code:
            raise ChatGPTUsageStopped(self.stop_code, "구독 호출이 중지되어 있습니다.")
        return {"identity_key": self.identity, "model": self.model, "access_token": "synthetic-oauth-token"}

    def stop_for_limit(self, code):
        self.stop_code = code


def context(**updates):
    return {"project_id": "project-test", "version": "1.0.1", "message": "가상의 외형 특징",
            "previous_fields": DirectionFields().model_dump(), "question_field": "appearance",
            "field_updates": {}, "references": [], "dialogue": [], **updates}


def draft_payload(**updates):
    return {"fields": DirectionFields(appearance="가상의 외형 특징").model_dump(),
            "assistant_message": "외형을 정리했습니다. 성격은 어떤가요?", **updates}


def event(data):
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


def completed(payload, *, delta=True):
    text = json.dumps(payload, ensure_ascii=False)
    prefix = event({"type": "response.output_text.delta", "delta": text}) if delta else ""
    return prefix + event({"type": "response.completed", "response": {
        "status": "completed", "output": [{"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": text}]}]}})


def finalized_events(payload):
    text = json.dumps(payload, ensure_ascii=False)
    source = {"output_index": 0, "content_index": 0, "item_id": "synthetic-item"}
    return [
        {"type": "response.output_text.delta", **source, "delta": text[:20]},
        {"type": "response.output_text.delta", **source, "delta": text[20:]},
        {"type": "response.output_text.done", **source, "text": text},
        {"type": "response.output_item.done", "output_index": 0, "item": {
            "id": "synthetic-item", "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text}]}},
        {"type": "response.completed", "response": {"status": "completed", "output": []}},
    ]


def stream_events(events):
    return "".join(event(item) for item in events)


def adapter(body, *, status=200, auth=None, headers=None, inspect=None):
    calls = []

    def handle(request):
        calls.append(request)
        if inspect:
            inspect(request)
        return httpx.Response(status, content=body, headers={"content-type": "text/event-stream"} if headers is None else headers)

    identity = auth or FakeAuth()
    return ChatGPTCharacterProvider(identity, transport=httpx.MockTransport(handle)), identity, calls


def test_subscription_request_uses_only_selected_oauth_and_supported_fields(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://must-not-be-used.invalid")
    provider, auth, calls = adapter(completed(draft_payload()))
    result = provider.draft(context(_execution_identity=auth.identity_key()))
    assert result == draft_payload()
    assert len(calls) == 1
    request = calls[0]
    assert str(request.url) == RESPONSES_URL and request.method == "POST"
    assert request.headers["authorization"] == "Bearer synthetic-oauth-token"
    payload = json.loads(request.content)
    assert set(payload) == {"model", "instructions", "input", "stream", "store"}
    assert payload["stream"] is True and payload["store"] is False
    assert payload["model"] == auth.model and isinstance(payload["input"], list)
    assert payload["input"][0]["role"] == "user"
    assert "_execution_identity" not in payload["input"][0]["content"]
    assert "must-not-be-used" not in request.content.decode()


def test_http_client_disables_environment_credentials_proxies_and_redirects(monkeypatch):
    options = []
    original = httpx.AsyncClient

    def capture(**kwargs):
        options.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", capture)
    provider, _, _ = adapter(completed(draft_payload(), delta=False))
    provider.draft(context())
    assert options[0]["trust_env"] is False
    assert options[0]["follow_redirects"] is False


@pytest.mark.parametrize("code,status", [
    ("subscription_sharing_usage_limit_exceeded", 429),
    ("subscription_sharing_usage_unavailable", 503),
    ("rate_limit_exceeded", 429),
    ("insufficient_quota", 429),
    (None, 429),
])
def test_http_limit_stops_later_roles_without_fallback_or_retry(code, status):
    payload = {"error": {"code": code, "message": "sensitive diagnostic"}} if code else {"detail": "not a stable code"}
    provider, auth, calls = adapter(json.dumps(payload), status=status)
    with pytest.raises(ChatGPTUsageStopped) as error:
        provider.draft(context())
    assert auth.stop_code == (code or "rate_limit_exceeded")
    assert "sensitive diagnostic" not in str(error.value)
    with pytest.raises(ChatGPTUsageStopped):
        provider.evaluate({"project_id": "project-test", "brief": {"version": "1.0.1"}})
    assert len(calls) == 1


def test_unknown_429_code_is_normalized_and_never_echoed_in_failure_metadata():
    secret_code = "opaque-credential-value-never-retain"
    provider, auth, calls = adapter(json.dumps({"error": {"code": secret_code, "message": "private raw body"}}), status=429)
    with pytest.raises(ChatGPTUsageStopped) as error:
        provider.draft(context())
    assert error.value.code == "rate_limit_exceeded" and auth.stop_code == "rate_limit_exceeded"
    assert secret_code not in json.dumps(vars(error.value)) + str(error.value)
    assert len(calls) == 1


def test_unknown_nonusage_error_code_is_never_returned_as_persistable_metadata():
    opaque_code = "opaque-credential-value-never-retain"
    provider, _, calls = adapter(json.dumps({"error": {"code": opaque_code, "message": opaque_code}}), status=400)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_response_failed"
    assert opaque_code not in json.dumps(vars(error.value)) + str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("code", ["subscription_sharing_usage_limit_exceeded", "subscription_sharing_usage_unavailable"])
def test_midstream_usage_failure_never_returns_partial_draft_and_latches(code):
    body = event({"type": "response.output_text.delta", "delta": json.dumps(draft_payload())})
    body += event({"type": "response.failed", "response": {"error": {"code": code, "message": "never display"}}})
    provider, auth, calls = adapter(body)
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert auth.stop_code == code
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [(429, "rate_limit_exceeded"), (401, "authentication_required")])
def test_known_stop_status_remains_latched_when_reading_its_error_body_fails(status, code):
    class BrokenBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            raise httpx.ReadTimeout("body interrupted")
            yield b""

    calls = []

    def fail_body(request):
        calls.append(request)
        return httpx.Response(status, stream=BrokenBody())

    auth = FakeAuth()
    provider = ChatGPTCharacterProvider(auth, transport=httpx.MockTransport(fail_body))
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert auth.stop_code == code
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [(401, "authentication_required"), (429, "rate_limit_exceeded")])
def test_known_stop_status_is_durable_before_the_first_error_body_read(status, code):
    auth = FakeAuth()

    class CheckLatch(httpx.AsyncByteStream):
        async def __aiter__(self):
            assert auth.stop_code == code
            yield json.dumps({"error": {"code": "subscription_sharing_usage_limit_exceeded"}}).encode()

    provider = ChatGPTCharacterProvider(auth, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, stream=CheckLatch())))
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert auth.stop_code is not None


def test_nonstream_usage_error_is_latched_without_accepting_a_plain_json_response():
    provider, auth, _ = adapter(json.dumps({"error": {"code": "subscription_sharing_usage_unavailable"}}),
                                headers={"content-type": "application/json"})
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert auth.stop_code == "subscription_sharing_usage_unavailable"


@pytest.mark.parametrize("terminal", [
    "", "data: [DONE]\n\n",
    event({"type": "response.incomplete", "response": {"incomplete_details": {"reason": "max_output_tokens"}}}),
    event({"type": "response.failed", "response": {"error": {"code": "server_error", "message": "diagnostic"}}}),
    event({"type": "error", "error": {"code": "server_error", "message": "diagnostic"}}),
])
def test_no_partial_result_is_accepted_without_completed_event(terminal):
    body = event({"type": "response.output_text.delta", "delta": json.dumps(draft_payload())}) + terminal
    provider, _, calls = adapter(body)
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert len(calls) == 1


def test_refusal_or_unexpected_tool_output_is_never_character_data():
    body = event({"type": "response.completed", "response": {"status": "completed", "output": [
        {"type": "function_call", "name": "unexpected_tool", "arguments": "{}"}]}})
    provider, _, _ = adapter(body)
    with pytest.raises(ChatGPTProviderError, match="지원하지"):
        provider.draft(context())


@pytest.mark.parametrize("payload", [
    {"fields": {"appearance": "not all fields"}, "assistant_message": "summary"},
    {"fields": DirectionFields().model_dump(), "assistant_message": 4},
    {**draft_payload(), "sheet_approved": True},
])
def test_model_json_is_strict_and_cannot_inject_approval_privileges(payload):
    provider, _, _ = adapter(completed(payload))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_invalid_json"


def test_direct_field_edit_preserves_unrequested_fields_and_exact_user_text():
    before = DirectionFields(appearance="기존 합성 외형", personality="기존 성격").model_dump()
    changed = {**before, "personality": "수정한 성격"}
    provider, _, _ = adapter(completed(draft_payload(fields=changed)))
    result = provider.draft(context(previous_fields=before, field_updates={"personality": "수정한 성격"}))
    assert result["fields"] == changed
    wrong = {**changed, "appearance": "요청하지 않은 외형 변경"}
    provider, _, _ = adapter(completed(draft_payload(fields=wrong)))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context(previous_fields=before, field_updates={"personality": "수정한 성격"}))
    assert error.value.code == "chatgpt_edit_scope_mismatch"


def test_evaluator_is_separate_role_and_bound_to_exact_project_version():
    payload = {"recommendation": "ready_for_human", "issues": [], "evidence": ["합성 입력을 보존함"],
               "project_id": "project-test", "version": "1.0.1"}
    provider, _, calls = adapter(completed(payload))
    ctx = {"project_id": "project-test", "brief": {"version": "1.0.1"}, "request_context": context()}
    assert provider.evaluate(ctx) == payload
    request = json.loads(calls[0].content)
    assert "Independently inspect" in request["instructions"]
    assert json.loads(request["input"][0]["content"])["role"] == "character_evaluator"
    provider, _, _ = adapter(completed({**payload, "version": "1.0.2"}))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.evaluate(ctx)
    assert error.value.code == "chatgpt_evaluation_source_mismatch"


def test_changed_account_or_model_blocks_before_inference():
    provider, _, calls = adapter(completed(draft_payload()))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context(_execution_identity="other-account-or-model"))
    assert error.value.code == "chatgpt_identity_changed" and not calls


def test_account_change_during_stream_discards_result():
    auth = FakeAuth()

    def switch(_):
        auth.identity = "different-login-or-model"

    provider, _, calls = adapter(completed(draft_payload()), auth=auth, inspect=switch)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context(_execution_identity="synthetic-account-client-model-login"))
    assert error.value.code == "chatgpt_identity_changed" and len(calls) == 1


def test_http_admission_errors_remain_sanitized_and_do_not_repeat():
    provider, auth, calls = adapter(json.dumps({"detail": "credential-like-private-data"}), status=403)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.http_status == 403
    assert "private-data" not in str(error.value) and auth.stop_code is None
    assert len(calls) == 1


@pytest.mark.parametrize("status,payload", [
    (401, {"detail": "invalid identity diagnostic"}),
    (401, {"error": {"code": "subscription_sharing_invalid_user"}}),
    (403, {"error": {"code": "subscription_sharing_invalid_user"}}),
])
def test_confirmed_identity_loss_latches_and_prevents_all_later_inference(status, payload):
    provider, auth, calls = adapter(json.dumps(payload), status=status)
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert auth.stop_code == "authentication_required"
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert len(calls) == 1


def test_stream_identity_failure_latches_but_unsupported_capability_allows_model_repair():
    body = event({"type": "response.failed", "response": {"error": {"code": "subscription_sharing_invalid_user"}}})
    provider, auth, calls = adapter(body)
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert auth.stop_code == "authentication_required" and len(calls) == 1
    body = json.dumps({"error": {"code": "subscription_sharing_unsupported_capability", "param": "model"}})
    provider, auth, calls = adapter(body, status=400)
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert auth.stop_code is None and len(calls) == 1


def test_safe_auth_errors_are_preserved_without_inference():
    class SignedOut(FakeAuth):
        def inference_snapshot(self):
            raise ChatGPTAuthError("model_not_selected", "사용할 모델을 먼저 선택해주세요.")

    provider, _, calls = adapter(completed(draft_payload()), auth=SignedOut())
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "model_not_selected" and not calls


def test_error_metadata_preserves_safe_code_param_shape_and_request_id():
    body = json.dumps({"error": {"code": "subscription_sharing_unsupported_capability", "param": "tools[0]", "message": "private diagnostic"}})
    provider, _, _ = adapter(body, status=400, headers={"x-request-id": "req_synthetic_123"})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert (error.value.http_status, error.value.request_id, error.value.error_param, error.value.body_shape) == (
        400, "req_synthetic_123", "tools[0]", "error")
    assert "private diagnostic" not in str(error.value)


@pytest.mark.parametrize("body,expected", [
    ({"error": {"message": "Unsupported parameter: 'instructions'."}}, "reason=unsupported;fields=instructions"),
    ({"detail": "Missing required parameter: 'input[0].type'."}, "reason=required;fields=input,input[].type"),
    ({"error": {"message": "Invalid input: expected an array."}}, "reason=invalid,expected_array;fields=input"),
    ({"detail": "The selected model is not available."}, "reason=not_found;fields=model"),
    ({"error": {"message": "unclassified diagnostic with private data"}}, None),
])
def test_message_only_http400_keeps_static_allowlisted_diagnostic_hint(body, expected):
    provider, _, calls = adapter(json.dumps(body), status=400)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_response_failed" and error.value.http_status == 400
    assert error.value.diagnostic_hint.startswith("content_type=text/event-stream;body=json;keys=")
    if expected:
        assert error.value.diagnostic_hint.endswith(";" + expected)
    else:
        assert error.value.diagnostic_hint == "content_type=text/event-stream;body=json;keys=error"
    assert len(calls) == 1


def test_diagnostic_hint_cannot_persist_echoed_credentials_user_content_or_arbitrary_fields():
    echoed = ("Unsupported parameter 'secret_field_987': Bearer synthetic-oauth-token "
              "eyJhbGciOiJSUzI1NiJ9.private.signature sk-private-api-key person@example.invalid "
              "private user story with a distinct character")
    provider, _, _ = adapter(json.dumps({"error": {"message": echoed}}), status=400)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    # This is generated entirely from static constants, not a redacted body excerpt.
    assert error.value.diagnostic_hint == "content_type=text/event-stream;body=json;keys=error;reason=unsupported;fields=user"
    serialized = json.dumps(vars(error.value), ensure_ascii=False) + str(error.value)
    for forbidden in ("synthetic-oauth-token", "eyJhbGci", "sk-private", "person@example", "secret_field_987", "distinct character"):
        assert forbidden not in serialized


@pytest.mark.parametrize("body,content_type,expected", [
    (json.dumps({"object": "response", "status": "completed", "output": [{"private": "never-retain-generated-text"}]}),
     "application/json; charset=utf-8", "content_type=application/json;body=json;keys=object,status,output;object=response;status=completed;output=array"),
    (completed(draft_payload()), "application/json", "content_type=application/json;body=sse_framed"),
    ("<html>never-retain-login-content</html>", "text/html", "content_type=text/html;body=non_json"),
    (json.dumps({"object": "private-object", "status": "private-status", "type": "private-type", "output": "private-output"}),
     "unknown/with-private-value", "content_type=other;body=json;keys=object,status,type,output;object=other;status=other;type=other;output=other"),
])
def test_nonstream_http200_classification_never_retains_body_or_accepts_completed_json(body, content_type, expected):
    provider, _, calls = adapter(body, headers={"content-type": content_type})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.http_status == 200 and error.value.diagnostic_hint == expected
    assert len(calls) == 1
    assert "private-" not in json.dumps(vars(error.value))
    assert "never-retain" not in json.dumps(vars(error.value))


def test_missing_content_type_accepts_only_a_completed_sse_result_without_another_request():
    provider, _, calls = adapter(completed(draft_payload()), headers={})
    assert provider.draft(context()) == draft_payload()
    assert len(calls) == 1
    request = json.loads(calls[0].content)
    assert request["stream"] is True and request["store"] is False


@pytest.mark.parametrize("body", [
    event({"type": "response.output_text.delta", "delta": json.dumps(draft_payload())}),
    event({"type": "response.output_text.delta", "delta": json.dumps(draft_payload())}) + "data: [DONE]\n\n",
    event({"type": "response.incomplete", "response": {"status": "incomplete"}}),
])
def test_missing_content_type_never_accepts_partial_sse(body):
    provider, _, calls = adapter(body, headers={})
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())
    assert len(calls) == 1


def test_missing_content_type_json_usage_error_still_stops_and_completed_json_still_rejected():
    body = json.dumps({"error": {"code": "subscription_sharing_usage_limit_exceeded"}})
    provider, auth, calls = adapter(body, headers={})
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert auth.stop_code == "subscription_sharing_usage_limit_exceeded" and len(calls) == 1
    body = json.dumps({"object": "response", "status": "completed", "output": []})
    provider, _, calls = adapter(body, headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.diagnostic_hint == "content_type=missing;body=json;keys=object,status,output;object=response;status=completed;output=array"
    assert len(calls) == 1


@pytest.mark.parametrize("status", [400, 403, 429, 503])
def test_non200_sse_is_never_accepted_even_with_completed_event_and_missing_header(status):
    provider, auth, calls = adapter(completed(draft_payload()), status=status, headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.http_status == status and len(calls) == 1
    if status == 429:
        assert auth.stop_code == "rate_limit_exceeded"


def test_missing_content_type_sse_normalization_keeps_original_size_limit():
    provider, _, calls = adapter(":" + "x" * MAX_BODY_BYTES + "\n\n" + completed(draft_payload()), headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_response_too_large"
    assert len(calls) == 1


def test_missing_content_type_uses_same_delta_and_completed_body_consistency_check():
    body = event({"type": "response.output_text.delta", "delta": "different streamed text"}) + completed(draft_payload(), delta=False)
    provider, _, calls = adapter(body, headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_invalid_response" and len(calls) == 1


@pytest.mark.parametrize("headers", [{}, {"content-type": "text/event-stream"}])
@pytest.mark.parametrize("tail", ["timeout", "oversized"])
def test_received_usage_stop_event_is_latched_before_any_broken_or_oversized_tail(headers, tail):
    tail_read = []

    class LateFailure(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield event({"type": "response.failed", "response": {"error": {
                "code": "subscription_sharing_usage_limit_exceeded"}}}).encode()
            tail_read.append(tail)
            if tail == "timeout":
                raise httpx.ReadTimeout("late failure")
            yield b":" + b"x" * (MAX_BODY_BYTES + 1)

    auth, calls = FakeAuth(), []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=LateFailure(), headers=headers)

    provider = ChatGPTCharacterProvider(auth, transport=httpx.MockTransport(handler))
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert auth.stop_code == "subscription_sharing_usage_limit_exceeded"
    assert tail_read == [] and len(calls) == 1


def test_completed_output_missing_diagnostics_contain_counts_and_labels_but_no_text_or_ids():
    text = json.dumps(draft_payload(), ensure_ascii=False)
    body = event({"type": "response.output_text.delta", "delta": text,
                  "output_index": 1, "content_index": 0, "item_id": "private-item-id-never-retain"})
    body += event({"type": "response.output_text.done", "text": text, "output_index": 1, "content_index": 0})
    body += event({"type": "response.completed", "response": {"status": "completed", "output": [{"type": "reasoning"}]}})
    provider, _, _ = adapter(body, headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    hint = error.value.diagnostic_hint
    assert hint.startswith("reason=completed_text_missing;")
    for expected in ("text_parts=0", "text_length=0", "delta_parts=1", f"delta_length={len(text)}",
                     "done_parts=1", "delta_done_match=yes", "done_completed_match=missing",
                     "delta_output_indices=1", "delta_content_indices=0", "delta_item_ids=1",
                     "messages=0", "output_types=reasoning"):
        assert expected in hint
    assert "private-item" not in hint and "외형" not in hint and text not in hint


def test_delta_mismatch_diagnostics_report_fixed_message_channel_role_and_status_labels():
    payload = draft_payload()
    text = json.dumps(payload, ensure_ascii=False)
    body = event({"type": "response.output_text.delta", "delta": "different-private-stream-text",
                  "output_index": 0, "content_index": 0, "item_id": "private-id"})
    body += event({"type": "response.output_text.done", "text": "different-private-stream-text"})
    body += event({"type": "response.completed", "response": {"status": "completed", "output": [{
        "type": "message", "role": "assistant", "channel": "commentary", "phase": "final_answer", "status": "completed",
        "content": [{"type": "output_text", "text": text}]}]}})
    provider, _, _ = adapter(body)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    hint = error.value.diagnostic_hint
    for expected in ("reason=delta_mismatch", "text_parts=1", f"text_length={len(text)}", "messages=1",
                     "roles=assistant", "channels=commentary", "phases=final_answer", "message_statuses=completed",
                     "delta_done_match=yes", "done_completed_match=no"):
        assert expected in hint
    assert "private" not in hint and "외형" not in hint


@pytest.mark.parametrize("headers", [None, {}])
def test_empty_terminal_output_uses_only_agreeing_finalized_indexed_items(headers):
    provider, _, calls = adapter(stream_events(finalized_events(draft_payload())), headers=headers)
    assert provider.draft(context()) == draft_payload()
    assert len(calls) == 1
    assert json.loads(calls[0].content)["stream"] is True


@pytest.mark.parametrize("defect", [
    "missing_delta", "missing_text_done", "missing_item_done", "missing_completed",
    "duplicate_text_done", "malformed_duplicate_done", "duplicate_item_done", "delta_mismatch", "item_text_mismatch",
    "delta_item_id", "done_item_id", "item_done_id", "done_output_index", "done_content_index",
    "item_output_index", "bool_index", "negative_index", "incomplete_item", "nonassistant_item",
    "unsupported_item", "unsupported_content", "delta_after_done", "text_after_item_done",
    "missing_response_status", "incomplete_response_status", "missing_output",
])
def test_empty_terminal_reconstruction_rejects_incomplete_ambiguous_or_disagreeing_sources(defect):
    events = finalized_events(draft_payload())
    if defect == "missing_delta":
        events = events[2:]
    elif defect == "missing_text_done":
        del events[2]
    elif defect == "missing_item_done":
        del events[3]
    elif defect == "missing_completed":
        events.pop()
    elif defect == "duplicate_text_done":
        events.insert(3, dict(events[2]))
    elif defect == "malformed_duplicate_done":
        events.insert(3, {**events[2], "text": None})
    elif defect == "duplicate_item_done":
        events.insert(4, dict(events[3]))
    elif defect == "delta_mismatch":
        events[0]["delta"] = "sensitive-different-delta"
    elif defect == "item_text_mismatch":
        events[3]["item"]["content"][0]["text"] = "sensitive-different-item-text"
    elif defect == "delta_item_id":
        events[0]["item_id"] = "sensitive-different-item-id"
    elif defect == "done_item_id":
        events[2]["item_id"] = "sensitive-different-item-id"
    elif defect == "item_done_id":
        events[3]["item"]["id"] = "sensitive-different-item-id"
    elif defect == "done_output_index":
        events[2]["output_index"] = 1
    elif defect == "done_content_index":
        events[2]["content_index"] = 1
    elif defect == "item_output_index":
        events[3]["output_index"] = 1
    elif defect == "bool_index":
        events[0]["output_index"] = False
    elif defect == "negative_index":
        events[0]["content_index"] = -1
    elif defect == "incomplete_item":
        events[3]["item"]["status"] = "in_progress"
    elif defect == "nonassistant_item":
        events[3]["item"]["role"] = "user"
    elif defect == "unsupported_item":
        events[3]["item"]["type"] = "function_call"
    elif defect == "unsupported_content":
        events[3]["item"]["content"][0]["type"] = "refusal"
    elif defect == "delta_after_done":
        events.insert(3, dict(events[0]))
    elif defect == "text_after_item_done":
        events[2], events[3] = events[3], events[2]
    elif defect == "missing_response_status":
        del events[-1]["response"]["status"]
    elif defect == "incomplete_response_status":
        events[-1]["response"]["status"] = "incomplete"
    elif defect == "missing_output":
        del events[-1]["response"]["output"]
    provider, _, calls = adapter(stream_events(events), headers={})
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert len(calls) == 1
    assert "sensitive-" not in str(error.value) + json.dumps(vars(error.value))


def test_nonempty_terminal_output_must_match_its_own_text_even_when_item_done_matches_deltas():
    events = finalized_events(draft_payload())
    events[-1]["response"]["output"] = [{"type": "message", "role": "assistant", "content": [
        {"type": "output_text", "text": json.dumps(draft_payload(assistant_message="다른 결과"), ensure_ascii=False)}]}]
    provider, _, _ = adapter(stream_events(events))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_invalid_response"
    assert "reason=delta_mismatch" in error.value.diagnostic_hint


@pytest.mark.parametrize("defect", ["missing_status", "incomplete_response", "user_role", "missing_role", "in_progress_message", "null_message_status"])
def test_nonempty_terminal_requires_completed_response_and_completed_assistant_message(defect):
    text = json.dumps(draft_payload(), ensure_ascii=False)
    item = {"type": "message", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": text}]}
    response = {"status": "completed", "output": [item]}
    if defect == "missing_status":
        del response["status"]
    elif defect == "incomplete_response":
        response["status"] = "incomplete"
    elif defect == "user_role":
        item["role"] = "user"
    elif defect == "missing_role":
        del item["role"]
    elif defect == "in_progress_message":
        item["status"] = "in_progress"
    elif defect == "null_message_status":
        item["status"] = None
    provider, _, _ = adapter(event({"type": "response.completed", "response": response}))
    with pytest.raises(ChatGPTProviderError):
        provider.draft(context())


def test_empty_terminal_reconstruction_still_requires_strict_character_contract():
    payload = draft_payload()
    payload["unexpected_approval"] = True
    provider, _, _ = adapter(stream_events(finalized_events(payload)))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_invalid_json"


def test_usage_failure_after_finalized_item_stops_without_accepting_text_before_completed():
    events = finalized_events(draft_payload())
    events.insert(-1, {"type": "response.failed", "response": {"error": {
        "code": "subscription_sharing_usage_limit_exceeded", "message": "sensitive-never-retain"}}})
    provider, auth, calls = adapter(stream_events(events), headers={})
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert auth.stop_code == "subscription_sharing_usage_limit_exceeded" and len(calls) == 1
    with pytest.raises(ChatGPTUsageStopped):
        provider.draft(context())
    assert len(calls) == 1


def test_stage_evaluator_instructions_keep_intentional_unknowns_and_optional_fields_unblocked():
    payload = {"project_id": "project-test", "version": "1.0.1", "recommendation": "ready_for_human",
               "issues": [], "evidence": ["현재 입력만 검토함"]}
    provider, _, calls = adapter(completed(payload))
    assert provider.evaluate({"project_id": "project-test", "brief": {"version": "1.0.1"}}) == payload
    instructions = json.loads(calls[0].content)["instructions"]
    assert "do not block merely because they are empty" in instructions
    assert "Voice, invariants and avoid are optional" in instructions


def test_request_and_response_size_limits_stop_without_partial_commit():
    provider, _, calls = adapter(completed(draft_payload()))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context(message="x" * MAX_BODY_BYTES))
    assert error.value.code == "chatgpt_input_too_large" and not calls
    provider, _, calls = adapter(b":" + b"x" * MAX_BODY_BYTES)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_response_too_large" and len(calls) == 1


def test_deadline_and_transport_timeout_do_not_retry():
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("sensitive diagnostic")

    provider = ChatGPTCharacterProvider(FakeAuth(), transport=httpx.MockTransport(fail))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_timeout" and len(calls) == 1


@pytest.mark.parametrize("headers", [{}, {"content-type": "text/event-stream"}])
def test_absolute_deadline_cancels_a_live_stream_even_when_each_read_is_within_timeout(monkeypatch, headers):
    monkeypatch.setattr("backend.chatgpt_provider.MAX_SECONDS", 0.08)
    lifecycle, calls = [], []

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            try:
                yield b": heartbeat\n\n"
                await asyncio.sleep(0.05)
                yield b": heartbeat\n\n"
                await asyncio.sleep(0.05)
                lifecycle.append("past-total-deadline")
                yield completed(draft_payload()).encode()
            except asyncio.CancelledError:
                lifecycle.append("cancelled")
                raise
            finally:
                lifecycle.append("finished")

        async def aclose(self):
            lifecycle.append("closed")

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=SlowStream(), headers=headers)

    provider = ChatGPTCharacterProvider(FakeAuth(), transport=httpx.MockTransport(handler))
    started = time.monotonic()
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_timeout"
    assert lifecycle == ["cancelled", "finished", "closed"] and len(calls) == 1
    assert time.monotonic() - started < 0.5


@pytest.mark.parametrize("status,code", [(401, "authentication_required"), (429, "rate_limit_exceeded")])
def test_absolute_deadline_during_error_body_preserves_header_stop(monkeypatch, status, code):
    monkeypatch.setattr("backend.chatgpt_provider.MAX_SECONDS", 0.03)
    auth, cancelled = FakeAuth(), []

    class StalledError(httpx.AsyncByteStream):
        async def __aiter__(self):
            assert auth.stop_code == code
            try:
                await asyncio.sleep(1)
                yield b"{}"
            except asyncio.CancelledError:
                cancelled.append(True)
                raise

    provider = ChatGPTCharacterProvider(auth, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, stream=StalledError())))
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_timeout" and auth.stop_code == code
    assert cancelled == [True]


def test_credential_snapshot_time_is_deducted_before_any_inference_request():
    elapsed = [0]

    class ExpiredBudgetAuth(FakeAuth):
        def inference_snapshot(self):
            elapsed[0] = 61
            return super().inference_snapshot()

    provider, _, calls = adapter(completed(draft_payload()), auth=ExpiredBudgetAuth())
    provider._clock = lambda: elapsed[0]
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_timeout" and calls == []


def test_budget_clock_is_checked_while_consuming_the_response():
    provider, _, calls = adapter(completed(draft_payload()))
    ticks = iter([0, 0, 61])
    provider._clock = lambda: next(ticks)
    with pytest.raises(ChatGPTProviderError) as error:
        provider.draft(context())
    assert error.value.code == "chatgpt_timeout" and len(calls) == 1
