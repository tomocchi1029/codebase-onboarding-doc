# Contributing to Codebase Onboarding Doc

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/tomocchi1029/codebase-onboarding-doc.git
cd codebase-onboarding-doc
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest -v
pytest --cov=codebase_onboarding_doc
```

## Linting

```bash
ruff check src tests
mypy src
```

## Adding a New Code Pattern Detector

1. Add a `detect_xxx()` function in `src/codebase_onboarding_doc/code_analyzer.py`
2. Add a new `FindingType` in `models.py` if needed
3. Wire it in `analyze_codebase()`
4. Add tests in `tests/test_code_analyzer.py`

## Pull Request Process

1. Fork the repo and create a feature branch
2. Write tests for your changes
3. Ensure all tests pass and linting is clean
4. Open a PR with a clear description
