"""Club registry. Resolves API-Football ids and common names onto our ids."""

from __future__ import annotations

from typing import Any


class ClubRegistry:
    def __init__(self, clubs: dict[str, dict[str, Any]]):
        self.clubs = clubs
        self._by_api: dict[int, str] = {}
        self._by_name: dict[str, str] = {}
        for cid, club in clubs.items():
            self._by_name[cid.lower()] = cid
            self._by_name[club.get("name", "").lower()] = cid
            for alias in club.get("aliases") or []:
                self._by_name[str(alias).lower()] = cid
            api_id = club.get("api_football_id")
            if api_id:
                self._by_api[int(api_id)] = cid

    def resolve(self, key: Any) -> str | None:
        if key is None:
            return None
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            return self._by_api.get(int(key))
        text = str(key).strip()
        if text in self.clubs:
            return text
        return self._by_name.get(text.lower())

    def api_id(self, club_id: str | None) -> int | None:
        if not club_id or club_id not in self.clubs:
            return None
        api_id = self.clubs[club_id].get("api_football_id")
        return int(api_id) if api_id else None
