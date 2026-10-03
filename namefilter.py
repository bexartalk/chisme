"""v49.12 (legal audit M5/M6): the public high-score board's name filter. The list lives in static/name_blocklist.json so
the phone (static/juan.js) checks the very same words before posting; the server is the one that decides."""
from __future__ import annotations

import json
import pathlib
import re
import unicodedata

_LIST = json.loads((pathlib.Path(__file__).resolve().parent / "static" / "name_blocklist.json").read_text(encoding="utf-8"))
CONTAINS = tuple(_LIST["contains"])
WORDS = frozenset(_LIST["words"])
_LEET = str.maketrans({"0": "o", "1": "i", "!": "i", "|": "i", "3": "e", "4": "a", "@": "a", "5": "s", "$": "s", "7": "t", "8": "b", "9": "g"})


def _base(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c)).translate(_LEET)
    return s


def _squeeze(s: str) -> str:
    return re.sub(r"(.)\1+", r"\1", s)


def blocked(name: str) -> bool:
    """True if a name can't go on the public board (slurs, the worst profanity, in English or Spanish)."""
    b = _base(name)
    joined = re.sub(r"[^a-z]", "", b)
    if any(w in joined or w in _squeeze(joined) for w in CONTAINS):
        return True
    words = [w for w in re.split(r"[^a-z]+", b) if w]
    return any(w in WORDS or _squeeze(w) in WORDS for w in words) or joined in WORDS or _squeeze(joined) in WORDS
