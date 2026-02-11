from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from auditgraph.config import Config, redaction_settings
from auditgraph.errors import SecurityPolicyError
from auditgraph.storage.artifacts import ensure_dir, profile_pkg_root
from auditgraph.utils.profile import validate_profile_name


@dataclass(frozen=True)
class RedactionDetector:
    name: str
    category: str
    pattern: re.Pattern[str]
    group: int = 0


@dataclass(frozen=True)
class RedactionPolicy:
    policy_id: str
    version: str
    enabled: bool
    detectors: tuple[RedactionDetector, ...]


@dataclass
class RedactionSummary:
    counts_by_category: dict[str, int] = field(default_factory=dict)
    total_matches: int = 0

    def add(self, category: str, count: int = 1) -> None:
        self.counts_by_category[category] = self.counts_by_category.get(category, 0) + count
        self.total_matches += count

    def merge(self, other: "RedactionSummary") -> None:
        for category, count in other.counts_by_category.items():
            self.add(category, count)

    def to_dict(self) -> dict[str, object]:
        return {
            "counts_by_category": dict(self.counts_by_category),
            "total_matches": self.total_matches,
        }


@dataclass(frozen=True)
class RedactionResult:
    value: Any
    summary: RedactionSummary


def _build_marker(category: str, secret: str, key: bytes) -> str:
    digest = hmac.new(key, secret.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
    return f"<<redacted:{category}:{digest}>>"


def _apply_detector(text: str, detector: RedactionDetector, summary: RedactionSummary, key: bytes) -> str:
    if not text:
        return text
    parts: list[str] = []
    last_index = 0
    for match in detector.pattern.finditer(text):
        group_index = detector.group
        try:
            start, end = match.span(group_index)
        except IndexError:
            start, end = match.span(0)
        if start < last_index:
            continue
        secret = match.group(group_index)
        parts.append(text[last_index:start])
        parts.append(_build_marker(detector.category, secret, key))
        parts.append(text[end:match.end()])
        last_index = match.end()
        summary.add(detector.category)
    if not parts:
        return text
    parts.append(text[last_index:])
    return "".join(parts)


def _default_detectors() -> dict[str, RedactionDetector]:
    return {
        "pem_private_key": RedactionDetector(
            name="pem_private_key",
            category="private_key",
            pattern=re.compile(
                r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL,
            ),
        ),
        "jwt": RedactionDetector(
            name="jwt",
            category="jwt",
            pattern=re.compile(r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        ),
        "bearer_token": RedactionDetector(
            name="bearer_token",
            category="bearer",
            pattern=re.compile(r"(?i)authorization:\s*bearer\s+([A-Za-z0-9._~-]+)"),
            group=1,
        ),
        "credential_kv": RedactionDetector(
            name="credential_kv",
            category="credential",
            pattern=re.compile(
                r"(?i)\b(password|secret|token|api_key|apikey|client_secret|private_key)\s*[:=]\s*([^\s\"']+)",
            ),
            group=2,
        ),
        "url_credentials": RedactionDetector(
            name="url_credentials",
            category="url_credential",
            pattern=re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^/\s:@]+:([^@\s]+)@"),
            group=1,
        ),
        "vendor_token": RedactionDetector(
            name="vendor_token",
            category="vendor_token",
            pattern=re.compile(r"\b(ghp_[A-Za-z0-9]{12,}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
        ),
    }


def redaction_policy_for_config(config: Config) -> RedactionPolicy:
    settings = redaction_settings(config)
    enabled = bool(settings.get("enabled", True))
    policy_id = str(settings.get("policy_id", "redaction.policy.v1"))
    version = str(settings.get("policy_version", "v1"))
    detectors = _default_detectors()
    requested = settings.get("detectors")
    if isinstance(requested, Iterable) and not isinstance(requested, (str, bytes)):
        selected = [detectors[name] for name in requested if name in detectors]
        return RedactionPolicy(policy_id=policy_id, version=version, enabled=enabled, detectors=tuple(selected))
    return RedactionPolicy(policy_id=policy_id, version=version, enabled=enabled, detectors=tuple(detectors.values()))


def redaction_key_path(pkg_root: Path) -> Path:
    return pkg_root / "secrets" / "redaction.key"


def load_or_create_redaction_key(pkg_root: Path, profile: str) -> bytes:
    validate_profile_name(profile)
    path = redaction_key_path(pkg_root)
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            raise SecurityPolicyError("Redaction key is empty")
        return bytes.fromhex(raw)
    key = secrets.token_bytes(32)
    ensure_dir(path.parent)
    path.write_text(key.hex(), encoding="utf-8")
    return key


class Redactor:
    def __init__(self, policy: RedactionPolicy, key: bytes) -> None:
        self._policy = policy
        self._key = key

    @property
    def policy(self) -> RedactionPolicy:
        return self._policy

    def _redact_text_with_summary(self, text: str, summary: RedactionSummary) -> str:
        if not self._policy.enabled:
            return text
        redacted = text
        for detector in self._policy.detectors:
            redacted = _apply_detector(redacted, detector, summary, self._key)
        return redacted

    def redact_text(self, text: str) -> RedactionResult:
        summary = RedactionSummary()
        redacted = self._redact_text_with_summary(text, summary)
        return RedactionResult(value=redacted, summary=summary)

    def redact_payload(self, payload: Any) -> RedactionResult:
        summary = RedactionSummary()
        redacted = self._redact_payload(payload, summary)
        return RedactionResult(value=redacted, summary=summary)

    def _redact_payload(self, payload: Any, summary: RedactionSummary) -> Any:
        if isinstance(payload, str):
            return self._redact_text_with_summary(payload, summary)
        if isinstance(payload, dict):
            return {key: self._redact_payload(value, summary) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self._redact_payload(item, summary) for item in payload]
        if isinstance(payload, tuple):
            return tuple(self._redact_payload(item, summary) for item in payload)
        return payload


def build_redactor(root: Path, config: Config) -> Redactor:
    policy = redaction_policy_for_config(config)
    key = b""
    if policy.enabled:
        pkg_root = profile_pkg_root(root, config)
        key = load_or_create_redaction_key(pkg_root, config.active_profile())
    return Redactor(policy, key)


def build_redactor_for_pkg_root(pkg_root: Path, config: Config) -> Redactor:
    policy = redaction_policy_for_config(config)
    key = b""
    if policy.enabled:
        key = load_or_create_redaction_key(pkg_root, config.active_profile())
    return Redactor(policy, key)
