"""Ollama-only LLM client for the @gpumaxxing Twitter bot."""
import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, Sequence
from .config import OLLAMA_MODEL
from .logger import log

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "600"))
LLM_RATE_LIMIT_CODE = 75

def llm_hourly_limit_status() -> tuple[bool, int, int, int]:
    """Compatibility shim: LLM budget limits are disabled for local Ollama."""
    return False, 0, 0, 0

# Sarcastic / high-confidence comedy forcer. 
_FUNNY_FORCER = "Follow the GPUMAXXING content engine strategy. Be cinematic, confident, and futuristic.\n\n"

@dataclass
class LLMResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

def _run_ollama_http(prompt: str, label: str, timeout: int) -> LLMResult:
    """Hit ollama's /api/generate directly."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": _FUNNY_FORCER + prompt,
        "stream": False,
        "keep_alive": "24h",
        "think": False,
        "options": {
            "temperature": 1.0,
            "top_p": 0.95,
            "repeat_penalty": 1.15,
            "num_predict": 1800,
        },
    }).encode("utf-8")
    
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        text = (data.get("response") or "").strip()
        return LLMResult(0, text, "")
    except urllib.error.URLError as e:
        return LLMResult(1, "", f"{label}: ollama HTTP error: {e}")
    except (json.JSONDecodeError, ValueError) as e:
        return LLMResult(1, "", f"{label}: ollama returned non-JSON: {e}")
    except Exception as e:
        return LLMResult(1, "", f"{label}: ollama unexpected error: {e}")

def run_llm(
    prompt: str,
    model: str,
    *,
    label: str,
    output_json: bool = True,
    allowed_tools: Optional[Sequence[str]] = None,
    permission_mode: Optional[str] = None,
    timeout: Optional[int] = None,
    cwd: Optional[str] = None,
) -> LLMResult:
    """Main entry point: hard-locked to local Ollama."""
    effective_timeout = max(timeout or 0, DEFAULT_LLM_TIMEOUT_SECONDS)
    log.info(f"[LLM] {label}: ollama HTTP / {OLLAMA_MODEL} (timeout {effective_timeout}s).")
    return _run_ollama_http(prompt, label=label, timeout=effective_timeout)

def unwrap_text(stdout: str) -> str:
    """Return raw text from Ollama response."""
    return (stdout or "").strip()

def contains_post_unsafe_leak(text: str) -> bool:
    """Safety check to prevent leaking internal tags or code."""
    if not text:
        return False
    # Check for common internal indicators
    indicators = ["<function", "{\"type\":", "[[step_start]]", "[[thought]]"]
    return any(ind in text for ind in indicators)

def strip_tool_calls(text: str) -> str:
    """Deterministic removal of any XML-style tool calls."""
    import re
    return re.sub(r"<function=.*?>.*?</function>", "", text, flags=re.DOTALL).strip()
