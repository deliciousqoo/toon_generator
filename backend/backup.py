"""Bounded, in-memory project packages; never reads or extracts filesystem paths.

The caller takes a consistent storage snapshot before export and registers a new
project copy only after ``unpack_project`` and artifact validation have succeeded.
Passphrase encryption uses the standard age format via pyrage, not a local cipher.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import secrets
import stat
import zipfile
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from . import APP_VERSION

PACKAGE_FORMAT_VERSION = "1.0.0"
SCHEMA_ID = "urn:toon-generator:contracts:mvp-records"
SCHEMA_VERSION = "1.0.0"
MAX_PACKAGE_BYTES = 256 * 1024 * 1024
MAX_ENTRY_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 5000
MAX_JSON_DEPTH = 64
SNAPSHOT_PATH = "records/project.json"
AGE_HEADER = b"age-encryption.org/v1\n"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_MEDIA = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$")
_FORBIDDEN_KEYS = {
    "apikey", "accesstoken", "refreshtoken", "idtoken", "token",
    "password", "passphrase", "secret", "clientsecret", "privatekey",
    "credentials", "credential", "authorization", "cookie", "sessiontoken",
}
_FORBIDDEN_COMPONENTS = {"tmp", "temp", "cache", "runtime-cache", ".env"}
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}
_WORDS = tuple("""
acorn amber anchor apple apron atlas autumn bamboo basket beacon berry birch
blossom bottle breeze bridge brook bubble cabin cactus candle canyon cedar
cherry chestnut cloud clover coast cobalt coffee comet coral cotton crane
crystal daisy dawn delta desert dune eagle earth elm ember falcon feather
fern field finch flame flower forest fossil fountain fox frost garden gate
gem ginger glacier glow golden grape grass grove harbor hazel hill honey
indigo island ivory jade jasmine jewel juniper kettle kiwi lake lantern
laurel leaf lemon lilac lily lime linen lotus maple marble meadow melon
mint mist moon moss mountain nectar north oak ocean olive opal orchid
otter owl peach pearl pebble pine planet plum pond poppy prairie quartz
rain raven reed river robin rock rose ruby sage sand sea shell silver
sky snow south sparrow spice spring spruce star stone stream summer sun
sunset teal thyme tiger trail tulip valley violet water wave wheat willow
wind winter wren yellow zebra zenith
""".split())


class BackupError(ValueError):
    """A safe, user-facing package error that never includes input secrets."""


def generate_passphrase() -> str:
    """Twelve independent random words (over 85 bits with this bundled list)."""
    return "-".join(secrets.choice(_WORDS) for _ in range(12))


def evaluate_passphrase(passphrase: str) -> dict[str, Any]:
    """A length/repetition guide, not a promise of measured password entropy."""
    if not isinstance(passphrase, str):
        raise BackupError("암호문구는 문자열이어야 합니다.")
    length = len(passphrase)
    common = passphrase.casefold() in {
        "password", "password123", "12345678", "123456789012", "qwerty",
    }
    diverse = len(set(passphrase)) >= 8
    score = 0 if common or length < 8 else 1
    if not common and diverse:
        score = 2 if length >= 12 else score
        score = 3 if length >= 20 else score
        score = 4 if length >= 32 else score
    return {
        "score": score,
        "label": ("매우 약함", "약함", "보통", "강함", "긴 암호문구")[score],
        "length": length,
        "guidance": "서로 관계없는 긴 문구나 생성된 암호문구를 사용하세요. 길이 안내는 보안 보증이 아닙니다.",
    }


def _passphrase(value: str | None) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise BackupError("암호화 백업에는 비어 있지 않은 암호문구가 필요합니다.")
    return value


def _safe_path(path: Any) -> str:
    if not isinstance(path, str) or len(path) > 512 or "\\" in path:
        raise BackupError("백업에 허용되지 않은 파일 경로가 있습니다.")
    parts = path.split("/")
    if not parts or any(
        not _ID.fullmatch(part) or part in {".", ".."} or part.endswith(".")
        or part.casefold() in _FORBIDDEN_COMPONENTS
        or part.split(".")[0].upper() in _WINDOWS_DEVICES
        for part in parts
    ):
        raise BackupError("백업에 허용되지 않은 파일 경로가 있습니다.")
    return path


def _safe_identifier(value: Any) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise BackupError("백업의 프로젝트 또는 레코드 ID가 올바르지 않습니다.")
    _safe_path(value)
    return value


def _check_json(value: Any, project_id: str | None = None, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise BackupError("백업의 JSON 중첩 깊이가 제한을 초과합니다.")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise BackupError("백업 JSON의 필드 이름이 올바르지 않습니다.")
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            if normalized in _FORBIDDEN_KEYS:
                raise BackupError("자격 증명 또는 암호 필드는 백업에 포함할 수 없습니다.")
            if key == "project_id" and project_id is not None and child != project_id:
                raise BackupError("백업의 프로젝트 범위가 일치하지 않습니다.")
            if key == "schema_id" and child != SCHEMA_ID:
                raise BackupError("지원하지 않는 스키마 ID입니다.")
            if key == "schema_version" and child != SCHEMA_VERSION:
                raise BackupError("지원하지 않는 스키마 버전입니다.")
            _check_json(child, project_id, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_json(child, project_id, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise BackupError("백업 JSON 숫자가 올바르지 않습니다.")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise BackupError("백업에는 JSON 데이터만 포함할 수 있습니다.")


def _json_bytes(value: Any, limit: int = MAX_JSON_BYTES) -> bytes:
    try:
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError):
        raise BackupError("백업 JSON 데이터가 올바르지 않습니다.") from None
    if len(data) > limit:
        raise BackupError("백업 JSON 크기가 제한을 초과합니다.")
    return data


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise BackupError("백업 JSON에 중복 필드가 있습니다.")
        result[key] = value
    return result


def _load_json(data: bytes) -> dict:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(BackupError("백업 JSON 숫자가 올바르지 않습니다.")))
    except (UnicodeError, ValueError, RecursionError):
        raise BackupError("백업 JSON 데이터가 올바르지 않습니다.") from None
    if not isinstance(value, dict):
        raise BackupError("백업 JSON 최상위 값은 객체여야 합니다.")
    _check_json(value)
    return value


def _snapshot_info(snapshot: dict) -> tuple[str, dict[str, dict]]:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("project"), dict):
        raise BackupError("프로젝트 정보가 없는 백업입니다.")
    project_id = _safe_identifier(snapshot["project"].get("project_id"))
    _check_json(snapshot, project_id)
    _json_bytes(snapshot)
    for collection in ("records", "review_decisions", "audit_events", "episodes"):
        if collection in snapshot and not isinstance(snapshot[collection], list):
            raise BackupError("백업 레코드 목록이 올바르지 않습니다.")
        if any(not isinstance(record, dict) for record in snapshot.get(collection, [])):
            raise BackupError("백업 레코드가 올바르지 않습니다.")
    asset_records: dict[str, dict] = {}
    folded_asset_keys: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for record in snapshot.get("records", []):
        identity = (record.get("artifact_id"), record.get("version"))
        if not all(isinstance(item, str) and item for item in identity) or identity in identities:
            raise BackupError("백업의 아티팩트 ID/버전이 없거나 중복됩니다.")
        identities.add(identity)
        if record.get("project_id") != project_id:
            raise BackupError("백업 레코드의 프로젝트 범위가 일치하지 않습니다.")
        if record.get("schema_id") != SCHEMA_ID or record.get("schema_version") != SCHEMA_VERSION:
            raise BackupError("지원하지 않는 아티팩트 스키마입니다.")
        if record.get("artifact_type") == "asset_record":
            key = _safe_path(record.get("storage_key"))
            if key.casefold() in folded_asset_keys:
                raise BackupError("여러 자산 레코드가 같은 저장 경로를 사용합니다.")
            folded_asset_keys.add(key.casefold())
            if not isinstance(record.get("media_type"), str) or not _MEDIA.fullmatch(record["media_type"]):
                raise BackupError("자산 미디어 형식이 올바르지 않습니다.")
            if type(record.get("byte_size")) is not int or not 0 <= record["byte_size"] <= MAX_ENTRY_BYTES:
                raise BackupError("자산 크기가 제한을 초과하거나 올바르지 않습니다.")
            if not isinstance(record.get("sha256"), str) or not _SHA256.fullmatch(record["sha256"].lower()):
                raise BackupError("자산 체크섬이 올바르지 않습니다.")
            owner = record.get("owner_artifact_ref")
            if not isinstance(owner, dict) or owner.get("project_id") != project_id:
                raise BackupError("자산 소유 아티팩트의 범위가 올바르지 않습니다.")
            asset_records[key] = record
    for record in asset_records.values():
        owner = record["owner_artifact_ref"]
        if (owner.get("artifact_id"), owner.get("version")) not in identities:
            raise BackupError("자산의 소유 아티팩트 버전이 백업에 없습니다.")
    return project_id, asset_records


def _entry(path: str, data: bytes, media_type: str, owner_ref: dict) -> dict:
    return {"path": path, "byte_size": len(data), "media_type": media_type,
            "sha256": hashlib.sha256(data).hexdigest(), "owner_artifact_ref": owner_ref}


def pack_project(snapshot: dict, assets: dict[str, bytes], *, encrypted: bool = False,
                 passphrase: str | None = None) -> tuple[str, bytes]:
    """Export an already-consistent snapshot and every registered asset version."""
    project_id, asset_records = _snapshot_info(snapshot)
    if not isinstance(assets, dict) or set(assets) != set(asset_records):
        raise BackupError("백업 자산 목록이 프로젝트 레코드와 일치하지 않습니다.")
    project_version = snapshot["project"].get("version", "1.0.0")
    if not isinstance(project_version, str) or not _VERSION.fullmatch(project_version):
        raise BackupError("프로젝트 버전이 올바르지 않습니다.")
    snapshot_data = _json_bytes(snapshot)
    entries = [_entry(SNAPSHOT_PATH, snapshot_data, "application/json", {
        "project_id": project_id, "artifact_id": project_id, "version": project_version,
    })]
    contents = {SNAPSHOT_PATH: snapshot_data}
    for key, data in assets.items():
        record = asset_records[key]
        if not isinstance(data, bytes) or len(data) != record["byte_size"] or hashlib.sha256(data).hexdigest() != record["sha256"].lower():
            raise BackupError("프로젝트 자산의 크기 또는 체크섬이 일치하지 않습니다.")
        path = _safe_path("assets/" + key)
        entries.append(_entry(path, data, record["media_type"], record["owner_artifact_ref"]))
        contents[path] = data
    if len(contents) + 1 > MAX_ENTRIES or sum(map(len, contents.values())) > MAX_PACKAGE_BYTES:
        raise BackupError("백업 크기 또는 파일 수가 제한을 초과합니다.")
    backup_id = "backup-" + uuid4().hex
    manifest = {
        "backup_id": backup_id, "package_format_version": PACKAGE_FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "app_version": APP_VERSION, "source_project_id": project_id,
        "schemas": [{"schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION}],
        "files": sorted(entries, key=lambda entry: entry["path"]),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", _json_bytes(manifest, MAX_MANIFEST_BYTES), compress_type=zipfile.ZIP_STORED)
        for path, data in sorted(contents.items()):
            # Media is often already compressed. Storing all entries also avoids
            # decompression amplification and makes the MVP format predictable.
            archive.writestr(path, data, compress_type=zipfile.ZIP_STORED)
    package = buffer.getvalue()
    if len(package) > MAX_PACKAGE_BYTES:
        raise BackupError("백업 크기가 제한을 초과합니다.")
    filename = f"{project_id}-{backup_id}.toonbackup"
    if encrypted:
        secret = _passphrase(passphrase)
        try:
            from pyrage import passphrase as age_passphrase
            package = age_passphrase.encrypt(package, secret)
        except ImportError:
            raise BackupError("age 암호화 라이브러리가 설치되어 있지 않습니다.") from None
        except Exception:
            raise BackupError("age 백업 암호화에 실패했습니다.") from None
        filename += ".age"
    return filename, package


def _validate_manifest(manifest: dict, names: set[str]) -> dict[str, dict]:
    if set(manifest) != {"backup_id", "package_format_version", "created_at", "app_version", "source_project_id", "schemas", "files"}:
        raise BackupError("백업 매니페스트 필드가 올바르지 않습니다.")
    _safe_identifier(manifest["backup_id"])
    _safe_identifier(manifest["source_project_id"])
    if manifest["package_format_version"] != PACKAGE_FORMAT_VERSION:
        raise BackupError("지원하지 않는 백업 패키지 버전입니다.")
    if manifest["schemas"] != [{"schema_id": SCHEMA_ID, "schema_version": SCHEMA_VERSION}]:
        raise BackupError("지원하지 않는 백업 스키마 목록입니다.")
    if not isinstance(manifest["app_version"], str) or not _VERSION.fullmatch(manifest["app_version"]):
        raise BackupError("백업 앱 버전이 올바르지 않습니다.")
    try:
        timestamp = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise BackupError("백업 생성 시간이 올바르지 않습니다.") from None
    if not isinstance(manifest["files"], list) or not 1 <= len(manifest["files"]) < MAX_ENTRIES:
        raise BackupError("백업 파일 목록이 올바르지 않습니다.")
    entries: dict[str, dict] = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "byte_size", "media_type", "sha256", "owner_artifact_ref"}:
            raise BackupError("백업 파일 메타데이터가 올바르지 않습니다.")
        path = _safe_path(entry["path"])
        if path in entries or path == "manifest.json" or (path != SNAPSHOT_PATH and not path.startswith("assets/")):
            raise BackupError("백업에 중복되거나 허용되지 않은 파일이 있습니다.")
        if type(entry["byte_size"]) is not int or not 0 <= entry["byte_size"] <= MAX_ENTRY_BYTES:
            raise BackupError("백업 파일 크기가 올바르지 않습니다.")
        if not isinstance(entry["sha256"], str) or not _SHA256.fullmatch(entry["sha256"]):
            raise BackupError("백업 파일 체크섬이 올바르지 않습니다.")
        if not isinstance(entry["media_type"], str) or not _MEDIA.fullmatch(entry["media_type"]):
            raise BackupError("백업 파일 미디어 형식이 올바르지 않습니다.")
        owner = entry["owner_artifact_ref"]
        if not isinstance(owner, dict) or owner.get("project_id") != manifest["source_project_id"] or not isinstance(owner.get("artifact_id"), str) or not isinstance(owner.get("version"), str) or not _VERSION.fullmatch(owner["version"]):
            raise BackupError("백업 파일의 소유 아티팩트 정보가 올바르지 않습니다.")
        entries[path] = entry
    if set(entries) != names - {"manifest.json"} or SNAPSHOT_PATH not in entries:
        raise BackupError("매니페스트와 실제 백업 파일 목록이 일치하지 않습니다.")
    return entries


def unpack_project(data: bytes, *, passphrase: str | None = None) -> tuple[dict, dict[str, bytes], dict]:
    """Validate the complete package, returning data without writing anything.

    The returned project keeps its source ID. The storage transaction creates a
    new ID and remaps all internal project references while preserving lineage.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_PACKAGE_BYTES + 1024 * 1024:
        raise BackupError("백업 파일이 비어 있거나 크기 제한을 초과합니다.")
    if data.startswith(AGE_HEADER):
        secret = _passphrase(passphrase)
        try:
            from pyrage import passphrase as age_passphrase
            data = age_passphrase.decrypt(data, secret)
        except ImportError:
            raise BackupError("age 암호화 라이브러리가 설치되어 있지 않습니다.") from None
        except Exception:
            raise BackupError("암호문구가 올바르지 않거나 암호화 백업이 손상되었습니다.") from None
    if len(data) > MAX_PACKAGE_BYTES or not data.startswith(b"PK\x03\x04"):
        raise BackupError("지원하지 않거나 손상된 백업 파일입니다.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if not 2 <= len(infos) <= MAX_ENTRIES:
                raise BackupError("백업 파일 수가 제한을 초과하거나 올바르지 않습니다.")
            names: set[str] = set()
            folded: set[str] = set()
            total = 0
            for info in infos:
                if info.orig_filename != info.filename:
                    raise BackupError("백업 파일 경로에 허용되지 않은 문자가 있습니다.")
                name = _safe_path(info.filename)
                if name in names or name.casefold() in folded or info.is_dir():
                    raise BackupError("백업에 중복 파일이나 디렉터리가 있습니다.")
                names.add(name)
                folded.add(name.casefold())
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFREG) or info.flag_bits & 1:
                    raise BackupError("백업의 링크 또는 ZIP 암호화 파일은 허용되지 않습니다.")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise BackupError("지원하지 않는 ZIP 압축 형식입니다.")
                limit = MAX_MANIFEST_BYTES if name == "manifest.json" else MAX_JSON_BYTES if name == SNAPSHOT_PATH else MAX_ENTRY_BYTES
                if info.file_size > limit:
                    raise BackupError("백업 파일 크기가 제한을 초과합니다.")
                total += info.file_size
                if total > MAX_PACKAGE_BYTES:
                    raise BackupError("백업 전체 크기가 제한을 초과합니다.")
            if "manifest.json" not in names:
                raise BackupError("백업 매니페스트가 없습니다.")
            manifest = _load_json(archive.read("manifest.json"))
            entries = _validate_manifest(manifest, names)
            contents: dict[str, bytes] = {}
            for name, entry in entries.items():
                info = archive.getinfo(name)
                if info.file_size != entry["byte_size"]:
                    raise BackupError("백업 파일 크기가 매니페스트와 일치하지 않습니다.")
                content = archive.read(info)
                if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                    raise BackupError("백업 파일 체크섬이 일치하지 않습니다.")
                contents[name] = content
            snapshot = _load_json(contents.pop(SNAPSHOT_PATH))
            project_id, asset_records = _snapshot_info(snapshot)
            if project_id != manifest["source_project_id"]:
                raise BackupError("백업 원본 프로젝트 범위가 일치하지 않습니다.")
            assets = {name[len("assets/"):]: content for name, content in contents.items()}
            if set(assets) != set(asset_records):
                raise BackupError("백업 자산 목록이 프로젝트 레코드와 일치하지 않습니다.")
            project_version = snapshot["project"].get("version", "1.0.0")
            expected_project_owner = {"project_id": project_id, "artifact_id": project_id, "version": project_version}
            if entries[SNAPSHOT_PATH]["media_type"] != "application/json" or entries[SNAPSHOT_PATH]["owner_artifact_ref"] != expected_project_owner:
                raise BackupError("프로젝트 레코드 파일의 소유 정보가 일치하지 않습니다.")
            for key, content in assets.items():
                record = asset_records[key]
                entry = entries["assets/" + key]
                if len(content) != record["byte_size"] or hashlib.sha256(content).hexdigest() != record["sha256"].lower() or entry["media_type"] != record["media_type"] or entry["owner_artifact_ref"] != record["owner_artifact_ref"]:
                    raise BackupError("백업 자산과 자산 레코드 정보가 일치하지 않습니다.")
            return snapshot, assets, manifest
    except BackupError:
        raise
    except (zipfile.BadZipFile, RuntimeError, OSError, ValueError, KeyError, TypeError, EOFError):
        raise BackupError("지원하지 않거나 손상된 백업 패키지입니다.") from None
