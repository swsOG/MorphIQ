"""AI client seams injected into ai_prefill for the eval harness.

Both clients are callables matching ``generate_gemini_text``'s keyword
signature ``(*, model, prompt, inline_pdf_b64=None, **kwargs) -> str`` so they
can be passed as ``client=`` to ``prefill_doc`` / ``detect_doc_type_from_pdf``.

A fresh client instance is created per case (see runners), so usage tracking is
naturally thread-safe with no shared mutable state.
"""

from __future__ import annotations

from typing import Any

# Sentinel phrase emitted by ai_prefill.detect_doc_type_from_pdf's user prompt.
_DETECTION_MARKER = "identify what type it is"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) for offline cost approximation."""
    return max(1, len(text) // 4)


class ReplayClient:
    """Returns recorded responses; never touches the network.

    ``recording`` is ``{"detection": "<label>", "extraction": "<raw json>"}``.
    The call is routed to detection vs extraction by inspecting the prompt.
    """

    def __init__(self, recording: dict[str, str]):
        self._recording = recording or {}
        self.usages: list[dict[str, int]] = []
        self.calls = 0

    def __call__(self, *, model: str, prompt: str, inline_pdf_b64: str | None = None, **_: Any) -> str:
        self.calls += 1
        is_detection = _DETECTION_MARKER in prompt.lower()
        text = self._recording.get("detection" if is_detection else "extraction", "")
        # Estimated usage so the cost panel is populated in replay mode.
        self.usages.append(
            {
                "promptTokenCount": _estimate_tokens(prompt),
                "candidatesTokenCount": _estimate_tokens(text),
                "totalTokenCount": _estimate_tokens(prompt) + _estimate_tokens(text),
            }
        )
        return text


class LiveClient:
    """Calls the real Gemini API and records token usage from the response."""

    def __init__(self) -> None:
        self.usages: list[dict[str, int]] = []
        self.calls = 0

    def __call__(self, *, model: str, prompt: str, inline_pdf_b64: str | None = None, **kwargs: Any) -> str:
        # Imported lazily so offline runs never import the live path's needs.
        from portal_new.ai_runtime import generate_gemini_response

        self.calls += 1
        result = generate_gemini_response(
            model=model, prompt=prompt, inline_pdf_b64=inline_pdf_b64, **kwargs
        )
        self.usages.append(dict(result.usage))
        return result.text


def summarize_usage(usages: list[dict[str, int]]) -> dict[str, int]:
    """Sum token counts across calls into prompt/output/total totals."""
    prompt_tokens = sum(int(u.get("promptTokenCount", 0) or 0) for u in usages)
    output_tokens = sum(int(u.get("candidatesTokenCount", 0) or 0) for u in usages)
    total_tokens = sum(
        int(u.get("totalTokenCount", 0) or 0) or
        (int(u.get("promptTokenCount", 0) or 0) + int(u.get("candidatesTokenCount", 0) or 0))
        for u in usages
    )
    return {
        "calls": len(usages),
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
