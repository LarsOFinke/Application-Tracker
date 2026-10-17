.PHONY: help dev test quality compile

help:
	@echo 'make dev      Run Application Tracker from source'
	@echo 'make test     Run the Python tests'
	@echo 'make quality  Run Ruff and Python tests'
	@echo 'make compile  Build dist/linux/ApplicationTracker-<arch>.AppImage on Linux'

dev:
	bash scripts/dev.sh

test:
	$${PYTHON_BIN:-.venv/bin/python} -m pytest -q

quality:
	$${PYTHON_BIN:-.venv/bin/python} -m ruff check src tests
	$${PYTHON_BIN:-.venv/bin/python} -m pytest -q

compile:
	bash scripts/build-linux.sh
