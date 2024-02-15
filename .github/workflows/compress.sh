#!/bin/bash

for file in dist/*; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" | cut -d. -f1)
        zip -r "dist/$filename.zip" "$file"
        rm "dist/$file"
    fi
done

cd dist
sha256sum * > SHA256SUMS
cd -