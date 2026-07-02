# MCP Trust Index — Design & Launch Doc

_Date: 2026-07-01 · Status: built, E2E-verified, not yet published_

## Goal

A personal GitHub repo engineered to earn a lot of stars with near-zero ongoing
upkeep. Strategy: **auto-generating curated resource** (the highest-star genre on
GitHub) in a hot niche (**MCP servers**), on an **axis no incumbent owns**
(trust/security instead of popularity).

## Why this shape

- Most-starred repos are curated knowledge, not tools → build a list, not a CLI.
- "Near-zero upkeep" → GitHub Actions regenerates everything weekly; owner just
  merges the occasional `servers.yaml` PR.
- MCP popularity lists already exist (`best-of-mcp-servers`, `awesome-mcp-servers`,
  registries) → don't compete on popularity. Grade on **security + liveness**,
  the ecosystem's #1 unmet anxiety.

## Architecture

```
servers.yaml → collect.py → score.py → render.py → README.md + reports/ + badges/ + data/data.json
 (seed list)   (GH API/       (transparent  (Jinja2)     (committed weekly by the bot)
                fixtures)      heuristic)
```

- **collect.py** — live GitHub REST (uses `GITHUB_TOKEN`) or `--offline` fixtures.
  One raw-record schema feeds everything downstream.
- **score.py** — Security (0–50) + Liveness (0–50) → Trust (0–100) → A–F. Archived
  or >1yr-stale repos are flagged **graveyard**, capped at D, and sink in rank.
  Every point is an evidence-based signal with a human-readable reason.
- **render.py** — ranked category README, per-server report cards, shields.io
  endpoint badges, and an embeddable `data.json`. Rank movement (▲▼🆕) diffs the
  previous `data.json`.
- **.github/workflows/update.yml** — weekly cron + manual + on-list-change;
  runs tests, rebuilds live, commits back.

Full scoring rules: [METHODOLOGY.md](METHODOLOGY.md).

## Deliberate scope calls (YAGNI)

- Liveness = static installability + maintenance signals, **not** literally booting
  1,900 servers weekly (flaky, needs secrets, kills the zero-upkeep goal). Deep
  boot-tests can come later for a curated top-N.
- No website, DB, accounts, or CVE/vuln claims at v1. Pure repo + Actions.

## Risk framing (load-bearing)

Grading others' repos "F on security" can anger maintainers. Mitigations baked in:
transparent versioned methodology; "informational, not an audit" disclaimer on
README + every report; language is **signal present/absent**, never "vulnerable";
grades rise automatically when a maintainer adds the missing signal; dispute path
in CONTRIBUTING.md.

## Launch plan (automation sustains, the launch ignites)

1. Publish with the full demo README already polished; run once live to populate
   real grades before announcing.
2. Salvo (one day): Show HN "I graded every MCP server on security", r/mcp +
   r/LocalLLaMA + r/programming, an X/LinkedIn thread, a dev.to writeup. Hook =
   the F-grades and the graveyard.
3. Judo the incumbents: submit as a *resource* to existing awesome-lists/registries
   so they link back.
4. Offer maintainers embeddable "MCP Trust: A" badges → they market the repo for you.

## Roadmap after v1

- Grow `servers.yaml` toward the full ecosystem (community PRs + a seeding script).
- History page / trend charts from archived `data.json`.
- Optional deep boot-test tier for top-50.
- A tiny static site over `data.json` (GitHub Pages) for SEO once traction shows.
