"""Offline validation of pinned, versioned stage handoff records."""
import copy
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from . import APP_VERSION

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ID = "urn:toon-generator:contracts:mvp-records"
SCHEMA_VERSION = "1.0.0"
SCHEMA = json.loads((ROOT / "docs/contracts/mvp-records-v1.schema.json").read_text("utf-8"))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
FIXTURES = json.loads((ROOT / "docs/contracts/fixtures/mvp-minimum-records.json").read_text("utf-8"))
TEMPLATES = {r["artifact_type"]: r for r in FIXTURES if "artifact_type" in r}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate(record):
    # Revalidate changed bytes, while keeping reads of immutable history inexpensive.
    # Scope/currentness/approval checks are separate and are never cached here.
    _validate_serialized(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False))


@lru_cache(maxsize=2048)
def _validate_serialized(serialized):
    record = json.loads(serialized)
    if "artifact_type" in record:
        if record.get("schema_id") != SCHEMA_ID or record.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("지원하지 않는 계약 버전입니다.")
    errors = list(VALIDATOR.iter_errors(record))
    if errors:
        # Field paths only; values may contain confidential material.
        path = ".".join(str(p) for p in errors[0].absolute_path) or "record"
        raise ValueError(f"계약 필드가 올바르지 않습니다: {path}")


def artifact(kind, project_id, artifact_id, version="1.0.0", content_id=None, sources=()):
    result = copy.deepcopy(TEMPLATES[kind])
    result.update(artifact_id=artifact_id, project_id=project_id, version=version,
                  created_at=now(), created_by="local-mock", owner="local-user",
                  source_artifact_refs=list(sources), state="draft",
                  approval={"status": "pending"}, validation={"status": "passed"},
                  provenance={"synthetic": True, "adapter": "mock", "app_version": APP_VERSION},
                  unresolved_risks=[])
    result.pop("content_id", None)
    if content_id:
        result["content_id"] = content_id
    return result


def ref(record):
    return {k: record[k] for k in ("artifact_id", "version", "project_id", "content_id", "schema_id", "schema_version") if k in record}


def validate_fixtures():
    for record in FIXTURES:
        validate(record)
    return len(FIXTURES)


if __name__ == "__main__":
    print(f"Draft 2020-12 schema and {validate_fixtures()} synthetic fixtures validated offline.")
