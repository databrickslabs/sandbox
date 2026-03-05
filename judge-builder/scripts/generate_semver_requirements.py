#!/usr/bin/env python3
"""Generate requirements.txt with semantic versioning ranges from pyproject.toml.

This script helps avoid conflicts with pre-installed packages in Databricks Apps.
"""

import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        # Fallback to manual parsing if no toml library available
        tomllib = None  # type: ignore


def parse_dependencies_manual(content):
    """Manually parse dependencies from pyproject.toml content."""
    dependencies = []
    in_dependencies = False

    for line in content.split('\n'):
        line = line.strip()
        if line == 'dependencies = [':
            in_dependencies = True
            continue
        elif in_dependencies and line == ']':
            break
        elif in_dependencies and line.startswith('"') and line.endswith('",'):
            # Extract dependency string
            dep = line[1:-2]  # Remove quotes and comma
            dependencies.append(dep)
        elif in_dependencies and line.startswith('"') and line.endswith('"'):
            # Last dependency without comma
            dep = line[1:-1]  # Remove quotes
            dependencies.append(dep)

    return dependencies


def write_requirements_file(filename, deps, description):
    """Write a requirements file with the given dependencies."""
    with open(filename, 'w') as f:
        f.write(f'# Generated from pyproject.toml - {description}\n')
        f.write('# Avoids editable installs and hash conflicts\n\n')

        for dep in deps:
            f.write(f'{dep}\n')


def generate_semver_requirements():
    """Extract dependencies from pyproject.toml and write requirements files."""
    # Read pyproject.toml
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        print('Error: pyproject.toml not found', file=sys.stderr)
        sys.exit(1)

    # Try to parse with tomllib, fallback to manual parsing
    if tomllib:
        with open(pyproject_path, 'rb') as f:
            pyproject = tomllib.load(f)
        dependencies = pyproject.get('project', {}).get('dependencies', [])
        dev_dependencies = (
            pyproject.get('project', {}).get('optional-dependencies', {}).get('dev', [])
        )
        uv_sources = pyproject.get('tool', {}).get('uv', {}).get('sources', {})
    else:
        # Manual parsing fallback
        with open(pyproject_path, 'r') as f:
            content = f.read()
        dependencies = parse_dependencies_manual(content)
        dev_dependencies = []  # Manual parsing doesn't support dev deps yet
        uv_sources = {}

    if not dependencies:
        print('Warning: No production dependencies found in pyproject.toml', file=sys.stderr)

    # Process dependencies to handle custom sources
    def process_deps(deps):
        processed = []
        for dep in deps:
            # Check if this dependency has a custom source (wheel URL)
            dep_name = dep.split('>=')[0].split('==')[0].split('~=')[0].strip()
            if dep_name in uv_sources and 'url' in uv_sources[dep_name]:
                # Use the wheel URL instead of the package name
                processed.append(uv_sources[dep_name]['url'])
            else:
                # Write regular dependency
                processed.append(dep)
        return processed

    # Process both production and dev dependencies
    prod_deps = process_deps(dependencies)
    dev_deps = process_deps(dev_dependencies)

    # Write requirements.txt (production only)
    write_requirements_file(
        'requirements.txt', prod_deps, 'Production dependencies for Databricks Apps deployment'
    )

    # Write dev-requirements.txt (dev dependencies)
    if dev_deps:
        write_requirements_file('dev-requirements.txt', dev_deps, 'Development dependencies')

    print(f'Generated requirements.txt with {len(prod_deps)} production dependencies')
    if dev_deps:
        print(f'Generated dev-requirements.txt with {len(dev_deps)} development dependencies')


if __name__ == '__main__':
    generate_semver_requirements()
