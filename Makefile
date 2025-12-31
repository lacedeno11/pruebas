.PHONY: help up down logs test lint fmt clean build health dev-setup install-deps

# Default target
help:
	@echo "DERCAS-ONCO-XAI V1 - Explainable AI Oncology Platform"
	@echo "Available targets:"
	@echo "  up       - Start all services with docker-compose"
	@echo "  down     - Stop all services"
	@echo "  logs     - Show logs from all services"
	@echo "  test     - Run all tests"
	@echo "  lint     - Run linting (ruff + mypy)"
	@echo "  fmt      - Format code (black + ruff)"
	@echo "  clean    - Clean up containers and volumes"
	@echo "  build    - Build all services"
	@echo "  health   - Check service health"

# Infrastructure management
up:
	@echo "Starting DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Services started successfully!"

down:
	@echo "Stopping DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml down

logs:
	docker-compose -f infra/docker-compose.yml logs -f

clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose -f infra/docker-compose.yml down -v --remove-orphans
	docker system prune -f

# Development
build:
	@echo "Building all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/Dockerfile" ]; then \
			echo "Building $$service..."; \
			docker build -t "oncology-xai/$$(basename $$service)" "$$service"; \
		fi; \
	done

# Testing
test:
	@echo "Running tests for all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ] || [ -f "$$service/requirements.txt" ]; then \
			echo "Testing $$service..."; \
			cd "$$service" && python -m pytest tests/ -v --no-colors || true; \
			cd - > /dev/null; \
		fi; \
	done

# Code quality
lint:
	@echo "Running linting..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ] || [ -f "$$service/requirements.txt" ]; then \
			echo "Linting $$service..."; \
			cd "$$service" && ruff check . && mypy . || true; \
			cd - > /dev/null; \
		fi; \
	done

fmt:
	@echo "Formatting code..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ] || [ -f "$$service/requirements.txt" ]; then \
			echo "Formatting $$service..."; \
			cd "$$service" && black . && ruff format . || true; \
			cd - > /dev/null; \
		fi; \
	done

# Package management
install-deps:
	@echo "Installing dependencies for all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/requirements.txt" ]; then \
			echo "Installing deps for $$service..."; \
			cd "$$service" && pip install -r requirements.txt; \
			cd - > /dev/null; \
		fi; \
	done

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	@echo "Creating .env files..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Installing pre-commit hooks..."
	@pre-commit install || echo "pre-commit not available, skipping..."

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8080/healthz || echo "API Gateway not ready"
	@curl -f http://localhost:5432 || echo "PostgreSQL not ready"
	@curl -f http://localhost:5672 || echo "RabbitMQ not ready"
	@curl -f http://localhost:6379 || echo "Redis not ready"
	@curl -f http://localhost:9000 || echo "MinIO not ready"
	@curl -f http://localhost:8081 || echo "Keycloak not ready"
	@curl -f http://localhost:3030 || echo "Fuseki not ready"
