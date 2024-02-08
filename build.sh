#!/bin/sh

app=$1

# Define platforms and architectures
platforms=("windows" "linux" "darwin")
architectures=("amd64" "arm64")
mkdir -p dist

# Build binaries for each platform and architecture combination
for GOOS in "${platforms[@]}"; do
    for GOARCH in "${architectures[@]}"; do
        target="dist/${app}_${GOOS}_${GOARCH}"
        if [ "$GOOS" == "windows" ]; then
            target="$target.exe"
        fi
        GOOS=$GOOS GOARCH=$GOARCH go build -ldflags="-s -w" -o $target $app/main.go
    done
done
