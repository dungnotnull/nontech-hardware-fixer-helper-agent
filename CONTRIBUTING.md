# Contributing to FixerAgent

Thank you for considering contributing to FixerAgent! We welcome bug reports, feature requests, documentation improvements, and code contributions.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [How to Contribute](#how-to-contribute)
- [Reporting Bugs](#reporting-bugs)
- [Security Issues](#security-issues)

---

## Code of Conduct

This project adheres to a standard of respectful, inclusive collaboration. Harassment or discrimination of any kind is not tolerated.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nontech-hardware-fixer-agent.git
   cd nontech-hardware-fixer-agent
   ```
3. Install dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```
4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

## Development Setup

### Requirements
- Python 3.11+
- `uv` (recommended) or `pip`
- Docker + Docker Compose (for full stack)
- Node.js 18+ (for frontend)

### Running Tests
```bash
pytest tests/ -v --tb=short
```

### Linting & Formatting
```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Starting the Backend
```bash
docker compose up -d
uvicorn fixeragent.api.main:app --reload
```

### Starting the Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
src/fixeragent/
├── agents/         # Orchestration layer
├── api/            # FastAPI backend
├── config/         # Settings & logging
├── models/         # Pydantic schemas
├── tools/          # Vision, RAG, crawlers, safety, repair generator
├── celery_config.py
├── cli.py
└── tasks.py

frontend/           # Next.js web app
tests/              # pytest suite
scripts/            # Knowledge updater, crawlers
data/               # Manuals, embeddings, feedback logs
docs/               # Architecture & legal docs
```

## Coding Standards

- **Python 3.11+** with `from __future__ import annotations`
- **Type hints** on all public functions
- **Pydantic v2** for all data models
- **Loguru** for logging (no `print` in production code)
- **Docstrings** for all modules, classes, and public methods
- **No `dummy` / `TODO` comments in merged code** — implement the logic or open an issue

### Safety-Critical Rules
Safety is the highest priority in this project. Any code touching the following must include unit tests and maintain a paper trail:

- Repair tier classification (`safety_assessor.py`)
- Escalation logic for mains voltage, gas, refrigerant, microwave capacitors
- Confidence threshold gating before issuing repair instructions

## How to Contribute

### 1. Find or Open an Issue
Check the [issue tracker](../../issues) for open tasks. Comment on an issue before starting work to avoid duplication.

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes
- Keep changes focused and atomic.
- Add tests for new functionality.
- Update documentation if behavior changes.

### 4. Commit
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add LED blink pattern detector
fix: correct microwave tier-4 escalation logic
docs: update API endpoint examples
test: add safety assessor edge cases
```

### 5. Push and Open a Pull Request
```bash
git push origin feature/your-feature-name
```

**PR requirements:**
- Descriptive title and summary
- Link to related issue(s)
- All CI checks passing
- At least one maintainer review

## Reporting Bugs

Use the [bug report template](../../issues/new?template=bug_report.md) and include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (scrub API keys before posting)

## Security Issues

Please see [SECURITY.md](SECURITY.md) for our responsible disclosure policy.

---

*By contributing, you agree that your contributions will be licensed under the MIT License.*