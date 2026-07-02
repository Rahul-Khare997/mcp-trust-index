"""Render scored records into the committed artifacts:

  * README.md          — the ranked, category-grouped scoreboard
  * reports/<slug>.md  — one transparent report card per server
  * data/data.json     — machine-readable export (embeddable by others)
  * badges/<slug>.json — shields.io endpoint badges ("Trust: A")

Rank movement (↑/↓/new) is computed by diffing against the previous data.json,
so the very first run shows everything as "new" and later runs show drift.
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import (
    BADGES_DIR,
    DATA_JSON_OUT,
    METHODOLOGY_VERSION,
    README_OUT,
    REPORTS_DIR,
    TEMPLATES_DIR,
)

GRADE_COLOR = {
    "A": "brightgreen",
    "B": "green",
    "C": "yellow",
    "D": "orange",
    "F": "red",
}
GRADE_EMOJI = {"A": "🟢", "B": "🟩", "C": "🟡", "D": "🟠", "F": "🔴"}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(enabled_extensions=(), default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _slug_file(slug: str) -> str:
    return slug.replace("/", "__")


def _load_previous_ranks() -> dict[str, int]:
    if not DATA_JSON_OUT.exists():
        return {}
    try:
        prev = json.loads(DATA_JSON_OUT.read_text(encoding="utf-8"))
        return {r["slug"]: r["rank"] for r in prev.get("servers", [])}
    except Exception:
        return {}


def _movement(slug: str, rank: int, prev: dict[str, int]) -> dict[str, Any]:
    if slug not in prev:
        return {"symbol": "🆕", "delta": None, "label": "new"}
    delta = prev[slug] - rank  # positive => moved up
    if delta > 0:
        return {"symbol": f"▲{delta}", "delta": delta, "label": f"up {delta}"}
    if delta < 0:
        return {"symbol": f"▼{abs(delta)}", "delta": delta, "label": f"down {abs(delta)}"}
    return {"symbol": "—", "delta": 0, "label": "no change"}


def _group_by_category(scored: list[dict]) -> "OrderedDict[str, list[dict]]":
    groups: "OrderedDict[str, list[dict]]" = OrderedDict()
    for row in scored:
        groups.setdefault(row.get("category") or "Uncategorized", []).append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: r["rank"])
    return groups


def _stats(scored: list[dict]) -> dict[str, Any]:
    counts = Counter(r["grade"] for r in scored)
    graveyards = sum(1 for r in scored if r["graveyard"])
    avg = round(sum(r["trust_score"] for r in scored) / len(scored), 1) if scored else 0
    return {
        "total": len(scored),
        "grade_counts": {g: counts.get(g, 0) for g in ["A", "B", "C", "D", "F"]},
        "graveyards": graveyards,
        "avg_score": avg,
    }


def render_all(scored: list[dict], generated_at: str | None = None) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prev_ranks = _load_previous_ranks()

    for row in scored:
        row["movement"] = _movement(row["slug"], row["rank"], prev_ranks)
        row["grade_color"] = GRADE_COLOR[row["grade"]]
        row["grade_emoji"] = GRADE_EMOJI[row["grade"]]
        row["report_path"] = f"reports/{_slug_file(row['slug'])}.md"

    stats = _stats(scored)
    groups = _group_by_category(scored)
    env = _env()

    # README
    readme = env.get_template("README.md.j2").render(
        generated_at=generated_at,
        methodology_version=METHODOLOGY_VERSION,
        stats=stats,
        groups=groups,
        scored=scored,
        grade_emoji=GRADE_EMOJI,
    )
    README_OUT.write_text(readme, encoding="utf-8")

    # per-server reports
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_tpl = env.get_template("report.md.j2")
    for row in scored:
        out = report_tpl.render(r=row, methodology_version=METHODOLOGY_VERSION,
                                generated_at=generated_at)
        (REPORTS_DIR / f"{_slug_file(row['slug'])}.md").write_text(out, encoding="utf-8")

    # badges (shields.io endpoint format)
    BADGES_DIR.mkdir(parents=True, exist_ok=True)
    for row in scored:
        badge = {
            "schemaVersion": 1,
            "label": "MCP Trust",
            "message": f"{row['grade']} ({row['trust_score']}/100)",
            "color": row["grade_color"],
        }
        (BADGES_DIR / f"{_slug_file(row['slug'])}.json").write_text(
            json.dumps(badge), encoding="utf-8"
        )

    # machine-readable export
    export = {
        "generated_at": generated_at,
        "methodology_version": METHODOLOGY_VERSION,
        "stats": stats,
        "servers": [
            {
                "rank": r["rank"],
                "slug": r["slug"],
                "url": r["url"],
                "category": r["category"],
                "grade": r["grade"],
                "trust_score": r["trust_score"],
                "security_score": r["security_score"],
                "liveness_score": r["liveness_score"],
                "graveyard": r["graveyard"],
                "stars": r.get("stars", 0),
                "days_since_push": r.get("days_since_push"),
            }
            for r in scored
        ],
    }
    DATA_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA_JSON_OUT.write_text(json.dumps(export, indent=2), encoding="utf-8")

    return {"stats": stats, "readme_bytes": len(readme), "reports": len(scored)}
