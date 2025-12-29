.PHONY: up down logs test lint fmt build clean install migrate

# Default environment file
ENV_FILE ?= .env

# Docker Compose commands
DOCKER_COMPOSE = docker compose -f infra/docker-compose.yml --env-file $(ENV_FILE)

# Colors for output
GREEN = \033[0;32m
NC = \033[0m

## Infrastructure

up: ## Start all services
	@echo "$(GREEN)Starting infrastructure...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started. Use 'make logs' to view logs.$(NC)"

down: ## Stop all services
	@echo "$(GREEN)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

logs-service: ## View logs for specific service (usage: make logs-service SERVICE=case-service)
	$(DOCKER_COMPOSE) logs -f $(SERVICE)

ps: ## List running services
	$(DOCKER_COMPOSE) ps

build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

clean: ## Remove all containers, volumes, and images
	$(DOCKER_COMPOSE) down -v --rmi local
	docker system prune -f

## Development

install: ## Install Python dependencies for all services
	@echo "$(GREEN)Installing dependencies...$(NC)"
	cd packages/common && pip install -e .
	cd packages/event-contracts && pip install -e .
	cd packages/langgraph-workflows && pip install -e .
	cd apps/api-gateway && pip install -e .
	cd apps/case-service && pip install -e .
	cd apps/image-service && pip install -e .
	cd apps/inference-service && pip install -e .
	cd apps/ehr-service && pip install -e .
	cd apps/graph-service && pip install -e .
	cd apps/ontology-admin-service && pip install -e .
	cd apps/audit-service && pip install -e .

install-webapp: ## Install webapp dependencies
	cd apps/webapp && npm install

## Database

migrate: ## Run database migrations for all services
	@echo "$(GREEN)Running migrations...$(NC)"
	cd apps/case-service && alembic upgrade head
	cd apps/image-service && alembic upgrade head
	cd apps/inference-service && alembic upgrade head
	cd apps/ehr-service && alembic upgrade head
	cd apps/graph-service && alembic upgrade head
	cd apps/ontology-admin-service && alembic upgrade head
	cd apps/audit-service && alembic upgrade head

migrate-down: ## Rollback database migrations
	cd apps/case-service && alembic downgrade -1
	cd apps/image-service && alembic downgrade -1
	cd apps/inference-service && alembic downgrade -1
	cd apps/ehr-service && alembic downgrade -1
	cd apps/graph-service && alembic downgrade -1
	cd apps/ontology-admin-service && alembic downgrade -1
	cd apps/audit-service && alembic downgrade -1

## Testing

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	cd packages/common && pytest tests/ -v
	cd packages/event-contracts && pytest tests/ -v
	cd apps/case-service && pytest tests/ -v
	cd apps/image-service && pytest tests/ -v
	cd apps/inference-service && pytest tests/ -v
	cd apps/ehr-service && pytest tests/ -v
	cd apps/graph-service && pytest tests/ -v
	cd apps/ontology-admin-service && pytest tests/ -v
	cd apps/audit-service && pytest tests/ -v

test-service: ## Run tests for specific service (usage: make test-service SERVICE=case-service)
	cd apps/$(SERVICE) && pytest tests/ -v

test-coverage: ## Run tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest --cov=apps --cov=packages --cov-report=html --cov-report=term

## Code Quality

lint: ## Run linters
	@echo "$(GREEN)Running linters...$(NC)"
	ruff check packages/ apps/
	mypy packages/ apps/ --ignore-missing-imports

fmt: ## Format code
	@echo "$(GREEN)Formatting code...$(NC)"
	ruff check --fix packages/ apps/
	black packages/ apps/

fmt-check: ## Check code formatting
	black --check packages/ apps/

## OpenAPI

openapi-export: ## Export OpenAPI specs
	@echo "$(GREEN)Exporting OpenAPI specs...$(NC)"
	@mkdir -p docs/openapi
	curl -s http://localhost:8000/openapi.json > docs/openapi/api-gateway.json || true
	curl -s http://localhost:8001/openapi.json > docs/openapi/case-service.json || true
	curl -s http://localhost:8002/openapi.json > docs/openapi/image-service.json || true
	curl -s http://localhost:8003/openapi.json > docs/openapi/inference-service.json || true
	curl -s http://localhost:8004/openapi.json > docs/openapi/ehr-service.json || true
	curl -s http://localhost:8005/openapi.json > docs/openapi/graph-service.json || true
	curl -s http://localhost:8006/openapi.json > docs/openapi/ontology-admin-service.json || true
	curl -s http://localhost:8007/openapi.json > docs/openapi/audit-service.json || true

## Help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
