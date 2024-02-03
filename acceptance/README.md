---
title: "GitHub Action for Acceptance Testing"
language: go
author: "Serge Smertin"
date: 2024-01-15

tags: 
 - github
 - testing
---

# GitHub Action for Acceptance Testing


- [GitHub Action for Acceptance Testing](#github-action-for-acceptance-testing)
  - [Usage](#usage)
  - [Logs](#logs)
  - [Artifacts](#artifacts)
    - [`event.json`](#eventjson)
    - [`test-report.json`](#test-reportjson)
    - [`go-coverprofile`](#go-coverprofile)
    - [`go-test.out`](#go-testout)
    - [`go-test.err`](#go-testerr)

Executes tests, comments on PR, links to worflow run, uploads artifacts for later analysis. Only once comment is created per PR and gets edited with subsequent runs.

![Alt text](comments.png)

## Usage

Add to your `.github/workflows` folder:

```yaml
name: acceptance

on:
  pull_request:
    types: [opened, synchronize]
    paths: ['go-libs/**']

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  acceptance:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: 1.21

      - name: Acceptance
        uses: databrickslabs/sandbox/acceptance@actions/artifact
        with:
          directory: go-libs
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

Python support is coming soon.

## Artifacts

### `event.json`

GitHub Actions raw event information. Example:

```json
{
  "action": "synchronize",
  "after": "faa8a5ba40d987cb981362581e556eb676761161",
  "before": "3d0b4fe5bdc45292358a29dde28718e1605efcad",
  "enterprise": {
    ...
  },
  "number": 69,
  "organization": {
    ...
  },
  "pull_request": {
    "_links": {
```

### `test-report.json`

Normalised integration test execution report across all ecosystems. Example:

```json
{"ts":"2024-02-03T15:28:16.940198637Z","project":"go-libs","package":"sqlexec","name":"TestAccErrorMapping","pass":false,"skip":true,"output":"=== RUN   TestAccErrorMapping\n    init.go:96: Environment variable CLOUD_ENV is missing\n--- SKIP: TestAccErrorMapping (0.00s)\n","elapsed":0}
{"ts":"2024-02-03T15:28:16.940348556Z","project":"go-libs","package":"sqlexec","name":"TestAccMultiChunk","pass":false,"skip":true,"output":"=== RUN   TestAccMultiChunk\n    init.go:96: Environment variable CLOUD_ENV is missing\n--- SKIP: TestAccMultiChunk (0.00s)\n","elapsed":0}
```

### `go-coverprofile`

Code coverage profile for Go applications. Example:

```
mode: set
github.com/databrickslabs/sandbox/go-libs/env/context.go:13.53,15.22 2 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:15.22,17.3 1 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:18.2,18.12 1 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:21.52,22.16 1 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:22.16,24.3 1 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:25.2,26.9 2 0
github.com/databrickslabs/sandbox/go-libs/env/context.go:26.9,28.3 1 0
```

### `go-test.out`

Standard outout from `go test -json` command. Example:

```json
{"Time":"2024-02-03T15:28:06.204157427Z","Action":"start","Package":"github.com/databrickslabs/sandbox/go-libs"}
{"Time":"2024-02-03T15:28:06.204217579Z","Action":"output","Package":"github.com/databrickslabs/sandbox/go-libs","Output":"?   \tgithub.com/databrickslabs/sandbox/go-libs\t[no test files]\n"}
...
```

### `go-test.err`

Standard error from `go test` command. Example:

```
go: downloading github.com/spf13/cobra v1.8.0
go: downloading github.com/fatih/color v1.16.0
go: downloading github.com/spf13/pflag v1.0.5
go: downloading github.com/spf13/viper v1.18.2
go: downloading github.com/stretchr/testify v1.8.4
```