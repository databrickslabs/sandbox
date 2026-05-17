# Contributing to dbx-agent-app

Thank you for your interest in contributing to dbx-agent-app! This project is a Databricks Labs initiative to make it easier to build discoverable AI agents on Databricks Apps.

## Development Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Use Black for code formatting: `black src/`
- Use Ruff for linting: `ruff check src/`
- Line length: 100 characters (configured in `pyproject.toml`)
- Type hints are encouraged for public APIs

## Testing

- Write tests for new features using pytest
- Place tests in the `tests/` directory
- Run tests with: `pytest tests/`
- Aim for >80% code coverage

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Run tests and linting: `pytest && black src/ && ruff check src/`
6. Commit with a clear message describing the change
7. Push and create a pull request

## PR Guidelines

- **Clear description**: Explain what the PR does and why
- **Tests included**: All new features should have tests
- **Documentation updated**: Update README.md and docstrings as needed
- **Small, focused changes**: One feature or fix per PR
- **Passes CI**: All tests and linting must pass

## Areas for Contribution

We welcome contributions in these areas:

- **Unity Catalog integration**: Register agents as UC catalog objects
- **MCP server support**: Add Model Context Protocol server capabilities
- **Orchestration patterns**: Multi-agent coordination utilities
- **RAG utilities**: Built-in vector search and retrieval patterns
- **Observability**: Logging, metrics, and tracing integrations
- **Documentation**: Examples, guides, and API documentation
- **Testing**: Improve test coverage and test utilities

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for design questions
- Check existing issues and PRs before starting work

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions. This is a professional community focused on building great tools together.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
