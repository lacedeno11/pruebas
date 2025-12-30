# DERCAS-ONCO-XAI V1 Makefile
# Explainable AI Oncology Platform

.PHONY: help up down logs test lint fmt clean install-deps

# Default target
help:
	@echo "DERCAS-ONCO-XAI V1 - Explainable AI Oncology Platform"
	@echo ""
	@echo "Available targets:"
	@echo "  up           - Start all infrastructure and services"
	@echo "  down         - Stop all services and clean up"
	@echo "  logs         - Show logs from all services"
	@echo "  test         - Run all tests (unit, integration, contract)"
	@echo "  lint         - Run linting (ruff, mypy)"
	@echo "  fmt          - Format code (black, ruff)"
	@echo "  clean        - Clean up build artifacts and caches"
	@echo "  install-deps - Install all dependencies"
	@echo "  help         - Show this help message"

# Infrastructure and services
up:
	@echo "Starting DERCAS-ONCO-XAI infrastructure and services..."
	docker-compose -f infra/docker-compose.yml up -d
	@echo "Services started. Check status with 'make logs'"

down:
	@echo "Stopping all services..."
	docker-compose -f infra/docker-compose.yml down -v
	@echo "All services stopped and volumes removed."

logs:
	@echo "Showing logs from all services..."
	docker-compose -f infra/docker-compose.yml logs -f

# Development
install-deps:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "Installing Node.js dependencies for webapp..."
	cd apps/webapp && npm install

# Testing
test:
	@echo "Running all tests..."
	@echo "Running unit tests..."
	python -m pytest packages/ -v --tb=short
	@echo "Running integration tests..."
	python -m pytest apps/ -v --tb=short --integration
	@echo "Running contract tests..."
	python -m pytest tests/contract/ -v --tb=short

# Code quality
lint:
	@echo "Running linting..."
	ruff check .
	mypy packages/ apps/

fmt:
	@echo "Formatting code..."
	black .
	ruff format .

# Cleanup
clean:
	@echo "Cleaning up build artifacts and caches..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

# Service-specific targets
api-gateway:
	@echo "Starting API Gateway..."
	cd apps/api-gateway && python -m uvicorn main:app --reload --port 8000

case-service:
	@echo "Starting Case Service..."
	cd apps/case-service && python -m uvicorn main:app --reload --port 8001

image-service:
	@echo "Starting Image Service..."
	cd apps/image-service && python -m uvicorn main:app --reload --port 8002

inference-service:
	@echo "Starting Inference Service..."
	cd apps/inference-service && python -m uvicorn main:app --reload --port 8003

ehr-service:
	@echo "Starting EHR Service..."
	cd apps/ehr-service && python -m uvicorn main:app --reload --port 8004

graph-service:
	@echo "Starting Graph Service..."
	cd apps/graph-service && python -m uvicorn main:app --reload --port 8005

ontology-admin-service:
	@echo "Starting Ontology Admin Service..."
	cd apps/ontology-admin-service && python -m uvicorn main:app --reload --port 8006

audit-service:
	@echo "Starting Audit Service..."
	cd apps/audit-service && python -m uvicorn main:app --reload --port 8007

webapp:
	@echo "Starting WebApp..."
	cd apps/webapp && npm run dev

# Database migrations
migrate:
	@echo "Running database migrations..."
	cd apps/case-service && alembic upgrade head
	cd apps/image-service && alembic upgrade head
	cd apps/inference-service && alembic upgrade head
	cd apps/ehr-service && alembic upgrade head
	cd apps/graph-service && alembic upgrade head
	cd apps/ontology-admin-service && alembic upgrade head
	cd apps/audit-service && alembic upgrade head

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/healthz || echo "API Gateway: DOWN"
	@curl -f http://localhost:8001/healthz || echo "Case Service: DOWN"
	@curl -f http://localhost:8002/healthz || echo "Image Service: DOWN"
	@curl -f http://localhost:8003/healthz || echo "Inference Service: DOWN"
	@curl -f http://localhost:8004/healthz || echo "EHR Service: DOWN"
	@curl -f http://localhost:8005/healthz || echo "Graph Service: DOWN"
	@curl -f http://localhost:8006/healthz || echo "Ontology Admin Service: DOWN"
	@curl -f http://localhost:8007/healthz || echo "Audit Service: DOWN"
