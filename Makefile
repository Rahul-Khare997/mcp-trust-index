.PHONY: install build build-live test clean

install:
	python -m venv .venv
	./.venv/bin/pip install -U pip
	./.venv/bin/pip install -r requirements.txt

# Build from bundled fixtures — no network, no token.
build:
	./.venv/bin/python src/main.py --offline

# Build live against the GitHub API. Set GITHUB_TOKEN to avoid rate limits.
build-live:
	./.venv/bin/python src/main.py

test:
	./.venv/bin/python -m unittest discover -s tests -v

clean:
	rm -rf reports badges data/raw.json __pycache__ src/__pycache__ tests/__pycache__
