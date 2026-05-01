.PHONY: lint typecheck test format format-check license-check all

ADD_LICENSE_VERSION := 1.2.0
ADD_LICENSE_ARCH := $(shell uname -m)
ADD_LICENSE_OS := $(shell uname -s)

ifeq ($(ADD_LICENSE_ARCH),x86_64)
  ADD_LICENSE_ARCH := x86_64
endif

ifeq ($(ADD_LICENSE_OS),Linux)
  ADD_LICENSE_ARCHIVE := addlicense_v$(ADD_LICENSE_VERSION)_Linux_$(ADD_LICENSE_ARCH).tar.gz
else ifeq ($(ADD_LICENSE_OS),Darwin)
  ADD_LICENSE_ARCHIVE := addlicense_v$(ADD_LICENSE_VERSION)_macOS_$(ADD_LICENSE_ARCH).tar.gz
endif

ADD_LICENSE_URL := https://github.com/google/addlicense/releases/download/v$(ADD_LICENSE_VERSION)/$(ADD_LICENSE_ARCHIVE)
ADD_LICENSE_BIN := .addlicense

$(ADD_LICENSE_BIN):
	curl -sL $(ADD_LICENSE_URL) | tar xz -O addlicense > $(ADD_LICENSE_BIN)
	chmod +x $(ADD_LICENSE_BIN)

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

license-check: $(ADD_LICENSE_BIN)
	$(PWD)/$(ADD_LICENSE_BIN) -check \
		-f .license-header.tmpl \
		-c "FreeCAD ACP Client Contributors" \
		-y 2026 \
		-ignore '**/.venv/**' \
		-ignore '**/__pycache__/**' \
		-ignore '**/.mypy_cache/**' \
		-ignore '**/.ruff_cache/**' \
		-ignore '**/build/**' \
		-ignore '**/*.svg' \
		-ignore '**/py.typed' \
		-ignore '**/*.xml' \
		.

all: lint typecheck format-check license-check test
