.PHONY: help build up down logs test clean dev-setup health setup-pip-mirror

help:
	@echo "Available commands:"
	@echo "  build     - Build all Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs"
	@echo "  test      - Run tests"
	@echo "  clean     - Clean up containers and images"
	@echo "  dev-setup - Setup development environment"
	@echo "  health    - Check service health"
	@echo "  setup-pip-mirror - Setup pip to use Tsinghua mirror"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-answer:
	docker-compose logs -f answer-service

logs-viz:
	docker-compose logs -f viz-service

test:
	docker-compose exec answer-service python -m pytest
	docker-compose exec viz-service python -m pytest

clean:
	docker-compose down -v
	docker system prune -f

dev-setup:
	@if [ ! -f .env ]; then cp env.example .env; echo "Created .env file from env.example"; fi
	@echo "Please edit .env file with your configuration"
	@echo "Don't forget to set your DASHSCOPE_API_KEY"

setup-pip-mirror:
	@echo "Setting up pip to use Tsinghua mirror..."
	@mkdir -p ~/.pip
	@cp pip.conf ~/.pip/pip.conf
	@echo "✅ Pip mirror configured successfully!"
	@echo "You can now use 'pip install' with faster download speeds."

health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Answer service is down"
	@curl -f http://localhost:8001/health || echo "Viz service is down"

restart-answer:
	docker-compose restart answer-service

restart-viz:
	docker-compose restart viz-service 