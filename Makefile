all: clean

# See https://www.gnu.org/software/make/manual/make.html

clean:
	rm -fr dist

dist/runtime-packages: runtime-packages/main.go runtime-packages/go.mod runtime-packages/discover.py
	go build -o dist/runtime-packages runtime-packages/main.go

dist: dist/runtime-packages
	@echo "Building runtime package detector"