"""Tests for the player ship and its weapon-upgrade system."""

from game import settings as cfg, sprites
from game.entities import Player


def make_player():
    frames = {lvl: sprites.make_player_frames(lvl)
              for lvl in range(1, cfg.MAX_WEAPON_LEVEL + 1)}
    return Player(frames)


def test_player_starts_at_weapon_level_one():
    p = make_player()
    assert p.weapon_level == 1
    assert len(p.fire()) == 1


def test_upgrades_add_bullet_streams_up_to_max():
    p = make_player()
    counts = []
    for _ in range(cfg.MAX_WEAPON_LEVEL + 2):   # over-apply to prove the cap
        counts.append(len(p.fire()))
        p.apply("upgrade")
    assert p.weapon_level == cfg.MAX_WEAPON_LEVEL
    assert counts[0] == 1
    assert max(counts) == 5                     # top tier fires 5 streams


def test_heavy_weapon_deals_extra_damage():
    p = make_player()
    for _ in range(cfg.WEAPON_HEAVY_LEVEL - 1):
        p.apply("upgrade")
    assert p.fire()[0].damage == 2


def test_getting_hit_drops_one_weapon_level():
    p = make_player()
    for _ in range(4):
        p.apply("upgrade")
    assert p.weapon_level == 5
    p.hit()
    assert p.weapon_level == 4
    assert p.invuln > 0


def test_weapon_never_drops_below_one():
    p = make_player()
    p.hit()
    p.hit()
    assert p.weapon_level == 1


def test_multishot_temporarily_boosts_effective_level():
    p = make_player()
    base = p.effective_level
    p.apply("multi")
    assert p.effective_level == min(cfg.MAX_WEAPON_LEVEL, base + 1)


def test_buffs_expire_over_time():
    p = make_player()
    p.apply("rapid")
    p.apply("shield")
    assert p.rapid_t > 0 and p.shielded

    class Keys:
        def __getitem__(self, _):
            return False

    for _ in range(int(cfg.POWERUP_DURATION * 60) + 5):
        p.update(1 / 60, Keys())
    assert p.rapid_t == 0 and not p.shielded


def test_player_stays_within_bounds():
    p = make_player()

    class HeldLeft:
        def __getitem__(self, key):
            import pygame
            return key in (pygame.K_LEFT, pygame.K_UP)

    for _ in range(600):
        p.update(1 / 60, HeldLeft())
    assert p.x >= 5
    assert p.y >= cfg.HEIGHT // 2
