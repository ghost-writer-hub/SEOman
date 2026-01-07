.PHONY: help build up down restart logs clean install-backend install-frontend test-backend test-frontend migrate db-shell

help:
	@echo "Available commands:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs from all services"
	@echo "  make logs-backend   - View backend logs"
	@echo "  make logs-frontend  - View frontend logs"
	@echo "  make logs-worker    - View worker logs"
	@echo "  make clean          - Remove all containers, volumes, and images"
	@echo "  make install-backend - Install backend dependencies (local dev)"
	@echo "  make install-frontend - Install frontend dependencies (local dev)"
	@echo "  make test-backend   - Run backend tests"
	@echo "  make test-frontend  - Run frontend tests"
	@echo "  make migrate        - Run database migrations"
	@echo "  make db-shell       - Access database shell"
	@echo "  make redis-cli      - Access Redis CLI"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-worker:
	docker-compose logs -f worker

clean:
	docker-compose down -v --remove-orphans
	docker system prune -af

install-backend:
	cd backend && python -m venv .venv
	cd backend && .venv/bin/pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

test-backend:
	cd backend && .venv/bin/pytest

test-frontend:
	cd frontend && npm test

migrate:
	docker-compose exec backend alembic upgrade head

db-shell:
	docker-compose exec postgres psql -U seoman -d seoman

redis-cli:
	docker-compose exec redis redis-cli -a ${REDIS_PASSWORD}
