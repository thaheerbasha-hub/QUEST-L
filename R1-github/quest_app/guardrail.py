"""
quest_app/guardrail.py - Bridge to root guardrail.py
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from guardrail import (
    DISCLAIMER,
    regex_check,
    second_check,
    rewrite,
    safe_reply,
    build_scripted_fallback,
)

__all__ = [
    "DISCLAIMER",
    "regex_check",
    "second_check",
    "rewrite",
    "safe_reply",
    "build_scripted_fallback",
]
