#!/bin/bash

set -e

echo "Formatting code..."
echo "=================="

# Format Python code with ruff
echo "Formatting Python files with ruff..."
uv run ruff format .
uv run ruff check --fix .

# Type check Python code with ty
echo "Type checking Python files with ty..."
uv run ty check

# Format TypeScript/JavaScript files with prettier
echo "Formatting TypeScript/JavaScript files..."
cd client
npm run format 2>/dev/null || {
    echo "No npm format script found, using prettier directly..."
    npx prettier --write "src/**/*.{ts,tsx,js,jsx,json,css}" 2>/dev/null || {
        echo "Prettier not available, skipping TypeScript formatting"
    }
}
cd ..

echo "✅ Code formatting complete!"