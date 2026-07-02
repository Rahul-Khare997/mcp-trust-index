# Contributing

Thanks for helping keep the MCP Trust Index accurate and useful.

## ➕ Add a server

1. Edit [`servers.yaml`](servers.yaml).
2. Put the `owner/repo` slug under the most fitting category (add a category if
   none fits).
3. Open a PR. The weekly bot re-scores everything — you don't need to run
   anything, but you can (see below).

Unknown, renamed, or deleted repos are skipped with a warning and never break
the build.

## 🛠️ Improve or dispute your grade

Grades are an **automated heuristic**, not an audit (see
[docs/METHODOLOGY.md](docs/METHODOLOGY.md)). Two ways to act on a grade:

- **Raise it** — the honest way. Add a `SECURITY.md`, a dependency lockfile, CI,
  tests, or cut a release. Your score updates on the next weekly run.
- **Report a mis-read signal** — if we failed to detect something you *do* have
  (e.g., tests in a layout our matcher misses), open an issue titled
  `grade: <owner>/<repo>` describing the signal and where it lives. If it's a
  detector gap, we'll fix the heuristic (and bump the methodology version).

We will **not** manually override a score to be higher or lower than the signals
warrant. The whole value of the index is that it's mechanical and reproducible.

## 💻 Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# build from bundled fixtures — no network, no token:
python src/main.py --offline

# build live against GitHub (set a token to avoid rate limits):
export GITHUB_TOKEN=ghp_xxx
python src/main.py            # or: --limit 20 to test a slice
```

Then run the smoke tests:

```bash
python -m unittest discover -s tests -v
```

## Ground rules

- Don't add your own repo just to farm a grade — that's fine, actually, as long
  as it's a real MCP server. Spam and non-MCP repos will be removed.
- Keep the methodology honest. PRs that special-case individual repos will be
  declined; PRs that improve detection for a *class* of repos are welcome.
