# AGENTS.md

## Before any work: activate the venv

Always run this first before any shell command:

```bash
export PATH=".venv/bin:$PATH"
```

This ensures `mypy`, `ruff`, and `pytest` resolve from the project venv.
System-wide binaries may run against wrong site-packages and produce
spurious errors.

## Toolchain

This project uses **uv** for package management. Install dependencies with
`uv pip install`, not raw `pip`.

Install stubs for type checking (required for mypy to pass):

```bash
uv pip install types-Markdown
```

## Debugging with external libraries

When encountering unexpected behavior from any external library or software
dependency, consult the library's official documentation to validate
assumptions before proceeding with debugging. Do not rely solely on
source-code inspection or prior knowledge — verify expected API signatures,
return types, side effects, and threading guarantees against the docs.

## Quality checks

```bash
make all          # lint, typecheck, format-check, test
make lint         # ruff check .
make typecheck    # mypy freecad/
make test         # pytest tests/ -v
make format       # ruff format .
make format-check # ruff format --check .
```
