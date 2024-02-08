all: clean

# See https://www.gnu.org/software/make/manual/make.html

clean:
	rm -fr dist

dist/acceptance:
	./build.sh acceptance

dist/runtime-packages:
	./build.sh runtime-packages

dist/metascan: $(wildcard metascan/*.go) $(wildcard metascan/internal/*.go) $(wildcard metascan/cmd/*.go)
	./build.sh metascan

compress: dist/acceptance dist/runtime-packages dist/metascan
	for file in $(shell ls dist); do \
		zip -r "dist/$$file.zip" "dist/$$file"; \
		rm dist/$$file; \
	done

dist: compress
	cd dist && sha256sum * > SHA256SUMS

.venv/bin/python:
	python3.10 -m venv .venv

dev: .venv/bin/python
	.venv/bin/python -m pip install .
