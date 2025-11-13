# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**llnotes** is a CLI tool that generates GitHub release notes using LLMs hosted on Databricks Model Serving. It's part of the databrickslabs/sandbox monorepo and uses the shared `go-libs` library for common functionality.

## Monorepo Structure

This project exists within a Go workspace monorepo (`../go.work`). Key locations:
- **Application code**: `./llnotes/` (this directory)
- **Shared libraries**: `../go-libs/` - contains reusable packages including:
  - `llnotes`: Core business logic for release notes generation
  - `lite`: CLI framework for building commands
  - `github`: GitHub API integration utilities
  - `git`: Git operations helpers
- **Other projects**: `../acceptance/`, `../metascan/`, etc.

## Build & Development Commands

```bash
# Build the project (default target)
make

# Run linting
make lint

# Run tests
make test

# View test coverage in browser
make coverage

# Format code
make fmt

# Update dependencies and vendor folder
make vendor
```

**Important**: This project uses `go work vendor` (not `go mod vendor`) because it's part of a Go workspace. Always run `make vendor` instead of `go mod vendor`.

## Running the Application

### Authentication Setup

Before using llnotes, authenticate with both services:

```bash
# Databricks authentication
databricks auth login https://....cloud.databricks.com/

# GitHub authentication
gh auth login
```

### Available Commands

```bash
# Generate pull request description
llnotes pull-request --number <PR_NUMBER>

# Generate release notes for upcoming release
llnotes upcoming-release

# Generate release notes between two git references
llnotes diff --since <TAG_OR_COMMIT> --until <TAG_OR_COMMIT>

# Generate release announcement
llnotes announce --version <VERSION>
```

### Configuration Flags

Common flags available across commands:
- `--model`: Serving chat model (default: "databricks-claude-sonnet-4-5")
- `--org`: GitHub organization (default: "databrickslabs")
- `--repo`: GitHub repository (default: "ucx")
- `--profile`: Databricks config profile
- GitHub authentication: `--github-token`, `--github-app-id`, `--github-app-installation-id`, etc.

Config is stored in `$HOME/.databricks/labs/llnotes/`

## Architecture

### Command Structure

The application uses the `lite` framework (from `go-libs/lite`) for CLI scaffolding. Commands are registered in `main.go`:
- Each command follows the `lite.Command` pattern with `Name`, `Short`, `Flags`, and `Run` functions
- Commands interact with the core `llnotes` library (`../go-libs/llnotes/`)
- The `askFor()` helper provides interactive prompts for iterative refinement

### Core Library (go-libs/llnotes)

The business logic lives in `../go-libs/llnotes/`:
- `pull_request.go`: PR description generation
- `release_notes.go`: Release notes from commits
- `diff.go`: Diff-based release notes
- `announce.go`: Release announcements
- `talk.go`: Interactive chat with LLM
- `chain.go`: Message chain management

### Key Design Patterns

1. **Conversation Chain**: Uses a message chain pattern (`chain.go`) to maintain context across LLM interactions
2. **Interactive Mode**: `pull-request` and `announce` commands support iterative refinement through user prompts
3. **Settings Configuration**: Central `Settings` struct manages GitHub and Databricks credentials, model selection, and repo details

## Dependencies

- `github.com/databricks/databricks-sdk-go`: Databricks API SDK for model serving
- `github.com/databrickslabs/sandbox/go-libs`: Shared monorepo libraries
- `github.com/spf13/pflag`: CLI flag parsing
- `github.com/fatih/color`: Terminal color output

## Testing

Tests use the standard Go testing framework with `gotestsum` for better output formatting:
- Test files would follow `*_test.go` naming convention
- Run with `make test` (includes coverage output to `coverage.txt`)
- Use `-short` flag to skip long-running tests
