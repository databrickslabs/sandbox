import os
import pytest

class RunOne:
    def pytest_collection_modifyitems(self, items: list[pytest.Item], config: pytest.Config):
        deselected = []
        remaining = []
        for item in items:
            # Otherwise we have ERROR: Wrong expression passed to '-k': 
            #   test_uploading_notebooks_get_correct_urls[py-# Databricks notebook source]: 
            #   at column 46: unexpected character "#"
            # See https://github.com/pytest-dev/pytest/issues/12018
            if item.name != os.environ['TEST_FILTER']:
                deselected.append(item)
                continue
            remaining.append(item)
        if not deselected:
            return
        config.hook.pytest_deselected(items=deselected)
        items[:] = remaining

if __name__ == '__main__':
    pytest.main([
        "-n0",                                      # no xdist, single-threaded
		"--timeout", "1800",                        # fail in 30 minutes
		"--log-cli-level", "DEBUG",                 # log everything
		"--log-level", "DEBUG",                     # log everything
		"--log-disable", "urllib3.connectionpool",  # except noise
		"--log-format", "%(asctime)s %(levelname)s [%(name)s] %(message)s",
		"--log-date-format", "%H:%M",
		"--no-header",
		"--no-summary",
    ], plugins=[RunOne()])
