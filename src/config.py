"""Shared configuration: paths, grade thresholds, scoring weights.

Everything here is intentionally transparent and versioned. The whole point of
MCP Trust Index is that grades are reproducible from public signals — so the
rules live in one readable place, not scattered magic numbers.
"""
from __future__ import annotations

from pathlib import Path

# --- Methodology version (bump when weights/thresholds change) ---------------
METHODOLOGY_VERSION = "1.0.0"

# --- Paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
SERVERS_YAML = ROOT / "servers.yaml"
FIXTURES = ROOT / "fixtures" / "sample_repos.json"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
BADGES_DIR = ROOT / "badges"
TEMPLATES_DIR = ROOT / "templates"
README_OUT = ROOT / "README.md"
DATA_JSON_OUT = DATA_DIR / "data.json"
RAW_JSON_OUT = DATA_DIR / "raw.json"

# --- Grade thresholds (on 0-100 total trust score) ---------------------------
# Ordered high -> low. First threshold met wins.
GRADE_THRESHOLDS = [
    ("A", 85),
    ("B", 70),
    ("C", 55),
    ("D", 40),
    ("F", 0),
]

# A repo flagged as a "graveyard" (archived, or no push in this many days)
# can never grade above this letter, regardless of security signals.
GRAVEYARD_MAX_GRADE = "D"
GRAVEYARD_STALE_DAYS = 365

# --- Security signals (max 50) ----------------------------------------------
# Each is an additive, evidence-based signal. We never assert "vulnerable" —
# only "signal present / absent". Absence lowers the score; it is not an
# accusation. This framing is load-bearing (see docs/METHODOLOGY.md).
SECURITY_WEIGHTS = {
    "license_present": 5,
    "security_md": 8,
    "has_tests": 7,
    "dependency_lockfile": 8,
    "containerized": 6,
    "ci_configured": 6,
    "documents_auth": 5,
    "no_committed_env": 5,
}  # sum = 50

# Human-readable descriptions surfaced in per-server reports.
SECURITY_LABELS = {
    "license_present": "Has an open-source LICENSE",
    "security_md": "Publishes a SECURITY.md disclosure policy",
    "has_tests": "Ships an automated test suite",
    "dependency_lockfile": "Pins dependencies with a lockfile",
    "containerized": "Provides container/sandbox (Docker/devcontainer)",
    "ci_configured": "Runs CI on every change",
    "documents_auth": "Documents auth / permissions / scopes",
    "no_committed_env": "No committed .env secret file",
}

# --- Liveness signals (max 50) ----------------------------------------------
# Recency is scored on a decay curve; the rest are booleans/buckets.
LIVENESS_RECENCY_BUCKETS = [
    (30, 22),
    (90, 16),
    (180, 10),
    (365, 5),
]  # (max_days, points); older than last bucket -> 0
LIVENESS_RECENCY_MAX = 22

LIVENESS_WEIGHTS = {
    "has_releases": 8,
    "issue_health": 8,
    "published_package": 6,
    "adoption": 6,
}  # + recency(22) => sum = 50

LIVENESS_LABELS = {
    "recency": "Recently maintained (recent commits)",
    "has_releases": "Cuts tagged releases",
    "issue_health": "Healthy issue close rate",
    "published_package": "Publishes an installable package",
    "adoption": "Community adoption (stars)",
}

# Adoption buckets: (min_stars, points)
ADOPTION_BUCKETS = [(1000, 6), (200, 4), (20, 2)]

# Issue health: closed / (open + closed). (min_ratio, points)
ISSUE_HEALTH_BUCKETS = [(0.7, 8), (0.5, 5), (0.3, 2)]
