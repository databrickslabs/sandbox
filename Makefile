all: clean

# See https://www.gnu.org/software/make/manual/make.html

clean:
	rm -fr dist

dist/runtime-packages: runtime-packages/main.go runtime-packages/go.mod runtime-packages/discover.py
	@go build -o dist/runtime-packages runtime-packages/main.go
	@echo "Building runtime-packages"

dist/metascan: $(wildcard metascan/*.go) $(wildcard metascan/internal/*.go) $(wildcard metascan/cmd/*.go)
	@go build -o dist/metascan metascan/main.go
	@echo "Building metascan"

dist: dist/runtime-packages dist/metascan

.venv/bin/python:
	python3.10 -m venv .venv

dev: .venv/bin/python
	.venv/bin/python -m pip install .

test-go-libs:
	cd go-libs && make test

test-acceptance:
	cd acceptance && make test

test: test-acceptance test-go-libs