# local-commit

**Local LLM-powered conventional commit messages.**  
Runs entirely offline — no API keys, no cloud, no data leaves your machine.

Uses [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF)
via `llama-cpp-python` in CPU mode, requiring **≈1 GB RAM**.  
Works on any OS (Windows, macOS, Linux) — even low-end devices.

---

## Features

- **Fully local** — no internet needed after model download
- **Conventional Commits** — messages follow the `<type>(<scope>): <desc>` spec
- **Smart grouping** — detects logical commit groups by file type & directory
- **Anti-hallucination** — the prompt is hardened against inventing changes
- **Interactive & `--auto` modes** — review or batch-commit
- **Low resource** — ~1 GB RAM, CPU-only, works on a Raspberry Pi 4

---

## Quick start

Choose your path:

| You have… | Install with |
|-----------|-------------|
| Python 3.9+ | `pip install local-commit` |
| Docker | `make docker-build` |
| Nothing but a terminal | One-liner below |

### One-liner installs (no Python needed)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/your-org/local-commit/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/your-org/local-commit/main/scripts/install.ps1 | iex
```

The script auto-detects what you have (pip → binary → Docker) and picks the
best method.

### pip install

```bash
pip install local-commit
local-commit --setup        # download model (one-time, ~400 MB)
cd my-project && local-commit
```

### Docker (any OS — no Python on host)

```bash
# Build once
make docker-build

# Download model (persists in named volume)
make docker-setup

# Use in any repo
make docker-run
# or set an alias:
alias lc='docker run --rm -v local-commit-model:/root/.local-commit \
  -v "$(pwd):/repo" -w /repo local-commit'
lc
```

### Pre-built binary (no Python, no Docker)

Grab the latest binary from
[GitHub Releases](https://github.com/your-org/local-commit/releases):

| Platform | Binary |
|----------|--------|
| Linux x86_64 | `local-commit_linux_x86_64` |
| macOS (Intel) | `local-commit_macos_x86_64` |
| macOS (Apple Silicon) | `local-commit_macos_aarch64` |
| Windows x86_64 | `local-commit_windows_x86_64.exe` |

Download, `chmod +x`, put it on your `PATH`, run `local-commit --setup` once.

### From source

```bash
git clone https://github.com/your-org/local-commit
cd local-commit

# Quick start with Make:
make setup           # install + download model
local-commit         # use it

# Or manually:
pip install -e ".[dev]"
python -m local_commit --setup
python -m local_commit
```

### Windows (no admin rights)

```powershell
# If you have Python:
pip install local-commit
local-commit --setup

