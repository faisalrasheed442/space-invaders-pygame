"""Tests for the animated starfield background."""

import pygame

from game import settings as cfg
from game.background import Background, ShootingStar


def test_background_updates_and_draws_without_error():
    bg = Background()
    surf = pygame.Surface((cfg.WIDTH, cfg.HEIGHT))
    for _ in range(200):
        bg.update(1 / 60)
        bg.draw(surf)


def test_stars_stay_on_screen_after_scrolling():
    bg = Background()
    for _ in range(600):          # 10 seconds of scrolling
        bg.update(1 / 60)
    for s in bg.stars:
        assert -5 <= s.y <= cfg.HEIGHT + 5


def test_shooting_stars_expire():
    import random
    sh = ShootingStar(random.Random(0))
    done = False
    for _ in range(120):
        if sh.update(1 / 60):
            done = True
            break
    assert done


def test_background_is_deterministic_for_a_seed():
    a = Background(seed=42)
    b = Background(seed=42)
    assert [round(s.x) for s in a.stars] == [round(s.x) for s in b.stars]
