"""Command-line entrypoint and interactive commit workflow."""

import argparse
import subprocess
import textwrap

from local_commit import __version__
from local_commit.colors import C, info, ok, warn, err, step, _safe_print, print_banner
from local_commit.config import DIFF_MAX_CHARS
from local_commit.git_utils import (
    ensure_git_repo,
    get_changed_files,
    get_diff,
    stage_files,
    do_commit,
    git,
)
from local_commit.grouping import group_changes
from local_commit.llm import generate_commit_message, load_model


# ─── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Parse args, ensure deps / model, then run the interactive flow."""
    print_banner()
    parser = _build_parser()
    args = parser.parse_args()

    if args.setup:
        _run_setup()
        return

    _ensure_dependencies()
    _download_model()
    interactive_mode(auto=args.auto)


# ─── Setup ────────────────────────────────────────────────────────────────────


def _run_setup() -> None:
    """Download the model and verify it loads."""
    _ensure_dependencies()
    _download_model()
    step("Testing model load")
    load_model()
    ok("Setup complete! Run without --setup to commit.")


# ─── Dependency bootstrapping ────────────────────────────────────────────────


def _ensure_dependencies() -> None:
    """Install ``llama-cpp-python`` and ``requests`` if missing (pure-Python
    fallback, no CUDA)."""
    import sys

    step("Checking dependencies")

    packages = {"llama_cpp": "llama-cpp-python", "requests": "requests"}
    missing = []
    for mod, pkg in packages.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if not missing:
        ok("All dependencies present")
        return

    import os

    info(f"Installing: {', '.join(missing)}")
    env = os.environ.copy()
    env["CMAKE_ARGS"] = "-DGGML_BLAS=OFF -DGGML_CUDA=OFF -DGGML_METAL=OFF"
    env["FORCE_CMAKE"] = "1"

    cmd = [sys.executable, "-m", "pip", "install", "--quiet"] + missing
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        info("Trying pre-built wheel …")
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--quiet",
                "llama-cpp-python",
                "--extra-index-url",
                "https://abetlen.github.io/llama-cpp-python/whl/cpu",
            ],
            check=True,
        )
    ok("Dependencies installed")


