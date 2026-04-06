# Purple Team GPT - Makefile
# Common commands for development and deployment

.PHONY: help dev start stop build clean test lint health logs backup restore

# Default target
help:
	@echo "Purple Team GPT - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Development:"
	@echo "  make dev        Start development environment"
	@echo "  make dev-build  Build and start development environment"
	@echo "  make dev-clean  Clean and rebuild development environment"
	@echo ""
	@echo "Production:"
	@echo "  make start      Start production environment"
	@echo "  make stop       Stop all services"
	@echo "  make health     Run health checks"
	@echo ""
	@echo "Operations:"
	@echo "  make build      Build all Docker images"
	@echo "  make clean      Remove containers and volumes"
	@echo "  make logs       View container logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test       Run all tests"
	@echo "  make lint       Run linters"
	@echo "  make coverage   Run tests with coverage"
	@echo ""
	@echo "Backup:"
	@echo "  make backup     Create backup"
	@echo "  make restore    Restore from latest backup"

# Development
dev:
	@./dev.sh

dev-build:
	@./dev.sh --build

dev-clean:
	@./dev.sh --clean

# Production
start:
	@./start.sh

stop:
	@./scripts/stop.sh

health:
	@./scripts/health-check.sh

# Docker
build:
	@docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

clean:
	@docker-compose down -v --remove-orphans
	@docker system prune -f

logs:
	@docker-compose logs -f

# Testing
test:
	@docker-compose exec backend pytest tests/ -v

lint:
	@docker-compose exec backend ruff check src/
	@docker-compose exec backend black --check src/

coverage:
	@docker-compose exec backend pytest tests/ --cov=src/purple_team_gpt --cov-report=html

# Backup
backup:
	@./scripts/backup.sh

restore:
	@./scripts/restore.sh

# CI/CD
ci:
	@echo "Running CI pipeline locally..."
	@pip install ruff black mypy pytest pytest-cov
	@ruff check src/ tests/
	@black --check src/ tests/
	@mypy src/
	@pytest tests/ -v