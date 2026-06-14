"""Configuration constants: model paths, URLs, and defaults."""

from pathlib import Path

# ─── Model ────────────────────────────────────────────────────────────────────

MODEL_DIR = Path.home() / ".local-commit" / "models"
MODEL_FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/"
    + MODEL_FILENAME
)

# ─── LLM defaults ─────────────────────────────────────────────────────────────

LLM_CONTEXT_SIZE = 2048
LLM_MAX_TOKENS = 200
LLM_TEMPERATURE = 0.1
LLM_TOP_P = 0.9
LLM_REPEAT_PENALTY = 1.1
LLM_THREADS = None  # auto-detect at load time

# Diff content is capped to keep prompt within context window
DIFF_MAX_CHARS = 3000
