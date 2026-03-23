# Private / Non-Essential Files

This folder groups all non-critical files to keep the main project directory clean and focused.

## Organization

### docs/
- **documentation/** — Setup guides, API docs, architecture, migration guides
- **diagram/** — UML diagrams, ER diagrams, component specs, flow diagrams  
- **infrastructure/** — Docker deployment, Kubernetes configs, production setup

### scripts/
One-time setup/deployment scripts (not used in daily operations):
- create_tunnels.sh — Create public tunnels for services
- deploy.sh — Deployment script
- setup_models.sh — Model setup
- setup.py — Python setup

### dev-tools/
Development & CI/CD configuration:
- .github/ — GitHub Actions workflows
- .flake8 — Code style linting
- .pre-commit-config.yaml — Pre-commit hooks

### data/
Training data, models, and samples:
- local_data/ — Local cached data
- pretrain/ — Pre-training resources
- sample/ — Sample data for testing
- resources/ — Additional resources

## Usage
- Core project runs with files in the **root** only
- Reference [docs/](docs/) for guides and architecture
- Use [scripts/](scripts/) only for one-time setup tasks
- Dev-tools in [dev-tools/](dev-tools/) for CI/linting (configured in root config files)
