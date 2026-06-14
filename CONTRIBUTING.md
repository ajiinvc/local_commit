# Contributing

We welcome contributions! Here's how to get started.

## Development setup

```bash
# Clone & enter
git clone https://github.com/your-org/local-commit
cd local-commit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in editable mode with dev extras
pip install -e ".[dev]"
```

## Running tests

```bash
make test
# or
python -m pytest
```

## Code style

- **Formatter**: [Ruff](https://docs.astral.sh/ruff/) — run `make lint`
- **Type hints**: required for all public functions / methods
- **Line length**: 88 characters
- **Imports**: stdlib → third-party → local (separated by blank lines)

## Commit style

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(config): add support for custom model paths
fix(llm): prevent empty message on empty diff
docs(readme): clarify --auto flag behaviour
```

## Pull request process

1. Open an issue first to discuss the change you'd like to make
2. Fork the repo and create a branch: `git checkout -b feat/my-feature`
3. Write code + tests
4. Run `make check` (lint + typecheck + test)
5. Open a PR against `main`

## Adding a new model

1. Update `src/local_commit/config.py` with the new `MODEL_URL` / `MODEL_FILENAME`
2. Adjust the prompt in `src/local_commit/llm.py` if the new model needs different instructions
3. Test with `local-commit --setup` then `local-commit` on a real repo

## Reporting bugs

Include:

- Your OS and Python version
- Full command output (use `--auto` if relevant)
- A minimal reproduction (a small git repo / diff that triggers the issue)