# Or download the .exe from Releases and put it in %LOCALAPPDATA%\Programs\
# (the install.ps1 script does this automatically)
```

---

## Usage

```
local-commit [--setup] [--auto]
```

| Flag | Description |
|------|-------------|
| `--setup` | Download the model and exit (one-time setup) |
| `--auto` | Non-interactive: stage all, generate, commit all groups |
| `--version` | Show version number |

### Interactive flow

1. **Scan** — detects staged, unstaged, and untracked files
2. **Group** — files are grouped into logical commits (e.g. *Python – app/*, *Dependencies*, *Docker*)
3. **Review** — you choose which groups to commit (`Y` / `n` / `pick 1,3`)
4. **Generate** — the LLM writes a commit message per group
5. **Accept or tweak** — per message: `[a]ccept`, `[e]dit`, `[s]kip`, `[d]iff`, `[q]uit`

### Automatic mode

```bash
local-commit --auto
```

Stages everything, generates messages for every group, and commits immediately.
Useful for CI or when you trust the model's output.

---

## Project structure

```
local-commit/
├── .github/
│   ├── workflows/ci.yml           # CI: test, lint, build binaries
│   └── ISSUE_TEMPLATE/            # bug report & feature request forms
├── scripts/
│   ├── install.sh                 # Linux/macOS installer (curl | bash)
│   └── install.ps1                # Windows installer (irm | iex)
├── src/local_commit/
│   ├── __init__.py                # package metadata (v0.1.0)
│   ├── __main__.py                # python -m entry point
│   ├── cli.py                     # CLI parser + interactive flow
│   ├── colors.py                  # terminal colours (UTF-8 safe)
│   ├── config.py                  # model paths, LLM defaults
│   ├── git_utils.py               # git diff / stage / commit helpers
│   ├── grouping.py                # heuristic file-to-commit grouping
│   └── llm.py                     # model loading + anti-hallucination prompt
├── tests/                         # pytest suite
├── Dockerfile                     # run anywhere Docker runs
├── Makefile                       # make setup / make test / make build
├── run.py                         # PyInstaller entry point
├── main.py                        # legacy wrapper (python main.py)
├── pyproject.toml                 # build config & entry points
├── LICENSE
├── CONTRIBUTING.md
└── CHANGELOG.md
```

---

## How the commit message is generated

1. The tool runs `git diff --cached` (or `git diff` as fallback)
2. Files are grouped by type, extension, and directory
3. For each group, the diff + file list is sent to the local LLM
4. The LLM returns a Conventional Commits message

### Anti-hallucination measures

- **Prompt hardened** — explicitly instructs the model to describe *only what's in the diff*, never to invent changes
- **Temperature 0.1** — near-deterministic output
- **File-name validation** — if the generated message doesn't reference any file from the diff, filenames are appended
- **Diff preview** — you see the diff stats before accepting each message

---

## Requirements

| Dependency | Version | Notes |
|-----------|---------|-------|
| Python   | ≥ 3.9   |       |
| `llama-cpp-python` | ≥ 0.2.0 | CPU-only wheel (no CUDA) |
| `requests` | ≥ 2.28 | For model download only |

The model is **Qwen2.5-0.5B-Instruct Q4_K_M** (~400 MB download, ~500 MB on disk).

---

## FAQ

### Can I use a different model?

Not yet — the model path is hardcoded in `config.py`, but the abstraction is
simple enough that swapping the GGUF file + adjusting the prompt should work.
PRs welcome!

### How is this different from `aicommits` / `opencommit`?

Those tools send your diff to OpenAI / Anthropic APIs.  
`local-commit` runs **100 % offline** — your code never leaves your machine.

### How much does it cost per commit?

**$0.00** — after the one-time model download.  
Cloud-based tools charge per token: a typical diff is 500–3000 tokens, plus the
model's reply (~100 tokens). At GPT-4o pricing (currently ~$2.50–10.00/1M input
tokens) that's **$0.001–0.03 per commit** — pennies at first, but it adds up
fast for teams making dozens of commits daily across the whole org.

| Tool | Per-commit cost | Data leaves your machine? | Requires internet? |
|------|----------------|---------------------------|-------------------|
| local-commit | **$0.00** | No | Setup only |
| aicommits (GPT-4o) | ~$0.003–0.03 | Yes | Yes |
| opencommit (GPT-4o) | ~$0.003–0.03 | Yes | Yes |
| GitHub Copilot commit | Included in $10–39/mo sub | Yes | Yes |

The trade-off: cloud models are smarter (GPT-4o / Claude can write richer
messages), while this model is **good enough, free, and private**.

### Does it work on Windows?

Yes. The `llama-cpp-python` pre-built CPU wheel supports Windows.
UTF-8 encoding is handled explicitly to avoid CP1252 issues.

---

## Development

```bash
git clone https://github.com/your-org/local-commit
cd local-commit

# Everything via Make (works on any OS):
make setup        # install deps + download model
make test         # run tests
make lint         # ruff check
make typecheck    # mypy
make check        # lint + typecheck + test all at once

# Or manually:
pip install -e ".[dev]"
python -m pytest
ruff check src/
mypy src/
```

### Build standalone executable

```bash
make build-exe
# → dist/local-commit (or .exe on Windows)
# No Python runtime needed — ship it as a single binary.
```

---

## License

MIT — see [LICENSE](LICENSE).
