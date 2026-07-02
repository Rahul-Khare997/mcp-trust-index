"""MCP Trust Index — pipeline entrypoint.

Usage:
  python src/main.py --offline          # build from fixtures (no network)
  python src/main.py                     # live: read servers.yaml, hit GitHub API
  python src/main.py --limit 20          # live but only first N repos (debug)

Env:
  GITHUB_TOKEN  — recommended in live mode to avoid tight rate limits.
"""
from __future__ import annotations

import argparse
import json
import sys

import yaml

from collect import collect_live, collect_offline
from config import RAW_JSON_OUT, SERVERS_YAML
from render import render_all
from score import score_all


def load_servers() -> list[tuple[str, str]]:
    """servers.yaml -> list of (slug, category), order preserved."""
    doc = yaml.safe_load(SERVERS_YAML.read_text(encoding="utf-8")) or {}
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for category in doc.get("categories", []):
        cat_name = category.get("name", "Uncategorized")
        for slug in category.get("servers", []):
            slug = slug.strip()
            if slug and slug not in seen:
                seen.add(slug)
                pairs.append((slug, cat_name))
    return pairs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the MCP Trust Index.")
    ap.add_argument("--offline", action="store_true", help="use fixtures, no network")
    ap.add_argument("--limit", type=int, default=0, help="live: cap number of repos")
    args = ap.parse_args(argv)

    if args.offline:
        print("[collect] offline mode — reading fixtures", file=sys.stderr)
        raw = collect_offline()
    else:
        pairs = load_servers()
        if args.limit:
            pairs = pairs[: args.limit]
        print(f"[collect] live mode — {len(pairs)} repos from servers.yaml", file=sys.stderr)
        raw = collect_live(pairs)

    if not raw:
        print("[error] no repos collected — aborting", file=sys.stderr)
        return 1

    RAW_JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW_JSON_OUT.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    scored = score_all(raw)
    result = render_all(scored)

    s = result["stats"]
    print(
        f"[done] {s['total']} servers scored | "
        f"A:{s['grade_counts']['A']} B:{s['grade_counts']['B']} "
        f"C:{s['grade_counts']['C']} D:{s['grade_counts']['D']} F:{s['grade_counts']['F']} | "
        f"graveyards:{s['graveyards']} | avg:{s['avg_score']}/100",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
