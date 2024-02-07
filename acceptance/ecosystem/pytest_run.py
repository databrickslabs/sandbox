import os
import pytest
import requests

class RunReport:
    def pytest_runtest_logreport(self, report: pytest.TestReport):
        package, _, name = report.location
        output = report.caplog
        if output:
            output += "\n"
        output += report.longreprtext
        requests.post(os.environ['REPLY_URL'], json={
            # 'ts':
            'package': package,
            'name': name,
            'pass': report.passed,
            'skip': report.skipped,
            'output': output,
            'elapsed': report.duration,
        })

if __name__ == '__main__':
    pytest.main(['-n', '10'], plugins=[RunReport()])
