"""Shared pytest fixtures.

Runs pygame fully headless (dummy video/audio) and isolates the save and
high-score files into a temp dir so tests never touch real player data.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def _isolate_saves(tmp_path, monkeypatch):
    from game import settings as cfg
    monkeypatch.setattr(cfg, "SAVE_FILE", tmp_path / "savegame.json")
    monkeypatch.setattr(cfg, "HIGHSCORE_FILE", tmp_path / "highscore.txt")


@pytest.fixture
def game():
    from game.game import Game
    return Game()
