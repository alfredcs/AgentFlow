# Makefile for AgentFlow

.PHONY: help install test lint format clean docs run-example

help:
	@echo "AgentFlow - Development Commands"
	@echo ""
	@echo "install       Install dependencies"
	@echo "test          Run tests"
	@echo "test-cov      Run tests with coverage"
	@echo "lint          Run linters"
	@echo "format        Format code"
	@echo "clean         Clean build artifacts"
	@echo "docs          Build documentation"
	@echo "run-example   Run basic example"
	@echo "deploy-check  Check deployment readiness"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=agentflow --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ examples/
	ruff check --fix src/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	cd docs && mkdocs build

run-example:
	python examples/basic_workflow.py

deploy-check:
	@echo "Checking deployment readiness..."
	@python -c "import boto3; print('✓ boto3 installed')"
	@python -c "from agentflow import Workflow; print('✓ AgentFlow importable')"
	@aws bedrock list-foundation-models --region us-east-1 > /dev/null && echo "✓ Bedrock accessible" || echo "✗ Bedrock not accessible"
	@echo "Deployment check complete"
