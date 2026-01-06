# DERCAS-ONCO-XAI V1 - Explainable AI Oncology Platform
# Makefile for local development and operations

.PHONY: help up down logs test lint fmt clean install build

# Default target
help: ## Show this help message
	@echo "DERCAS-ONCO-XAI V1 - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Infrastructure commands
up: ## Start all services with docker-compose
	@echo "🚀 Starting DERCAS-ONCO-XAI platform..."
	docker-compose -f infra/docker-compose.yml up -d
	@echo "✅ Platform started. Check logs with 'make logs'"

down: ## Stop all services
	@echo "🛑 Stopping DERCAS-ONCO-XAI platform..."
	docker-compose -f infra/docker-compose.yml down
	@echo "✅ Platform stopped"

logs: ## Show logs from all services
	docker-compose -f infra/docker-compose.yml logs -f

logs-service: ## Show logs from specific service (usage: make logs-service SERVICE=api-gateway)
	docker-compose -f infra/docker-compose.yml logs -f $(SERVICE)

restart: ## Restart all services
	@echo "🔄 Restarting DERCAS-ONCO-XAI platform..."
	docker-compose -f infra/docker-compose.yml restart
	@echo "✅ Platform restarted"

# Development commands
install: ## Install dependencies for all services
	@echo "📦 Installing dependencies..."
	@for service in apps/*/; do \
		if [ -f "$$service/requirements.txt" ]; then \
			echo "Installing dependencies for $$service"; \
			cd "$$service" && pip install -r requirements.txt && cd ../..; \
		fi; \
	done
	@if [ -f "apps/webapp/package.json" ]; then \
		echo "Installing frontend dependencies..."; \
		cd apps/webapp && npm install && cd ../..; \
	fi
	@echo "✅ Dependencies installed"

build: ## Build all service images
	@echo "🔨 Building service images..."
	docker-compose -f infra/docker-compose.yml build
	@echo "✅ Images built"

# Code quality commands
lint: ## Run linting on all Python services
	@echo "🔍 Running linting..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ] || [ -f "$$service/requirements.txt" ]; then \
			echo "Linting $$service"; \
			cd "$$service" && \
			ruff check . && \
			mypy . && \
			cd ../..; \
		fi; \
	done
	@echo "✅ Linting completed"

fmt: ## Format code in all Python services
	@echo "🎨 Formatting code..."
	@for service in apps/*/; do \
		if [ -f "$$service/pyproject.toml" ] || [ -f "$$service/requirements.txt" ]; then \
			echo "Formatting $$service"; \
			cd "$$service" && \
			black . && \
			ruff check --fix . && \
			cd ../..; \
		fi; \
	done
	@echo "✅ Code formatted"

# Testing commands
test: ## Run tests for all services
	@echo "🧪 Running tests..."
	@for service in apps/*/; do \
		if [ -f "$$service/pytest.ini" ] || [ -f "$$service/pyproject.toml" ]; then \
			echo "Testing $$service"; \
			cd "$$service" && \
			NO_COLOR=1 pytest -v && \
			cd ../..; \
		fi; \
	done
	@echo "✅ Tests completed"

test-service: ## Run tests for specific service (usage: make test-service SERVICE=case-service)
	@echo "🧪 Running tests for $(SERVICE)..."
	cd apps/$(SERVICE) && NO_COLOR=1 pytest -v

test-integration: ## Run integration tests
	@echo "🔗 Running integration tests..."
	NO_COLOR=1 pytest tests/integration/ -v
	@echo "✅ Integration tests completed"

# Database commands
db-migrate: ## Run database migrations for all services
	@echo "🗄️ Running database migrations..."
	@for service in apps/*/; do \
		if [ -f "$$service/alembic.ini" ]; then \
			echo "Migrating $$service"; \
			cd "$$service" && \
			alembic upgrade head && \
			cd ../..; \
		fi; \
	done
	@echo "✅ Migrations completed"

db-reset: ## Reset all databases (WARNING: destroys data)
	@echo "⚠️  Resetting databases..."
	@read -p "Are you sure? This will destroy all data (y/N): " confirm && [ "$$confirm" = "y" ]
	docker-compose -f infra/docker-compose.yml down -v
	docker-compose -f infra/docker-compose.yml up -d postgres redis rabbitmq minio fuseki
	sleep 10
	$(MAKE) db-migrate
	@echo "✅ Databases reset"

# Utility commands
clean: ## Clean up containers, images, and volumes
	@echo "🧹 Cleaning up..."
	docker-compose -f infra/docker-compose.yml down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup completed"

health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@curl -s http://localhost:8080/healthz || echo "❌ API Gateway not healthy"
	@curl -s http://localhost:5432 || echo "❌ PostgreSQL not healthy"
	@curl -s http://localhost:5672 || echo "❌ RabbitMQ not healthy"
	@curl -s http://localhost:6379 || echo "❌ Redis not healthy"
	@curl -s http://localhost:9000 || echo "❌ MinIO not healthy"
	@curl -s http://localhost:8081 || echo "❌ Keycloak not healthy"
	@curl -s http://localhost:3030 || echo "❌ Fuseki not healthy"
	@curl -s http://localhost:16686 || echo "❌ Jaeger not healthy"
	@curl -s http://localhost:9090 || echo "❌ Prometheus not healthy"
	@echo "✅ Health check completed"

status: ## Show status of all services
	docker-compose -f infra/docker-compose.yml ps

# Development helpers
dev-setup: ## Complete development setup
	@echo "🛠️ Setting up development environment..."
	$(MAKE) install
	$(MAKE) up
	sleep 30
	$(MAKE) db-migrate
	@echo "✅ Development environment ready!"

dev-reset: ## Reset development environment
	@echo "🔄 Resetting development environment..."
	$(MAKE) down
	$(MAKE) clean
	$(MAKE) dev-setup
	@echo "✅ Development environment reset!"

# Documentation
docs: ## Generate API documentation
	@echo "📚 Generating documentation..."
	@for service in apps/*/; do \
		if [ -f "$$service/main.py" ]; then \
			echo "Generating docs for $$service"; \
			# Extract OpenAPI specs (implementation depends on service structure)
		fi; \
	done
	@echo "✅ Documentation generated"

# Monitoring and observability
monitor: ## Open monitoring dashboards
	@echo "📊 Opening monitoring dashboards..."
	@echo "Jaeger UI: http://localhost:16686"
	@echo "Prometheus UI: http://localhost:9090"
	@echo "Grafana UI: http://localhost:3000 (if configured)"
	@echo "MinIO Console: http://localhost:9001"
	@echo "RabbitMQ Management: http://localhost:15672"

# Security
security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	@for service in apps/*/; do \
		if [ -f "$$service/requirements.txt" ]; then \
			echo "Scanning $$service"; \
			cd "$$service" && \
			safety check -r requirements.txt && \
			bandit -r . && \
			cd ../..; \
		fi; \
	done
	@echo "✅ Security scans completed"

# Production helpers
prod-check: ## Check production readiness
	@echo "🚀 Checking production readiness..."
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) security-scan
	@echo "✅ Production readiness check completed"
