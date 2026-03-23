# Makefile for AI-Assistant Project
.PHONY: help install test lint format clean docker-build docker-up docker-down

# Default target
help:
	@echo "AI-Assistant Project Commands:"
	@echo "  make install          - Install all dependencies"
	@echo "  make test            - Run all tests"
	@echo "  make test-chatbot    - Run ChatBot tests"
	@echo "  make test-text2sql   - Run Text2SQL tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"
	@echo "  make clean           - Clean temporary files"
	@echo "  make docker-build    - Build all Docker images"
	@echo "  make docker-up       - Start all services"
	@echo "  make docker-down     - Stop all services"
	@echo "  make deploy          - Deploy to production"

# Installation
install:
	@echo "Installing dependencies..."
	cd ChatBot && pip install -r requirements.txt
	cd "Text2SQL Services" && pip install -r requirements.txt
	pip install pre-commit
	pre-commit install

install-test:
	@echo "Installing test dependencies..."
	pip install pytest pytest-cov pytest-mock pytest-flask requests-mock

# Testing
test:
	@echo "Running all tests..."
	pytest ChatBot/tests/ -v --cov=ChatBot --cov-report=html
	pytest "Text2SQL Services/tests/" -v --cov="Text2SQL Services" --cov-report=html

test-chatbot:
	@echo "Running ChatBot tests..."
	cd ChatBot && pytest tests/ -v --cov=. --cov-report=html --cov-report=term

test-text2sql:
	@echo "Running Text2SQL tests..."
	cd "Text2SQL Services" && pytest tests/ -v --cov=. --cov-report=html --cov-report=term

test-coverage:
	@echo "Generating coverage report..."
	pytest --cov=. --cov-report=html --cov-report=term-missing

# Code Quality
lint:
	@echo "Running linters..."
	flake8 ChatBot/ --max-line-length=100 --exclude=venv_chatbot,Storage
	flake8 "Text2SQL Services/" --max-line-length=100 --exclude=Text2SQL,Speech2Text

format:
	@echo "Formatting code..."
	black ChatBot/ --line-length=100 --exclude=venv_chatbot
	black "Text2SQL Services/" --line-length=100 --exclude=Text2SQL
	isort ChatBot/ --profile black
	isort "Text2SQL Services/" --profile black

type-check:
	@echo "Running type checks..."
	mypy ChatBot/ --ignore-missing-imports
	mypy "Text2SQL Services/" --ignore-missing-imports

# Cleaning
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete

# Docker
docker-build:
	@echo "Building Docker images..."
	docker-compose build

docker-build-chatbot:
	@echo "Building ChatBot image..."
	docker-compose build chatbot

docker-build-text2sql:
	@echo "Building Text2SQL image..."
	docker-compose build text2sql

docker-up:
	@echo "Starting all services..."
	docker-compose up -d

docker-down:
	@echo "Stopping all services..."
	docker-compose down

docker-logs:
	@echo "Showing logs..."
	docker-compose logs -f

docker-restart:
	@echo "Restarting services..."
	docker-compose restart

# Development
dev-chatbot:
	@echo "Starting ChatBot in dev mode..."
	cd ChatBot && python app.py

dev-text2sql:
	@echo "Starting Text2SQL in dev mode..."
	cd "Text2SQL Services" && python app_simple.py

# Security
security-check:
	@echo "Running security checks..."
	bandit -r ChatBot/ -x venv_chatbot,tests
	bandit -r "Text2SQL Services/" -x Text2SQL,Speech2Text,tests

# Deployment
deploy:
	@echo "Deploying to production..."
	git push origin master
	# Add your deployment commands here

# Documentation
docs:
	@echo "Opening documentation..."
	start docs/API_DOCUMENTATION.md

# Git helpers
git-status:
	@git status

git-pull:
	@git pull origin Ver_1

git-push:
	@git add .
	@git commit -m "Auto commit"
	@git push origin Ver_1