def _download_model() -> None:
    """Download the GGUF model from Hugging Face with a progress bar."""
    import requests as req

    from local_commit.config import MODEL_DIR, MODEL_PATH, MODEL_URL

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists():
        size_mb = MODEL_PATH.stat().st_size / 1_048_576
        ok(f"Model already downloaded ({size_mb:.0f} MB) → {MODEL_PATH}")
        return

    step("Downloading model (~400 MB)")
    info(f"URL : {MODEL_URL}")
    info(f"Dest: {MODEL_PATH}")
    print()

    try:
        with req.get(MODEL_URL, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            bar_width = 40

            with open(MODEL_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total
                        filled = int(bar_width * pct)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        mb_done = downloaded / 1_048_576
                        mb_total = total / 1_048_576
                        print(
                            f"\r  [{bar}] {mb_done:.1f}/{mb_total:.1f} MB",
                            end="",
                            flush=True,
                        )
        print()
        ok("Model downloaded successfully")
    except Exception as e:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        err(f"Download failed: {e}")
        raise SystemExit(1) from e


# ─── Interactive workflow ─────────────────────────────────────────────────────


def interactive_mode(auto: bool = False) -> None:
    """Main interactive (or fully automatic) commit workflow."""
    ensure_git_repo()

    step("Scanning repository changes")
    changes = get_changed_files()
    total = (
        len(changes["staged"])
        + len(changes["unstaged"])
        + len(changes["untracked"])
    )

    if total == 0:
        info("No changes detected. Nothing to commit.")
        return

    _print_change_summary(changes)

    step("Grouping changes into logical commits")
    groups = group_changes(changes)

    if not groups:
        err("Could not group changes.")
        return

    _print_groups(groups)

    if not auto:
        groups = _prompt_group_selection(groups)
        if groups is None:
            return

    # Stage everything once
    step("Staging all changes")
    all_files = [f for g in groups for f in g["files"]]
    stage_files(all_files)
    ok(f"Staged {len(all_files)} file(s)")

    # Generate & commit per group
    step("Generating commit messages with local LLM")

    for i, group in enumerate(groups, 1):
        print(f"\n  {C.BOLD}[{i}/{len(groups)}] {group['label']}{C.RESET}")

        # Reset and re-stage only this group's files so the diff is focused
        subprocess.run(
            ["git", "reset", "HEAD", "--quiet"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        stage_files(group["files"])

        diff_stat, diff_content = get_diff(max_chars=DIFF_MAX_CHARS)
        if not diff_stat and not diff_content:
            warn(f"No diff for '{group['label']}' – skipping")
            continue

        info("Asking LLM …")
        msg = generate_commit_message(
            diff_stat,
            diff_content,
            group_label=group["label"],
            files=group["files"],
        )

        _print_message(msg)

        if not auto:
            choice = _prompt_message_choice(msg, diff_stat, diff_content)
            if choice == "q":
                warn("Aborted by user.")
                subprocess.run(
                    ["git", "reset", "HEAD", "--quiet"],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                )
                return
            if choice == "s":
                info("Skipped.")
                subprocess.run(
                    ["git", "reset", "HEAD", "--quiet"],
                    capture_output=True,
                )
                continue
            if choice == "e":
                edited = input("  Enter commit message: ").strip()
                if edited:
                    msg = edited
                else:
                    warn("Empty message – using generated one.")

        do_commit(msg)

    _print_footer()


# ─── UI helpers ───────────────────────────────────────────────────────────────


def _print_change_summary(changes: dict[str, list]) -> None:
    print(f"\n  {C.BOLD}Changes found:{C.RESET}")
    if changes["staged"]:
        print(f"  {C.GREEN}Staged   :{C.RESET} {len(changes['staged'])} file(s)")
    if changes["unstaged"]:
        print(f"  {C.YELLOW}Unstaged :{C.RESET} {len(changes['unstaged'])} file(s)")
    if changes["untracked"]:
        print(f"  {C.DIM}Untracked:{C.RESET} {len(changes['untracked'])} file(s)")


def _print_groups(groups: list[dict]) -> None:
    print(f"\n  Found {C.BOLD}{len(groups)}{C.RESET} logical group(s):\n")
    for i, g in enumerate(groups, 1):
        print(f"  {C.CYAN}{i}.{C.RESET} {C.BOLD}{g['label']}{C.RESET}")
        for f in g["files"][:5]:
            print(f"     {C.DIM}• {f}{C.RESET}")
        if len(g["files"]) > 5:
            print(f"     {C.DIM}  … +{len(g['files']) - 5} more{C.RESET}")


def _print_message(msg: str) -> None:
    print(f"\n  {C.YELLOW}Generated message:{C.RESET}")
    print(f"  {C.BOLD}{msg.splitlines()[0]}{C.RESET}")
    if "\n" in msg:
        for line in msg.splitlines()[1:]:
            print(f"  {C.DIM}{line}{C.RESET}")


def _prompt_group_selection(groups: list[dict]) -> list[dict] | None:
    """Let the user pick which groups to commit. Returns filtered list or None."""
    print()
    ans = (
        input(
            f"  {C.BOLD}Commit all {len(groups)} group(s)? "
            f"[Y/n/pick]:{C.RESET} "
        )
        .strip()
        .lower()
    )

    if ans == "n":
        info("Aborted.")
        return None

    if ans == "pick" or (ans.replace(",", "").replace(" ", "").isdigit()):
        selected = ans if ans != "pick" else input(
            "  Enter group numbers to commit (e.g. 1,3): "
        ).strip()
        try:
            indices = [int(x.strip()) - 1 for x in selected.split(",")]
            picked = [groups[i] for i in indices if 0 <= i < len(groups)]
            if not picked:
                err("No valid groups selected.")
                return None
            return picked
        except (ValueError, IndexError):
            err("Invalid selection.")
            return None

    return groups  # Y or enter


def _prompt_message_choice(
    msg: str,
    diff_stat: str,
    diff_content: str,
) -> str:
    """Return one of ``a``, ``e``, ``s``, ``d``, ``q``."""
    # Show brief diff stats for fact-checking
    print(f"\n  {C.DIM}Diff stats:{C.RESET}")
    lines = diff_stat.splitlines()
    for line in lines[:5]:
        print(f"  {C.DIM}  {line}{C.RESET}")
    if len(lines) > 5:
        print(f"  {C.DIM}  … +{len(lines) - 5} more{C.RESET}")

    print()
    while True:
        choice = (
            input(
                f"  {C.BOLD}[a]ccept / [e]dit / [s]kip / [d]iff / [q]uit:{C.RESET} "
            )
            .strip()
            .lower()
        )
        if choice == "d":
            print(f"\n  {C.DIM}Full diff:{C.RESET}")
            for line in diff_content.splitlines():
                print(f"  {C.DIM}{line}{C.RESET}")
            print()
            continue
        if choice in ("a", "e", "s", "q"):
            return choice
        warn(f"Invalid choice: '{choice}'")


def _print_footer() -> None:
    _safe_print(f"\n{C.GREEN}{C.BOLD}  Done! All commits created.{C.RESET}\n")
    log = git(["log", "--oneline", "-5"])
    print(f"  {C.DIM}Recent commits:{C.RESET}")
    for line in log.splitlines():
        print(f"  {C.DIM}  {line}{C.RESET}")
    print()


# ─── Argument parser ──────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local LLM-powered git commit message generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          local-commit             interactive commit
          local-commit --setup     download model only
          local-commit --auto      fully automatic (no prompts)
        """),
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Download model and exit",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Non-interactive: stage, generate, commit all groups",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"local-commit {__version__}",
    )
    return parser
