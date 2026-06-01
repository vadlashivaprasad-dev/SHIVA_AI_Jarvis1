.PHONY: help install dev lint format test test-cov clean docs up down

PYTHON := python3
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate || . $(VENV)/Scripts/activate

help:
	@echo "ShivaAI Jarvis Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make install          Install all dependencies"
	@echo "  make install-dev      Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Run development server"
	@echo "  make dev-frontend     Run frontend dev server"
	@echo "  make dev-backend      Run backend dev server"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (ruff, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo "  make format-check     Check formatting without changes"
	@echo "  make pre-commit       Run pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-cov         Run tests with coverage"
	@echo "  make test-watch       Run tests in watch mode"
	@echo ""
	@echo "Docker:"
	@echo "  make up               Start Docker services"
	@echo "  make down             Stop Docker services"
	@echo "  make build            Build Docker images"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Remove build artifacts"
	@echo "  make docs             Generate documentation"
	@echo "  make migrations       Create database migrations"

install:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip setuptools wheel
	$(ACTIVATE) && pip install -r requirements.txt

install-dev: install
	$(ACTIVATE) && pip install -r requirements-dev.txt
	$(ACTIVATE) && pre-commit install

dev: dev-backend dev-frontend

dev-backend:
	cd services/gateway && \
	$(ACTIVATE) && \
	ENVIRONMENT=development \
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd apps/web && \
	npm install && \
	npm run dev

lint:
	$(ACTIVATE) && ruff check services tests
	$(ACTIVATE) && mypy services

format:
	$(ACTIVATE) && black services apps/web
	$(ACTIVATE) && isort services apps/web
	$(ACTIVATE) && ruff check --fix services tests

format-check:
	$(ACTIVATE) && black --check services apps/web
	$(ACTIVATE) && isort --check-only services apps/web
	$(ACTIVATE) && ruff check services tests

pre-commit:
	$(ACTIVATE) && pre-commit run --all-files

test:
	$(ACTIVATE) && pytest tests -v

test-unit:
	$(ACTIVATE) && pytest tests -v -m "not integration"

test-cov:
	$(ACTIVATE) && pytest tests \
		--cov=services \
		--cov-report=html \
		--cov-report=term-missing \
		-v

test-watch:
	$(ACTIVATE) && ptw tests

up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker-compose logs

down:
	docker-compose down

build:
	docker-compose build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf build dist *.egg-info

docs:
	$(ACTIVATE) && mkdocs build
	@echo "Documentation built in site/"

migrations:
	cd services/gateway && \
	$(ACTIVATE) && \
	alembic revision --autogenerate -m "Auto migration"

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f gateway

logs-db:
	docker-compose logs -f postgresql
