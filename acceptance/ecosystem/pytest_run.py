import os
import pytest
import requests
import collections


class RunReport:
    _logs = collections.defaultdict(list)
    _failed = collections.defaultdict(bool)
    _skipped = collections.defaultdict(bool)
    _duration = collections.defaultdict(float)

    def pytest_runtest_logfinish(self, location):
        package, _, name = location
        requests.post(os.environ['REPLY_URL'], json={
            'package': package,
            'name': name,
            'pass': not self._failed[location],
            'skip': self._skipped[location],
            'output': "\n".join(self._logs[location]),
            'elapsed': self._duration[location],
        })

    def pytest_runtest_logreport(self, report: pytest.TestReport):
        if report.caplog:
            self._logs[report.location].append(report.caplog)
        if report.longreprtext:
            # longrepr can be either a tuple or an exception. 
            # we need to make it more friendly to one-line repr in CLI
            self._logs[report.location].append(report.longreprtext)
        if not report.passed:
            self._failed[report.location] = True
        if report.skipped:
            self._skipped[report.location] = True
        self._duration[report.location] += report.duration


if __name__ == '__main__':
    pytest.main(['-n', '10'], plugins=[RunReport()])
