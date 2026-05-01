.PHONY: lint typecheck test format format-check all

lint:
	ruff check .

typecheck:
	mypy freecad/

test:
	pytest tests/ -v

format:
	ruff format .

format-check:
	ruff format --check .

all: lint typecheck format-check test
