.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate

help:
	@echo "Available commands:"
	@echo "  install      - Install dependencies"
	@echo "  dev          - Run development server"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linters"
	@echo "  format       - Format code"
	@echo "  clean        - Clean cache files"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up    - Start Docker Compose services"
	@echo "  docker-down  - Stop Docker Compose services"
	@echo "  migrate      - Run database migrations"

install:
	poetry install

dev:
	poetry run uvicorn app.main:app --host 0.0.0.0 --port 8007 --reload

test:
	poetry run pytest

lint:
	poetry run ruff check app/
	poetry run mypy app/

format:
	poetry run black app/
	poetry run ruff check --fix app/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:
	docker build -t audit-service .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

migrate:
	poetry run alembic upgrade head

migrate-create:
	poetry run alembic revision --autogenerate -m "$(name)"
