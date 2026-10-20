"""Club registry. Resolves API-Football ids and common names onto our ids."""

from __future__ import annotations

import unicodedata
from typing import Any

_STROKE = str.maketrans({"ø": "o", "Ø": "o", "đ": "d", "ł": "l", "ß": "ss", "ı": "i"})
_PREFIXES = ("fc ", "fk ", "cf ", "ac ", "as ", "ssc ", "rsc ", "afc ")


def fold_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.translate(_STROKE))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().replace("-", " ").split())


class ClubRegistry:
    def __init__(self, clubs: dict[str, dict[str, Any]]):
        self.clubs = clubs
        self._by_api: dict[int, str] = {}
        self._by_name: dict[str, str] = {}
        for cid, club in clubs.items():
            self._add_name(cid, cid)
            self._add_name(club.get("name", ""), cid)
            for alias in club.get("aliases") or []:
                self._add_name(str(alias), cid)
            api_id = club.get("api_football_id")
            if api_id:
                self._by_api[int(api_id)] = cid

    def _add_name(self, text: str, cid: str) -> None:
        folded = fold_name(text)
        if folded:
            self._by_name[folded] = cid

    def resolve(self, key: Any) -> str | None:
        if key is None:
            return None
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            return self._by_api.get(int(key))
        text = str(key).strip()
        if text in self.clubs:
            return text
        folded = fold_name(text)
        hit = self._by_name.get(folded)
        if hit:
            return hit
        for prefix in _PREFIXES:
            if folded.startswith(prefix):
                hit = self._by_name.get(folded[len(prefix):])
                if hit:
                    return hit
        if folded.endswith(" fc"):
            return self._by_name.get(folded[:-3].strip())
        return None

    def api_id(self, club_id: str | None) -> int | None:
        if not club_id or club_id not in self.clubs:
            return None
        api_id = self.clubs[club_id].get("api_football_id")
        return int(api_id) if api_id else None
