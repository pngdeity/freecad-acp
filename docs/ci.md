# Continuous Integration

## Design

The CI pipeline is defined as **Makefile targets**, making it provider-agnostic. Any CI system only needs to:

1. Set up a Python environment (install `requirements.txt` + `pytest ruff mypy`)
2. Run `make all`

This means switching from GitHub Actions to GitLab CI, Jenkins, or a local pre-commit hook requires no changes to the quality checks themselves.

## Pipeline Stages

| Target | Command | Description |
|--------|---------|-------------|
| `lint` | `ruff check .` | Lint all Python source |
| `typecheck` | `mypy freecad/` | Static type checking |
| `format-check` | `ruff format --check .` | Verify formatting (non-mutating) |
| `test` | `pytest tests/ -v` | Run unit tests |
| `all` | (all of the above) | Full pipeline |

The `format` target (`ruff format .`) is a **mutating** convenience for local development and is not part of the `all` pipeline. CI uses the non-mutating `format-check` instead.

## Local Usage

```bash
# Run the full pipeline (what CI runs)
make all

# Run individual stages
make lint
make typecheck
make test
make format-check

# Auto-fix formatting locally
make format
```

## Adding a New CI Provider

1. Install Python and dependencies (see `docs/contributing.md`)
2. Run `make all`
3. Fail the build on any non-zero exit code

### Example: GitLab CI

```yaml
# .gitlab-ci.yml
image: python:3.10

before_script:
  - pip install -r requirements.txt pytest ruff mypy

test:
  script:
    - make all
```

### Example: Local pre-commit hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
make all
```

## Current Provider: GitHub Actions

See `.github/workflows/ci.yml` — it installs Python 3.10 and 3.11, caches dependencies via pip cache, and runs `make all`.
