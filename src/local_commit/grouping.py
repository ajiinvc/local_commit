"""Heuristic grouping of changed files into logical commit groups."""

from pathlib import Path

# Well-known dependency / config filenames that imply special semantics
DEP_FILES = {
    "requirements.txt", "Pipfile", "Pipfile.lock",
    "pyproject.toml", "setup.cfg", "setup.py",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Gemfile", "Gemfile.lock", "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}
DOCKER_FILES = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".dockerignore", "compose.yml", "compose.yaml",
}
CI_DIRS = {".github", ".gitlab-ci.yml", ".circleci", ".travis.yml",
           "Jenkinsfile", ".drone.yml"}

FRAMEWORK_SUBDIRS = {
    "models", "views", "serializers", "urls", "forms",
    "admin", "signals", "tasks", "permissions", "tests",
    "migrations",
}


def group_changes(changes: dict[str, list]) -> list[dict]:
    """Group changed files into logical commit groups.

    Accepts the dict from :func:`git_utils.get_changed_files`.

    Returns list of dicts::
        [{"label": str, "files": [str, ...]}, ...]

    Small singleton groups are merged into a ``Miscellaneous changes``
    group when they would otherwise fragment the commit log.
    """
    all_files = _collect_all_file_paths(changes)
    if not all_files:
        return []

    raw_groups: dict[str, list[str]] = {}
    for f in all_files:
        key = _classify(f)
        raw_groups.setdefault(key, []).append(f)

    return _merge_singletons(raw_groups)


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _collect_all_file_paths(changes: dict[str, list]) -> list[str]:
    """Deduplicated, ordered list of every changed file."""
    seen: set[str] = set()
    paths: list[str] = []
    for status, path in changes["staged"]:
        if path not in seen:
            paths.append(path)
            seen.add(path)
    for status, path in changes["unstaged"]:
        if path not in seen:
            paths.append(path)
            seen.add(path)
    for path in changes["untracked"]:
        if path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def _classify(filepath: str) -> str:
    """Return a human-readable group label for *filepath*."""
    p = Path(filepath)
    ext = p.suffix.lower()
    parts = p.parts
    name = p.name

    # ── special filenames ──
    if name in DEP_FILES:
        return "Dependencies"
    if name in DOCKER_FILES:
        return "Docker"
    if parts[0] in CI_DIRS or name in CI_DIRS:
        return "CI / DevOps"
    if name.startswith(".git"):
        return "Git config"
    if name in (".env", ".env.example", ".env.local"):
        return "Config & env"

    # ── by extension ──
    if ext in (".py",):
        return _py_label(p, parts)
    if ext in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        return f"JS/TS – {parts[0]}/" if len(parts) > 1 else "JS/TS – root"
    if ext in (".html", ".htm", ".jinja", ".jinja2", ".j2"):
        return "Templates"
    if ext in (".css", ".scss", ".sass", ".less"):
        return "Styles"
    if ext in (".md", ".rst", ".txt", ".mdx"):
        return "Docs & text"
    if ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"):
        return "Config & data"
    if ext in (".sql",):
        return "Database / SQL"
    if ext in (".sh", ".bash", ".zsh", ".fish", ".ps1"):
        return "Shell scripts"
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp"):
        return "Assets / images"

    return f"Other – {parts[0]}/" if len(parts) > 1 else "Other – root"


def _py_label(p: Path, parts: tuple[str, ...]) -> str:
    """Build a label for a ``.py`` file based on its directory depth."""
    if len(parts) >= 3:
        app, sub = parts[0], parts[1]
        if sub in FRAMEWORK_SUBDIRS:
            return f"Python – {app}/ (app)"
        return f"Python – {app}/{sub}/"
    if len(parts) == 2:
        sub = parts[0]
        if sub in FRAMEWORK_SUBDIRS:
            return f"Python – {sub}/ (framework)"
        return f"Python – {sub}/"
    return "Python – root"


def _merge_singletons(
    raw_groups: dict[str, list[str]],
) -> list[dict]:
    """Merge groups with a single file into *Miscellaneous* when there are
    many of them."""
    singletons = {k: v for k, v in raw_groups.items() if len(v) == 1}
    big_groups = {k: v for k, v in raw_groups.items() if len(v) > 1}

    if len(singletons) > 4:
        merged_files = [f for files in singletons.values() for f in files]
        big_groups["Miscellaneous changes"] = merged_files
    else:
        big_groups.update(singletons)

    return [{"label": label, "files": files}
            for label, files in big_groups.items()]
