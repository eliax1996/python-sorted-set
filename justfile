default:
    @just --list

# ── Linting ──────────────────────────────────────────────────────────────────

lint:
    uv run ruff check treap.py feistel.py tests/

format:
    uv run ruff format treap.py feistel.py tests/

# ── Type checking ──────────────────────────────────────────────────────────────

ty:
    uv run ty check treap.py

# ── Testing ────────────────────────────────────────────────────────────────────

test:
    uv run python3 -m pytest tests/ -q
