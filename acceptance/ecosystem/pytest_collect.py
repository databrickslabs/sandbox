import os
import pytest
import requests

class TestNames:
    def pytest_sessionfinish(self, session: pytest.Session):
        names = []
        for item in session.items:
            _, _, name = item.location
            names.append(name)
        requests.post(os.environ['REPLY_URL'], json=names)

if __name__ == '__main__':
    pytest.main(['--collect-only'], plugins=[TestNames()])
