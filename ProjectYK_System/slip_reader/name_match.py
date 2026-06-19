from __future__ import annotations
from difflib import SequenceMatcher

# Above this char-similarity, an OCR'd name is treated as the same person as a
# roster name. Tuned so common Thai OCR typos (วิไรจน์→วิโรจน์) match while
# genuinely different names don't.
_THRESHOLD = 0.6


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def best_name_match(ocr_name: str, roster: list[str]):
    """Return the roster name closest to the OCR'd recipient, or None.

    The roster is the correctly-spelled driver names (from the day's work-plan).
    Tries: exact first-name, then substring, then fuzzy ratio. Returns the
    roster's canonical spelling so a slightly-misread name still gets corrected.
    """
    name = (ocr_name or "").strip()
    if not name or not roster:
        return None
    first = name.split()[0] if name.split() else name
    # 1) exact match on full or first token
    for r in roster:
        if r == name or r == first:
            return r
    # 2) substring either way (roster has first name, OCR has full name or vice versa)
    for r in roster:
        if r and (r in name or r in first or first in r):
            return r
    # 3) fuzzy: best ratio against first token, above threshold
    best, best_score = None, 0.0
    for r in roster:
        score = max(_similarity(first, r), _similarity(name, r))
        if score > best_score:
            best, best_score = r, score
    return best if best_score >= _THRESHOLD else None
