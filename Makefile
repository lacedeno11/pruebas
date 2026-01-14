# DERCAS-ONCO-XAI Makefile
# Explainable AI Oncology Platform

.PHONY: help up down logs restart clean test lint fmt install-deps build

# Default target
help: ## Show this help message
	@echo "DERCAS-ONCO-XAI - Explainable AI Oncology Platform"
	@echo "=================================================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Infrastructure Management
up: ## Start all services with docker-compose
	@echo "🚀 Starting DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml up -d
	@echo "✅ Infrastructure started. Check logs with 'make logs'"

down: ## Stop all services
	@echo "🛑 Stopping DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml down
	@echo "✅ Infrastructure stopped"

logs: ## Show logs from all services
	docker-compose -f infra/docker-compose.yml logs -f

restart: ## Restart all services
	@echo "🔄 Restarting DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml restart
	@echo "✅ Infrastructure restarted"

clean: ## Clean up containers, volumes, and networks
	@echo "🧹 Cleaning up DERCAS-ONCO-XAI infrastructure..."
	docker-compose -f infra/docker-compose.yml down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup completed"

# Development
install-deps: ## Install Python dependencies for all services
	@echo "📦 Installing dependencies for all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Installing deps for $$service"; \
			cd "$$service" && pip install -e .[dev] && cd ../..; \
		fi; \
	done
	@for package in packages/*/; do \
		if [ -f "$$package/pyproject.toml" ]; then \
			echo "Installing deps for $$package"; \
			cd "$$package" && pip install -e .[dev] && cd ../..; \
		fi; \
	done
	@echo "Installing webapp dependencies..."
	cd apps/webapp && npm install
	@echo "✅ All dependencies installed"

build: ## Build all services
	@echo "🔨 Building all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Building $$service"; \
			cd "$$service" && python -m build && cd ../..; \
		fi; \
	done
	@echo "Building webapp..."
	cd apps/webapp && npm run build
	@echo "✅ All services built"

# Code Quality
lint: ## Run linting on all Python code
	@echo "🔍 Running linting on all Python services..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Linting $$service"; \
			cd "$$service" && ruff check . && mypy . && cd ../..; \
		fi; \
	done
	@for package in packages/*/; do \
		if [ -f "$$package/pyproject.toml" ]; then \
			echo "Linting $$package"; \
			cd "$$package" && ruff check . && mypy . && cd ../..; \
		fi; \
	done
	@echo "Linting webapp..."
	cd apps/webapp && npm run lint
	@echo "✅ Linting completed"

fmt: ## Format all code
	@echo "🎨 Formatting all Python code..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Formatting $$service"; \
			cd "$$service" && black . && ruff check --fix . && cd ../..; \
		fi; \
	done
	@for package in packages/*/; do \
		if [ -f "$$package/pyproject.toml" ]; then \
			echo "Formatting $$package"; \
			cd "$$package" && black . && ruff check --fix . && cd ../..; \
		fi; \
	done
	@echo "Formatting webapp..."
	cd apps/webapp && npm run lint:fix
	@echo "✅ Formatting completed"

# Testing
test: ## Run all tests
	@echo "🧪 Running tests for all services..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ]; then \
			echo "Testing $$service"; \
			cd "$$service" && python -m pytest && cd ../..; \
		fi; \
	done
	@for package in packages/*/; do \
		if [ -f "$$package/pyproject.toml" ]; then \
			echo "Testing $$package"; \
			cd "$$package" && python -m pytest && cd ../..; \
		fi; \
	done
	@echo "✅ All tests completed"

# Health Checks
health: ## Check health of all services
	@echo "🏥 Checking health of all services..."
	@echo "PostgreSQL:" && curl -f http://localhost:5432 || echo "❌ PostgreSQL not responding"
	@echo "RabbitMQ:" && curl -f http://localhost:15672 || echo "❌ RabbitMQ not responding"
	@echo "Redis:" && redis-cli ping || echo "❌ Redis not responding"
	@echo "MinIO:" && curl -f http://localhost:9000/minio/health/live || echo "❌ MinIO not responding"
	@echo "Keycloak:" && curl -f http://localhost:8080/auth/realms/dercas || echo "❌ Keycloak not responding"
	@echo "Fuseki:" && curl -f http://localhost:3030 || echo "❌ Fuseki not responding"
	@echo "Jaeger:" && curl -f http://localhost:16686 || echo "❌ Jaeger not responding"
	@echo "Prometheus:" && curl -f http://localhost:9090 || echo "❌ Prometheus not responding"

# Quick Start
quickstart: ## Quick start for development (up + install-deps)
	@echo "🚀 Quick start for DERCAS-ONCO-XAI development..."
	make up
	sleep 30
	make install-deps
	@echo "✅ Quick start completed! Services are running and dependencies installed."
	@echo "📖 Check README.md for next steps."

# Environment
env-example: ## Copy .env.example to .env
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
		echo "📝 Please edit .env with your configuration"; \
	else \
		echo "⚠️  .env already exists"; \
	fi
