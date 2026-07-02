# Methodology (v1.0.0)

MCP Trust Index grades every server with a **transparent, reproducible heuristic
over public GitHub signals**. No grade is hand-tuned per repo. Anyone can re-run
`python src/main.py` and get the same numbers.

## ⚖️ What this is — and is not

- **It IS**: a fast, automated *smell test* for whether an MCP server shows the
  hygiene signals you'd want before wiring it into an AI agent that can touch
  your files, network, and secrets.
- **It is NOT**: a security audit, a penetration test, or a claim that any server
  is "vulnerable." **Absence of a signal is not an accusation.** A perfectly safe
  server can score low simply because it doesn't advertise these signals.

We never emit the word "vulnerable." We only report **signal present / absent**.

## The score

`Trust = Security (0–50) + Liveness (0–50)`, mapped to a letter grade.

### 🛡️ Security signals (max 50)

| Signal | Points | What we look for |
|:--|:--:|:--|
| Open-source LICENSE | 5 | `LICENSE*`/`COPYING`, or GitHub-detected license |
| SECURITY.md | 8 | A published vulnerability-disclosure policy |
| Automated tests | 7 | test/spec files or dirs (`*_test.go`, `*.test.ts`, `tests/`, …) |
| Dependency lockfile | 8 | `package-lock.json`, `poetry.lock`, `go.sum`, `Cargo.lock`, … |
| Container / sandbox | 6 | `Dockerfile`, `docker-compose`, `.devcontainer` |
| CI configured | 6 | `.github/workflows/*`, GitLab CI, CircleCI |
| Documents auth | 5 | README mentions auth / token / permission / scope / OAuth |
| No committed `.env` | 5 | no secret env file checked into the repo |

### ⚡ Liveness signals (max 50)

| Signal | Points | What we look for |
|:--|:--:|:--|
| Recency | up to 22 | days since last push: ≤30→22, ≤90→16, ≤180→10, ≤365→5, else 0 |
| Tagged releases | 8 | at least one release or tag |
| Issue close rate | up to 8 | closed / (open + closed): ≥0.7→8, ≥0.5→5, ≥0.3→2 |
| Installable package | 6 | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, … |
| Adoption (stars) | up to 6 | ≥1000→6, ≥200→4, ≥20→2 |

### Grade thresholds

| Grade | Trust score |
|:--:|:--|
| 🟢 A | ≥ 85 |
| 🟩 B | 70–84 |
| 🟡 C | 55–69 |
| 🟠 D | 40–54 |
| 🔴 F | < 40 |

### 🪦 The graveyard rule

A repo is flagged **graveyard** if it is **archived** or has **no push in over
365 days**. A graveyard can never grade above **D**, regardless of its security
signals, and always sorts below live servers. Dormant code is a risk no matter
how clean it once was.

## Versioning

The methodology is versioned (`METHODOLOGY_VERSION` in `src/config.py`). When
weights or thresholds change, we bump the version so historical grades remain
interpretable. Current: **v1.0.0**.

## Disputing or improving a grade

Grades move the moment your repo does. Add a lockfile, a `SECURITY.md`, CI, or
ship a release, and your score rises on the next weekly run. To flag a
mis-read signal (e.g., tests we failed to detect), open an issue — see
[CONTRIBUTING.md](../CONTRIBUTING.md).
