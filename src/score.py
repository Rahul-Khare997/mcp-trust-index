"""Turn a raw repo record into a transparent trust score.

Input:  a raw record (see collect.py schema)
Output: the same record enriched with security/liveness subscores, a total,
        a letter grade, a graveyard flag, and a list of human-readable reasons.

No signal ever asserts a vulnerability. Every point is "evidence present".
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from config import (
    ADOPTION_BUCKETS,
    GRADE_THRESHOLDS,
    GRAVEYARD_MAX_GRADE,
    GRAVEYARD_STALE_DAYS,
    ISSUE_HEALTH_BUCKETS,
    LIVENESS_RECENCY_BUCKETS,
    LIVENESS_WEIGHTS,
    SECURITY_LABELS,
    SECURITY_WEIGHTS,
)

_LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "uv.lock", "pipfile.lock", "go.sum", "cargo.lock", "composer.lock",
    "gemfile.lock",
}
_CONTAINER_FILES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml"}
_LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md"}
_PKG_MANIFESTS = {"package.json", "pyproject.toml", "setup.py", "cargo.toml", "go.mod"}
_AUTH_RE = re.compile(
    r"\b(auth|authentication|oauth|api[\s_-]?key|token|permission|scope|credential)\b",
    re.IGNORECASE,
)


def _basenames(files: list[str]) -> set[str]:
    return {f.rsplit("/", 1)[-1].lower() for f in files}


def _days_since(iso_ts: str | None) -> float | None:
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0


# --- Security predicates -----------------------------------------------------

def _security_flags(raw: dict[str, Any]) -> dict[str, bool]:
    files = raw.get("files") or []
    lowered = [f.lower() for f in files]
    names = _basenames(files)
    readme = raw.get("readme_text") or ""

    def any_path(pred) -> bool:
        return any(pred(p) for p in lowered)

    return {
        "license_present": bool(raw.get("license")) or bool(names & _LICENSE_NAMES),
        "security_md": "security.md" in names,
        "has_tests": any_path(
            lambda p: p.startswith("test") or "/test" in p or "__tests__" in p
            or "/spec" in p or p.startswith("spec")
            # language-specific test filename conventions
            or p.endswith(("_test.py", "_test.go", "_test.rs", "_test.exs"))
            or p.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx"))
            or p.endswith((".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx"))
            or p.endswith(("test.java", "tests.cs", "_spec.rb"))
        ),
        "dependency_lockfile": bool(names & _LOCKFILES),
        "containerized": bool(names & _CONTAINER_FILES) or any_path(lambda p: ".devcontainer" in p),
        "ci_configured": any_path(
            lambda p: p.startswith(".github/workflows/")
            or p in (".gitlab-ci.yml", ".circleci/config.yml")
        ),
        "documents_auth": bool(_AUTH_RE.search(readme)),
        # ".env" committed is bad; ".env.example" / ".env.sample" are fine.
        "no_committed_env": ".env" not in names,
    }


def _score_security(raw: dict[str, Any]) -> tuple[int, list[dict], list[dict]]:
    flags = _security_flags(raw)
    earned, missing = [], []
    total = 0
    for key, weight in SECURITY_WEIGHTS.items():
        label = SECURITY_LABELS[key]
        if flags[key]:
            total += weight
            earned.append({"key": key, "label": label, "points": weight})
        else:
            missing.append({"key": key, "label": label, "points": weight})
    return total, earned, missing


# --- Liveness predicates -----------------------------------------------------

def _recency_points(days: float | None) -> int:
    if days is None:
        return 0
    for max_days, pts in LIVENESS_RECENCY_BUCKETS:
        if days <= max_days:
            return pts
    return 0


def _bucket_points(value: float, buckets: list[tuple[float, int]]) -> int:
    for threshold, pts in buckets:
        if value >= threshold:
            return pts
    return 0


def _score_liveness(raw: dict[str, Any]) -> tuple[int, list[dict], list[dict], float | None]:
    days = _days_since(raw.get("pushed_at"))
    earned, missing = [], []
    total = 0

    # recency (decay curve)
    rec = _recency_points(days)
    total += rec
    rec_entry = {"key": "recency", "label": "Recently maintained", "points": rec}
    (earned if rec > 0 else missing).append(rec_entry)

    # releases
    has_rel = bool(raw.get("has_releases"))
    w = LIVENESS_WEIGHTS["has_releases"]
    e = {"key": "has_releases", "label": "Cuts tagged releases", "points": w}
    if has_rel:
        total += w
        earned.append(e)
    else:
        missing.append(e)

    # issue health
    opened = raw.get("open_issues") or 0
    closed = raw.get("closed_issues") or 0
    ratio = (closed / (opened + closed)) if (opened + closed) > 0 else 0.0
    ih = _bucket_points(ratio, ISSUE_HEALTH_BUCKETS)
    total += ih
    ih_entry = {"key": "issue_health", "label": f"Issue close rate {ratio:.0%}", "points": ih}
    (earned if ih > 0 else missing).append(ih_entry)

    # published package
    names = _basenames(raw.get("files") or [])
    published = bool(names & _PKG_MANIFESTS)
    w = LIVENESS_WEIGHTS["published_package"]
    e = {"key": "published_package", "label": "Publishes an installable package", "points": w}
    if published:
        total += w
        earned.append(e)
    else:
        missing.append(e)

    # adoption
    stars = raw.get("stars") or 0
    ad = _bucket_points(stars, ADOPTION_BUCKETS)
    total += ad
    ad_entry = {"key": "adoption", "label": f"{stars:,} stars", "points": ad}
    (earned if ad > 0 else missing).append(ad_entry)

    return total, earned, missing, days


# --- Grade assignment --------------------------------------------------------

def _letter(total: int) -> str:
    for letter, threshold in GRADE_THRESHOLDS:
        if total >= threshold:
            return letter
    return "F"


def _cap_grade(letter: str, cap: str) -> str:
    order = [g for g, _ in GRADE_THRESHOLDS]  # A,B,C,D,F
    if order.index(letter) < order.index(cap):
        return cap
    return letter


def score_repo(raw: dict[str, Any]) -> dict[str, Any]:
    sec, sec_earned, sec_missing = _score_security(raw)
    live, live_earned, live_missing, days = _score_liveness(raw)
    total = sec + live

    archived = bool(raw.get("archived"))
    stale = days is not None and days > GRAVEYARD_STALE_DAYS
    graveyard = archived or stale

    grade = _letter(total)
    if graveyard:
        grade = _cap_grade(grade, GRAVEYARD_MAX_GRADE)

    return {
        **raw,
        "security_score": sec,
        "liveness_score": live,
        "trust_score": total,
        "grade": grade,
        "graveyard": graveyard,
        "graveyard_reason": (
            "archived" if archived else ("stale >1y" if stale else None)
        ),
        "days_since_push": round(days, 1) if days is not None else None,
        "security_earned": sec_earned,
        "security_missing": sec_missing,
        "liveness_earned": live_earned,
        "liveness_missing": live_missing,
    }


def score_all(raws: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [score_repo(r) for r in raws]
    # Rank: graveyards always sink below live servers; then highest trust
    # first; stable by name.
    scored.sort(key=lambda s: (s["graveyard"], -s["trust_score"], s["slug"].lower()))
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return scored
