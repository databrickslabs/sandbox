all: clean lint fmt test

# See https://www.gnu.org/software/make/manual/make.html

# Ensure that all uv commands don't automatically update the lock file. If UV_FROZEN=1 (from the environment)
# then UV_LOCKED should _not_ be set, but otherwise it needs to be set to ensure the lock-file is only ever
# deliberately updated.
ifneq ($(UV_FROZEN),1)
export UV_LOCKED := 1
endif

# Ensure that hatchling is pinned when builds are needed.
export UV_BUILD_CONSTRAINT := .build-constraints.txt

UV_RUN := uv run --exact --all-extras

clean:
	rm -fr dist .venv clean htmlcov .pytest_cache .ruff_cache .coverage coverage.xml
	find . -name '__pycache__' -print0 | xargs -0 rm -fr

dev:
	uv sync --all-extras

lint:
	$(UV_RUN) ruff format --check --diff
	$(UV_RUN) ruff check .

fmt:
	$(UV_RUN) ruff format
	$(UV_RUN) ruff check . --fix

test:
	@echo "No Python tests configured at root level."

build:
	uv build --require-hashes --build-constraints=.build-constraints.txt

lock-dependencies: UV_LOCKED := 0
lock-dependencies:
	uv lock
	$(UV_RUN) --group yq tomlq -r '.["build-system"].requires[]' pyproject.toml | \
		uv pip compile --generate-hashes --universal --no-header - > build-constraints-new.txt
	mv build-constraints-new.txt .build-constraints.txt

# Go targets
dist/runtime-packages: runtime-packages/main.go runtime-packages/go.mod runtime-packages/discover.py
	@go build -o dist/runtime-packages runtime-packages/main.go
	@echo "Building runtime-packages"

dist/metascan: $(wildcard metascan/*.go) $(wildcard metascan/internal/*.go) $(wildcard metascan/cmd/*.go)
	@go build -o dist/metascan metascan/main.go
	@echo "Building metascan"

dist: dist/runtime-packages dist/metascan

test-go-libs:
	cd go-libs && make test

test-acceptance:
	cd acceptance && make test

test-go: test-acceptance test-go-libs

fmt-go-libs:
	cd go-libs && make fmt

fmt-acceptance:
	cd acceptance && make fmt

fmt-llnotes:
	cd llnotes && make fmt

fmt-go: fmt-acceptance fmt-go-libs fmt-llnotes

.DEFAULT: all
.PHONY: all clean dev lint fmt test build lock-dependencies dist test-go-libs test-acceptance test-go fmt-go-libs fmt-acceptance fmt-llnotes fmt-go
