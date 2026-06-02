"""Guardrails: PII redaction before web research, and price-consistency checking.

These are deliberately small, pure, and independently testable so they can be
wired into agents as callbacks with a single line each.
"""
from __future__ import annotations

import re
from typing import Any, Optional

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Loose international/!local phone matcher (7+ digits with separators).
_PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{6,}\d)(?!\w)")


def redact_pii(text: str) -> str:
    """Replace emails and phone numbers with placeholders.

    Used before sending inquiry text to external web search so client contact
    details never leave the system via a search query.
    """
    if not text:
        return text
    text = _EMAIL_RE.sub("[redacted-email]", text)
    text = _PHONE_RE.sub("[redacted-phone]", text)
    return text


def make_pii_redaction_callback():
    """Return a `before_model_callback` that redacts PII from outgoing contents.

    Attach to the Researcher agent so the model (and any search query it emits)
    never sees raw client emails/phones.
    """

    def _callback(callback_context: Any, llm_request: Any):  # -> Optional[LlmResponse]
        contents = getattr(llm_request, "contents", None) or []
        for content in contents:
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    part.text = redact_pii(part.text)
        return None  # proceed with the (now redacted) request

    return _callback


def check_price_consistency(
    estimate: Optional[dict], proposal: Optional[dict], price_field: str = "price_band_usd"
) -> tuple[bool, str]:
    """Verify the proposal's quoted price band matches the deterministic estimate.

    The proposal text must contain BOTH the rubric's band low and high numbers.
    Returns (ok, message). Never raises — callers decide how to react.
    """
    if not estimate or not proposal:
        return False, "Missing estimate or proposal; cannot verify price."
    low = estimate.get("price_band_low_usd")
    high = estimate.get("price_band_high_usd")
    quoted = str(proposal.get(price_field, ""))
    digits = set(re.findall(r"\d+", quoted.replace(",", "")))
    ok = str(low) in digits and str(high) in digits
    if ok:
        return True, f"Price OK: band ${low:,}-${high:,} matches proposal."
    return (
        False,
        f"PRICE MISMATCH: estimate band ${low:,}-${high:,} not both present in "
        f"proposal {price_field}={quoted!r}.",
    )


if __name__ == "__main__":
    # PII redaction
    sample = "Reach Sarah at sarah.kim@tutorloop.io or +1 (415) 555-0199 today."
    red = redact_pii(sample)
    assert "tutorloop.io" not in red and "555-0199" not in red, red
    assert "[redacted-email]" in red and "[redacted-phone]" in red, red

    # Price consistency
    est = {"price_band_low_usd": 21500, "price_band_high_usd": 26500}
    ok, _ = check_price_consistency(est, {"price_band_usd": "$21,500 - $26,500"})
    assert ok
    bad_ok, msg = check_price_consistency(est, {"price_band_usd": "$30,000 - $40,000"})
    assert not bad_ok
    print("guardrails self-test passed:", red, "|", msg)
