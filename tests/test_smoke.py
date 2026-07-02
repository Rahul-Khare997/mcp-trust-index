"""Smoke tests for the MCP Trust Index scoring engine.

Run: python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from collect import collect_offline  # noqa: E402
from score import score_all, score_repo  # noqa: E402


def _raw(**overrides):
    base = {
        "slug": "acme/mcp", "name": "mcp", "owner": "acme",
        "url": "https://github.com/acme/mcp", "description": "", "category": "Test",
        "stars": 5000, "pushed_at": "2026-06-25T00:00:00Z", "archived": False,
        "license": "MIT", "open_issues": 10, "closed_issues": 90,
        "default_branch": "main", "language": "Python", "files": [],
        "readme_text": "", "has_releases": True,
    }
    base.update(overrides)
    return base


class TestScoring(unittest.TestCase):
    def test_full_security_signals_max_out(self):
        r = score_repo(_raw(files=[
            "LICENSE", "SECURITY.md", "tests/x_test.py", "poetry.lock",
            "Dockerfile", ".github/workflows/ci.yml", "pyproject.toml",
        ], readme_text="configure your auth token"))
        self.assertEqual(r["security_score"], 50)

    def test_go_test_files_detected(self):
        r = score_repo(_raw(files=["internal/server_test.go", "go.mod"]))
        earned = {e["key"] for e in r["security_earned"]}
        self.assertIn("has_tests", earned)

    def test_committed_env_loses_points(self):
        clean = score_repo(_raw(files=["src/index.js"]))
        dirty = score_repo(_raw(files=["src/index.js", ".env"]))
        self.assertGreater(clean["security_score"], dirty["security_score"])

    def test_archived_is_graveyard_capped_at_D(self):
        r = score_repo(_raw(archived=True, files=[
            "LICENSE", "SECURITY.md", "tests/x_test.py", "poetry.lock",
            "Dockerfile", ".github/workflows/ci.yml", "pyproject.toml",
        ], readme_text="auth token"))
        self.assertTrue(r["graveyard"])
        self.assertIn(r["grade"], {"D", "F"})  # never A/B/C despite full security

    def test_stale_repo_is_graveyard(self):
        r = score_repo(_raw(pushed_at="2024-01-01T00:00:00Z"))
        self.assertTrue(r["graveyard"])
        self.assertEqual(r["graveyard_reason"], "stale >1y")

    def test_graveyards_sink_below_live_servers(self):
        raws = [
            _raw(slug="live/low", stars=10, files=["src/i.js"], has_releases=False,
                 open_issues=50, closed_issues=1),                     # weak but live
            _raw(slug="dead/strong", archived=True, files=[
                "LICENSE", "SECURITY.md", "tests/x_test.py", "poetry.lock"]),  # strong but dead
        ]
        ranked = score_all(raws)
        self.assertFalse(ranked[0]["graveyard"], "a live server must rank first")
        self.assertTrue(ranked[-1]["graveyard"], "a graveyard must rank last")


class TestPipeline(unittest.TestCase):
    def test_offline_fixtures_load_and_score(self):
        raws = collect_offline()
        self.assertGreaterEqual(len(raws), 5)
        scored = score_all(raws)
        # ranks are contiguous 1..N
        self.assertEqual([s["rank"] for s in scored], list(range(1, len(scored) + 1)))
        # every score in range
        for s in scored:
            self.assertTrue(0 <= s["trust_score"] <= 100)
            self.assertIn(s["grade"], {"A", "B", "C", "D", "F"})


if __name__ == "__main__":
    unittest.main()
