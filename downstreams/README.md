---
title: "Reverse dependabot"
language: go
author: "Serge Smertin"
date: 2024-03-30

tags: 
 - github
 - testing
---

# Downstream dependency backwards compatibility enforcer


- [Downstream dependency backwards compatibility enforcer](#downstream-dependency-backwards-compatibility-enforcer)
  - [Usage](#usage)
  - [Logs](#logs)
  - [Releasing](#releasing)

Executes tests of a dependent project and provide a report

## Usage

Add to your `.github/workflows` folder:

```yaml
name: downstreams

on:
  pull_request:
    types: [opened, synchronize]
  merge_group:
    types: [checks_requested]
  push:
    # Always run on push to main. The build cache can only be reused
    # if it was saved by a run from the repository's default branch.
    # The run result will be identical to that from the merge queue
    # because the commit is identical, yet we need to perform it to
    # seed the build cache.
    branches:
      - main

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  ci:
    strategy:
      fail-fast: false
      matrix:
        downstream:
          - name: ucx
          - name: lsql
          - name: remorph
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Install Python
        uses: actions/setup-python@v4
        with:
          cache: 'pip'
          cache-dependency-path: '**/pyproject.toml'
          python-version: 3.10

      - name: Install toolchain
        run: |
          pip install hatch==1.9.4

      - name: Acceptance
        uses: databrickslabs/sandbox/downstreams@downstreams/v0.0.1
        with:
          repo: ${{ matrix.downstream.name }}
          org: databrickslabs
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Logs

If you use `github.com/databrickslabs/sandbox/go-libs/fixtures`, the logs would be available in `go-slog.json` artifact:

```go
import (
	"testing"
	"github.com/databrickslabs/sandbox/go-libs/fixtures"
)

func TestShowDatabases(t *testing.T) {
	ctx, w := fixtures.WorkspaceTest(t)
  // ...
}
```

## Releasing

As long as https://github.com/databrickslabs/sandbox is a monorepo, the `acceptance` action has to get a two-step release process:

1. NodeJS shim - edit version file in `shim.js` to pick `v0.0.1` as version in the top of the file.
2. Go module - `git tag acceptance/v0.0.1` and wait till https://github.com/databrickslabs/sandbox/actions/workflows/acceptance-release.yml is complete.

Tag names must start with `acceptance/` in order for [acceptance-release](../.github/workflows/acceptance-release.yml) to trigger and this folder to be used as Go module.