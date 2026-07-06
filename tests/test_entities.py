"""Unit tests for standalone entity behaviour."""

import pygame

from game import settings as cfg
from game.entities import Bullet, Explosion, PowerUp


def test_bullet_moves_and_culls_offscreen():
    b = Bullet(100, 100, -cfg.PLAYER_BULLET_SPEED, cfg.YELLOW, 6, True)
    assert b.update(0.01) is False          # still on screen after a short step
    b.y = -100
    assert b.update(0.01) is True           # off the top -> cull

    side = Bullet(-100, 300, 0, cfg.RED, 6, False, vx=-100)
    assert side.update(0.5) is True         # off the left edge -> cull


def test_bullet_damage_default_and_override():
    assert Bullet(0, 0, -1, cfg.YELLOW, 6, True).damage == 1
    assert Bullet(0, 0, -1, cfg.ORANGE, 7, True, damage=2).damage == 2


def test_bullet_rect_is_centered():
    b = Bullet(200, 150, -1, cfg.YELLOW, 6, True)
    r = b.rect
    assert r.centerx == 200 and r.centery == 150
    assert r.width == 12 and r.height == 12


def test_powerup_falls_and_culls_at_bottom():
    p = PowerUp(100, cfg.HEIGHT - 5, "rapid")
    assert p.kind == "rapid"
    culled = False
    for _ in range(200):
        if p.update(1 / 60):
            culled = True
            break
    assert culled, "power-up should eventually fall off the bottom"


def test_explosion_expires():
    ex = Explosion(50, 50)
    done = False
    for _ in range(120):
        if ex.update(1 / 60):
            done = True
            break
    assert done, "explosion should finish its lifetime"
