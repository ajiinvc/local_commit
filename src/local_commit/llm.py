"""LLM model loading, prompt building, and commit-message generation."""

import os
import textwrap

from local_commit.config import (
    LLM_CONTEXT_SIZE,
    LLM_MAX_TOKENS,
    LLM_REPEAT_PENALTY,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    MODEL_PATH,
)

_llm = None  # module-level singleton


def load_model():
    """Load (or return already-loaded) ``Llama`` model instance."""
    global _llm
    if _llm is not None:
        return _llm

    from llama_cpp import Llama

    _llm = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=LLM_CONTEXT_SIZE,
        n_threads=max(1, (os.cpu_count() or 2) - 1),
        n_gpu_layers=0,
        verbose=False,
        use_mlock=False,
        use_mmap=True,
    )
    return _llm


def unload_model() -> None:
    """Release the model from memory (useful for testing)."""
    global _llm
    _llm = None


# ─── Prompt & generation ─────────────────────────────────────────────────────


def generate_commit_message(
    diff_stat: str,
    diff_content: str,
    group_label: str | None = None,
    files: list[str] | None = None,
) -> str:
    """Ask the local LLM to write a conventional commit message.

    Returns a message string (may be multi-line).
    """
    llm = load_model()

    context = _build_context(group_label, files)

    prompt = textwrap.dedent(f"""\
    You are a senior developer writing a git commit message.
    Follow the Conventional Commits spec: <type>(<scope>): <short description>

    Types: feat, fix, refactor, docs, style, test, chore, build, ci, perf

    CRITICAL — Anti-hallucination rules (these are strict):
    - Describe ONLY what you can see in the diff above.
      Do NOT invent changes, features, fixes, or reasons.
    - If the diff shows a typo fix, say "fix: correct typo in …".
      Do NOT say "refactor" or "feat".
    - If the diff adds a function, say "feat: add …".
      Do NOT claim performance improvements unless the diff proves it.
    - Subject line: max 72 chars, imperative mood, no period.
    - Body (optional): wrap at 72 chars, list what changed factually.
    - Never write *why* — only write what the diff actually does.
      When in doubt, describe less.

    {context}
    Diff summary:
    {diff_stat}

    Diff content:
    {diff_content}

    Write ONLY the commit message, nothing else:
    """).strip()

    response = llm(
        prompt,
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
        top_p=LLM_TOP_P,
        repeat_penalty=LLM_REPEAT_PENALTY,
        stop=["\n\n\n", "```", "---"],
    )

    raw = response["choices"][0]["text"].strip()
    message = _clean_output(raw)

    # Fallback: if the message doesn't reference any file from the diff,
    # append filenames so it stays grounded.
    message = _validate_files_in_message(message, diff_stat)

    return message


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _build_context(
    group_label: str | None,
    files: list[str] | None,
) -> str:
    """Build the context string inserted before the diff in the prompt."""
    parts: list[str] = []
    if group_label:
        parts.append(f"Group: {group_label}")
    if files:
        lines = ["Files changed:"]
        lines.extend(f"  - {f}" for f in files[:20])
        if len(files) > 20:
            lines.append(f"  … and {len(files) - 20} more")
        parts.append("\n".join(lines))
    return ("\n".join(parts) + "\n\n") if parts else ""


def _clean_output(raw: str) -> str:
    """Strip markdown fences, trailing explanations, etc."""
    lines = raw.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if any(
            line.lower().startswith(x)
            for x in ["note:", "explanation:", "this commit", "here is", "---"]
        ):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _validate_files_in_message(message: str, diff_stat: str) -> str:
    """If the message doesn't name any file from the diff, append filenames."""
    diff_files: set[str] = set()
    for line in diff_stat.splitlines():
        parts = line.split("|", 1)
        name = parts[0].strip()
        if name:
            diff_files.add(name)

    if diff_files:
        msg_lower = message.lower()
        mentioned = any(f.lower() in msg_lower for f in diff_files)
        if not mentioned:
            file_list = ", ".join(sorted(diff_files)[:5])
            message = message + f"\n\nFiles: {file_list}"

    return message
