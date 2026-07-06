"""Tests that procedurally generated ships are valid and visually distinct."""

import pygame

from game import settings as cfg, sprites


def _raw(surface):
    return pygame.image.tostring(surface, "RGBA")


def test_enemy_kinds_have_distinct_silhouettes():
    first_frame = {k: sprites.make_enemy_variants(k, 1)[0][0] for k in cfg.ENEMY_KINDS}
    raws = {k: _raw(v) for k, v in first_frame.items()}
    assert len(set(raws.values())) == len(cfg.ENEMY_KINDS), "enemy types should not look identical"


def test_enemy_variants_differ_within_a_kind():
    variants = sprites.make_enemy_variants("shooter", 5)
    raws = {_raw(v[0]) for v in variants}
    assert len(raws) > 1, "variants of one kind should have colour/detail variation"


def test_enemy_sprites_are_correct_size():
    frames = sprites.make_enemy_variants("grunt", 1)[0]
    assert frames[0].get_size() == cfg.ENEMY_SIZE


def test_player_art_changes_with_weapon_level():
    lvl1 = _raw(sprites.make_player_frames(1)[0])
    lvl5 = _raw(sprites.make_player_frames(5)[0])
    assert lvl1 != lvl5, "upgraded ship should look different"


def test_all_boss_types_render_distinctly():
    imgs = {k: sprites.make_boss(k) for k in cfg.BOSS_SPECS}
    for img in imgs.values():
        assert img.get_size() == cfg.BOSS_SIZE
    assert len({_raw(v) for v in imgs.values()}) == len(cfg.BOSS_SPECS)


def test_generation_is_deterministic():
    a = _raw(sprites.make_boss("warlord"))
    b = _raw(sprites.make_boss("warlord"))
    assert a == b, "same input should generate the same sprite"
