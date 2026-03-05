#!/usr/bin/env python3
"""Simple test runner script."""

import subprocess
import sys


def run_tests(test_path: str = 'tests/', coverage: bool = False, verbose: bool = True):
    """Run tests with pytest."""
    cmd = ['uv', 'run', 'python', '-m', 'pytest']

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend(['--cov=server', '--cov-report=html', '--cov-report=term'])

    cmd.append(test_path)

    print(f'Running: {" ".join(cmd)}')
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = 'tests/'

    coverage = '--coverage' in sys.argv
    exit_code = run_tests(test_path, coverage)
    sys.exit(exit_code)
