"""Collect raw signals for each MCP server repo.

Two modes:
  * live    — hit the GitHub REST API (uses GITHUB_TOKEN if present).
  * offline — read fixtures/sample_repos.json so the full pipeline runs with
              zero network (used in CI smoke tests and local dev).

Raw record schema (the contract score.py/render.py depend on):
  {
    slug, name, owner, url, description, category,
    stars, pushed_at (ISO), archived (bool), license (str|None),
    open_issues (int), closed_issues (int), default_branch (str),
    language (str|None), files (list[str]), readme_text (str),
    has_releases (bool),
  }
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from typing import Any, Iterable

import requests

from config import FIXTURES

API = "https://api.github.com"
UA = "mcp-trust-index (+https://github.com/)"


class GitHubError(RuntimeError):
    pass


class GitHubCollector:
    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.s = session or requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept": "application/vnd.github+json"})
        if self.token:
            self.s.headers["Authorization"] = f"Bearer {self.token}"

    # -- low level ------------------------------------------------------------
    def _get(self, path: str, **params) -> tuple[int, Any]:
        url = path if path.startswith("http") else f"{API}{path}"
        for attempt in range(4):
            r = self.s.get(url, params=params, timeout=30)
            # primary/secondary rate limit backoff
            if r.status_code == 403 and "rate limit" in r.text.lower():
                reset = int(r.headers.get("X-RateLimit-Reset", "0"))
                wait = max(2, reset - int(time.time())) if reset else 2 ** attempt
                wait = min(wait, 60)
                sys.stderr.write(f"  rate limited; sleeping {wait}s\n")
                time.sleep(wait)
                continue
            try:
                body = r.json()
            except ValueError:
                body = None
            return r.status_code, body
        raise GitHubError(f"exhausted retries for {url}")

    # -- per-repo signal fetch ------------------------------------------------
    def fetch_repo(self, slug: str, category: str) -> dict[str, Any]:
        owner, _, name = slug.partition("/")
        status, meta = self._get(f"/repos/{slug}")
        if status == 404:
            raise GitHubError(f"{slug}: not found (renamed/deleted?)")
        if status != 200 or not isinstance(meta, dict):
            raise GitHubError(f"{slug}: repo meta HTTP {status}")

        default_branch = meta.get("default_branch") or "main"
        files = self._fetch_tree(slug, default_branch)
        readme_text = self._fetch_readme(slug)
        has_releases = self._has_releases(slug)
        closed_issues = self._closed_issue_count(slug)
        open_issues = self._open_issue_count(slug, meta)

        lic = meta.get("license") or {}
        return {
            "slug": slug,
            "name": name,
            "owner": owner,
            "url": meta.get("html_url", f"https://github.com/{slug}"),
            "description": (meta.get("description") or "").strip(),
            "category": category,
            "stars": meta.get("stargazers_count", 0),
            "pushed_at": meta.get("pushed_at"),
            "archived": bool(meta.get("archived")),
            "license": (lic.get("spdx_id") if lic.get("spdx_id") not in (None, "NOASSERTION") else None),
            "open_issues": open_issues,
            "closed_issues": closed_issues,
            "default_branch": default_branch,
            "language": meta.get("language"),
            "files": files,
            "readme_text": readme_text,
            "has_releases": has_releases,
        }

    def _fetch_tree(self, slug: str, branch: str) -> list[str]:
        status, body = self._get(f"/repos/{slug}/git/trees/{branch}", recursive=1)
        if status != 200 or not isinstance(body, dict):
            return []
        return [n["path"] for n in body.get("tree", []) if n.get("type") == "blob"]

    def _fetch_readme(self, slug: str) -> str:
        status, body = self._get(f"/repos/{slug}/readme")
        if status != 200 or not isinstance(body, dict):
            return ""
        content = body.get("content", "")
        if body.get("encoding") == "base64" and content:
            try:
                return base64.b64decode(content).decode("utf-8", "replace")
            except Exception:
                return ""
        return ""

    def _has_releases(self, slug: str) -> bool:
        status, body = self._get(f"/repos/{slug}/releases", per_page=1)
        if status == 200 and isinstance(body, list) and body:
            return True
        status, body = self._get(f"/repos/{slug}/tags", per_page=1)
        return status == 200 and isinstance(body, list) and bool(body)

    def _closed_issue_count(self, slug: str) -> int:
        status, body = self._get(
            "/search/issues", q=f"repo:{slug} type:issue state:closed", per_page=1
        )
        if status == 200 and isinstance(body, dict):
            return int(body.get("total_count", 0))
        return 0

    def _open_issue_count(self, slug: str, meta: dict) -> int:
        status, body = self._get(
            "/search/issues", q=f"repo:{slug} type:issue state:open", per_page=1
        )
        if status == 200 and isinstance(body, dict):
            return int(body.get("total_count", 0))
        # fall back to repo counter (includes PRs, imperfect but non-fatal)
        return int(meta.get("open_issues_count", 0))


# --- public entrypoints ------------------------------------------------------

def collect_live(repos: Iterable[tuple[str, str]], token: str | None = None) -> list[dict]:
    """repos: iterable of (slug, category)."""
    collector = GitHubCollector(token=token)
    out: list[dict] = []
    for slug, category in repos:
        try:
            sys.stderr.write(f"  fetching {slug}\n")
            out.append(collector.fetch_repo(slug, category))
        except GitHubError as e:
            sys.stderr.write(f"  !! skip {slug}: {e}\n")
    return out


def collect_offline() -> list[dict]:
    with open(FIXTURES, encoding="utf-8") as fh:
        return json.load(fh)
