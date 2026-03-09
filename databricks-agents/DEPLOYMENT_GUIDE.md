# Databricks Labs Sandbox Deployment Guide

## Overview

This framework is ready for deployment to the [Databricks Labs Sandbox](https://github.com/databrickslabs/sandbox) repository. The sandbox is the perfect home for this project as it's:

- **Early-stage but valuable**: Framework is functional and provides immediate value
- **Community-driven**: Open for contributions and iteration
- **Low barrier to adoption**: Simple API that users can start with immediately
- **Building block for future labs projects**: Foundation for multi-agent systems

## Repository Structure

```
databricks-agents/
├── src/databricks_agents/        # Core framework
│   ├── core/                      # @app_agent decorator, agent request/response types
│   ├── discovery/                 # Agent discovery, A2A client
│   ├── mcp/                       # MCP server, UC Functions
│   ├── registry/                  # Unity Catalog integration
│   └── orchestration/             # (Future: multi-agent patterns)
├── examples/                      # Complete working examples
├── tests/                         # Test suite
├── docs/                          # MkDocs documentation
├── .github/workflows/             # CI/CD pipelines
├── README.md                      # Main documentation
├── CONTRIBUTING.md                # Contribution guidelines
├── LICENSE                        # Apache 2.0
└── pyproject.toml                 # Package configuration
```

## Pre-Deployment Checklist

### ✅ Completed

- [x] Core framework implementation (@app_agent decorator, discovery)
- [x] Agent card endpoints and protocol
- [x] Workspace agent discovery
- [x] Example applications
- [x] Test suite foundation
- [x] CI/CD workflows (test, publish, docs)
- [x] Documentation structure (MkDocs)
- [x] README and CONTRIBUTING guides
- [x] Apache 2.0 LICENSE

### 🔄 Recommended Before Launch

1. **Additional Tests**
   - Integration tests with real Databricks Apps
   - UC registration end-to-end tests
   - MCP server protocol compliance tests

2. **Documentation Completion**
   - Finish all docs/ guide pages
   - Add API reference with mkdocstrings
   - Video walkthrough or GIF demos

3. **Example Expansion**
   - Multi-agent orchestration example
   - RAG agent with vector search
   - Data processing pipeline agent

4. **Community Prep**
   - Create GitHub issue templates
   - Set up discussion categories
   - Add CODE_OF_CONDUCT.md

## Deployment Steps

### 1. Fork to databrickslabs/sandbox

```bash
# Clone this repository
git clone <current-location>

# Add sandbox as remote
cd databricks-agents
git remote add sandbox git@github.com:databrickslabs/sandbox.git

# Create feature branch
git checkout -b databricks-agents-framework

# Push to sandbox
git push sandbox databricks-agents-framework
```

### 2. Create PR to sandbox/main

**PR Title**: Add databricks-agents framework for building discoverable agents

**PR Description**:
```markdown
## Summary

Adds `databricks-agents`, a lightweight Python framework for building discoverable AI agents on Databricks Apps. This framework makes it trivial to turn any Databricks App into a standards-compliant agent with auto-generated A2A protocol endpoints.

## What It Does

- **5 lines to create an agent**: Simple `@app_agent` decorator
- **Auto-generates protocol endpoints**: `/.well-known/agent.json`, OIDC config, health checks
- **Workspace discovery**: Find and communicate with agents across the workspace
- **Plain FastAPI support**: Use `add_agent_card()` helper for full control
- **Agent communication**: A2A protocol for standardized agent-to-agent interaction

## Key Files

- `src/databricks_agents/core/decorator.py` - @app_agent decorator
- `src/databricks_agents/core/types.py` - AgentRequest, AgentResponse types
- `src/databricks_agents/discovery/` - Agent discovery and A2A client
- `src/databricks_agents/registry/` - Unity Catalog integration
- `src/databricks_agents/mcp/` - MCP server support
- `examples/` - Complete working examples
- `tests/` - Test suite

## Example Usage

```python
from databricks_agents import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="customer_research",
    description="Research customers",
    capabilities=["search", "analysis"],
)
async def customer_research(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"Processing: {request.last_user_message}")
```

## Testing

All tests pass:
```bash
pytest tests/ -v
```

## Documentation

Full documentation at `docs/` (deployed via GitHub Pages)

## Related Issues

Addresses the need for standardized agent building on Databricks Apps.
```

### 3. Post-Merge Actions

1. **Set up PyPI publishing**
   - Create PyPI account for databricks-labs
   - Add `PYPI_API_TOKEN` to repo secrets
   - Publish first release (0.1.0)

2. **Enable GitHub Pages**
   - Go to Settings → Pages
   - Source: GitHub Actions
   - Deploy docs workflow will handle builds

3. **Community Engagement**
   - Announce in Databricks Community forums
   - Share in relevant Slack channels
   - Blog post on Databricks Labs blog

4. **Iterate Based on Feedback**
   - Monitor issues and discussions
   - Prioritize community requests
   - Release patches and minor versions

## Long-Term Vision

### Phase 1: Foundation (Current)
- ✅ Core framework
- ✅ Basic discovery
- ✅ UC integration
- ✅ MCP support

### Phase 2: Enrichment (Next 3 months)
- Advanced orchestration patterns
- RAG utilities (vector search, retrieval)
- Observability integrations
- More UC Functions examples

### Phase 3: Maturity (6-12 months)
- Graduate to full databrickslabs repo
- Native UC AGENT type support (when available)
- Multi-agent coordination primitives
- Production deployment patterns

## Success Metrics

Track these metrics to assess adoption:

- **GitHub stars**: Community interest
- **PyPI downloads**: Actual usage
- **Issues/PRs**: Community engagement
- **Documentation views**: Learning curve
- **Example forks**: Real-world adoption

Target for sandbox graduation (move to full repo):
- 100+ stars
- 1000+ PyPI downloads/month
- 10+ contributors
- 5+ community-contributed examples

## Contact

Framework developed as part of the multi-agent registry project.

Questions? Open an issue or start a discussion in the sandbox repo.
