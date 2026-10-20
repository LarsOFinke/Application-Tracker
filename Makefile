.PHONY: help dev test quality wheel compile

help:
	@echo 'make dev      Run Application Tracker from source'
	@echo 'make test     Run the Python tests'
	@echo 'make quality  Run Ruff and Python tests'
	@echo 'make wheel    Build dist/wheels/application_tracker-<version>-*.whl'
	@echo 'make compile  Build dist/linux/ApplicationTracker-<arch>.AppImage on Linux'

dev:
	bash scripts/dev.sh

test:
	$${PYTHON_BIN:-.venv/bin/python} -m pytest -q

quality:
	$${PYTHON_BIN:-.venv/bin/python} -m ruff check src tests
	$${PYTHON_BIN:-.venv/bin/python} -m pytest -q

wheel:
	bash scripts/build-wheel.sh

compile:
	bash scripts/build-linux.sh
