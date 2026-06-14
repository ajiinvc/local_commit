"""Terminal color helpers. Falls back to no-ops when stdout isn't a TTY."""

import os
import sys


class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    DIM    = "\033[2m"
    BLUE   = "\033[94m"


def _supports_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        return bool(int(os.environ.get("ANSICON", "0")))
    return True


if not _supports_color():
    for attr in dir(C):
        if not attr.startswith("_"):
            setattr(C, attr, "")


def _safe_print(text: str, **kwargs) -> None:
    """Print with fallback for terminals that can't render Unicode."""
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        clean = text.encode("ascii", "replace").decode("ascii")
        print(clean, **kwargs)


def info(msg: str) -> None:
    _safe_print(f"  {C.CYAN}i  {C.RESET}{msg}")


def ok(msg: str) -> None:
    _safe_print(f"  {C.GREEN}+  {C.RESET}{msg}")


def warn(msg: str) -> None:
    _safe_print(f"  {C.YELLOW}!  {C.RESET}{msg}")


def err(msg: str) -> None:
    _safe_print(f"  {C.RED}x  {C.RESET}{msg}", file=sys.stderr)


def step(msg: str) -> None:
    _safe_print(f"\n{C.BOLD}{C.BLUE}>  {msg}{C.RESET}")


def print_banner() -> None:
    banner = f"""
  {C.CYAN}{C.BOLD}+------------------------------------+
  |   local-commit  (local LLM)        |
  +------------------------------------+{C.RESET}
"""
    try:
        print(banner)
    except UnicodeEncodeError:
        fallback = f"""
  +------------------------------------+
  |   local-commit  (local LLM)        |
  +------------------------------------+
"""
        print(fallback)
