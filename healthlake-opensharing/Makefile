.PHONY: install test deploy consumer verify destroy

install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

test:
	.venv/bin/python -m pytest -q

deploy:
	bash scripts/deploy.sh

consumer:
	bash scripts/configure-consumer.sh

verify:
	bash scripts/verify.sh

destroy:
	bash scripts/destroy.sh
