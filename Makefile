PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn

.PHONY: install test run lint

install:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTEST)

run:
	$(UVICORN) app.main:app --host $${PIVED_HOST:-0.0.0.0} --port $${PIVED_PORT:-8080}

lint:
	$(PYTHON) -m compileall app tests
