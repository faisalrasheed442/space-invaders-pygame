"""Persistent save/continue and high-score storage (JSON + plain text)."""

from __future__ import annotations

import json

from game import settings as cfg


def has_save() -> bool:
    return cfg.SAVE_FILE.exists()


def save_game(data: dict) -> bool:
    try:
        cfg.SAVE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def load_game() -> dict | None:
    try:
        data = json.loads(cfg.SAVE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return None


def delete_save() -> None:
    try:
        cfg.SAVE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def read_highscore() -> int:
    try:
        return int(cfg.HIGHSCORE_FILE.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def write_highscore(value: int) -> None:
    try:
        cfg.HIGHSCORE_FILE.write_text(str(int(value)), encoding="utf-8")
    except OSError:
        pass
