# Contributing

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/pngdeity/freecad-acp.git
   cd freecad-acp
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

3. Install development tools:
   ```bash
   pip install pytest ruff mypy
   ```

3. (Optional) For local development inside FreeCAD, copy or symlink the `freecad/` directory into your FreeCAD `Mod` directory:
   ```bash
   # Linux
   ln -s "$(pwd)/freecad/acpclient" ~/.local/share/FreeCAD/Mod/acpclient
   # Windows
   mklink /D "%APPDATA%\FreeCAD\Mod\acpclient" "C:\path\to\freecad-acp\freecad\acpclient"
   # macOS
   ln -s "$(pwd)/freecad/acpclient" ~/Library/Application\ Support/FreeCAD/Mod/acpclient
   ```

## Running Tests

```bash
pytest tests/ -v
```

## Lint

```bash
ruff check .
```

## Typecheck

```bash
mypy freecad/
```

## Formatting

```bash
ruff format .
```

## CI

Quality checks are defined as Makefile targets, making them portable across CI providers. Run `make all` to execute the full pipeline locally.

See [`docs/ci.md`](ci.md) for the CI architecture.
