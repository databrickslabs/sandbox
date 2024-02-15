#!/bin/bash

for file in dist/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" | cut -d. -f1)
        zip -r "dist/$filename.zip" "$file" &
    fi
done

wait

cd dist
sha256sum * > SHA256SUMS
cd -