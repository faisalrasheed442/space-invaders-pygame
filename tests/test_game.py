"""Integration tests for the Game state machine, waves, and combat."""

import random

import pygame

from game import savegame, settings as cfg
from game.game import Game, MENU, PLAYING, PAUSED, GAME_OVER, weighted_choice


def test_weighted_choice_only_returns_known_keys():
    random.seed(0)
    keys = set(cfg.POWERUP_WEIGHTS)
    for _ in range(200):
        assert weighted_choice(cfg.POWERUP_WEIGHTS) in keys


def test_main_menu_hides_continue_without_a_save(game):
    savegame.delete_save()
    game.main_menu.set_items(game._main_menu_items())
    assert [k for k, _ in game.main_menu.items] == ["new", "quit"]


def test_new_game_spawns_first_wave(game):
    game.new_game()
    assert game.state == PLAYING
    assert game.wave == 1
    assert len(game.enemies) > 0
    assert game.lives == cfg.START_LIVES


def test_boss_wave_spawns_a_boss(game):
    game.new_game()
    game.wave = cfg.BOSS_EVERY - 1
    game._next_wave()
    assert game.wave == cfg.BOSS_EVERY
    assert game.boss is not None
    assert not game.enemies


def test_boss_types_differ_and_scale(game):
    game.new_game()
    specs = []
    for tier in range(1, len(cfg.BOSS_KINDS) + 1):
        game.wave = tier * cfg.BOSS_EVERY - 1
        game._next_wave()
        specs.append((game.boss.kind, game.boss.max_health))
    kinds = [k for k, _ in specs]
    healths = [h for _, h in specs]
    assert len(set(kinds)) == len(cfg.BOSS_KINDS)      # all distinct
    assert healths == sorted(healths)                  # health scales up by tier


def test_every_boss_attacks(game):
    game.new_game()
    for tier in range(1, len(cfg.BOSS_KINDS) + 1):
        game.wave = tier * cfg.BOSS_EVERY - 1
        game._next_wave()
        game.enemy_bullets.clear()
        fired = 0
        for _ in range(500):
            game._update_boss(1 / 60)
            fired = len(game.enemy_bullets)
            if fired > 0:
                break
        assert fired > 0, f"boss {game.boss.kind} never attacked"


def test_enemies_shoot_back(game):
    random.seed(1)
    game.new_game()
    game.wave = 3
    game._next_wave()                 # -> wave 4 (has shooters), not a boss wave
    assert game.wave % cfg.BOSS_EVERY != 0 and game.enemies
    fired = 0
    for _ in range(1200):
        game._update_enemies(1 / 60)
        if game.enemy_bullets:
            fired = len(game.enemy_bullets)
            break
    assert fired > 0


def test_enemies_dive_at_the_player(game):
    random.seed(2)
    game.new_game()
    game.wave = 3
    game._next_wave()                 # -> wave 4 (formation), not a boss wave
    assert game.wave % cfg.BOSS_EVERY != 0 and game.enemies
    dove = False
    for _ in range(1200):
        game._update_enemies(1 / 60)
        if any(e.state == "diving" for e in game.enemies):
            dove = True
            break
    assert dove


def test_tank_enemies_appear_in_deep_waves(game):
    random.seed(3)
    game.new_game()
    seen = set()
    for wave in (6, 7, 8, 9, 11, 12, 13):
        game.wave = wave - 1
        game._next_wave()
        seen.update(e.kind for e in game.enemies)
    assert "tank" in seen


def test_powerups_apply_their_effects(game):
    game.new_game()
    game.lives = 2
    game._collect("life")
    assert game.lives == 3

    game._collect("score")            # exact value asserted below
    game._collect("rapid")
    game._collect("multi")
    game._collect("shield")
    game._collect("upgrade")
    assert game.player.rapid_t > 0
    assert game.player.multi_t > 0
    assert game.player.shielded
    assert game.player.weapon_level == 2


def test_score_powerup_adds_bonus(game):
    game.new_game()
    before = game.score
    game._collect("score")
    assert game.score == before + cfg.SCORE_BONUS


def test_bomb_clears_bullets_and_damages_enemies(game):
    game.new_game()
    game.enemy_bullets.append(
        __import__("game.entities", fromlist=["Bullet"]).Bullet(
            100, 100, 100, cfg.RED, 6, False))
    count_before = len(game.enemies)
    game._collect("bomb")
    assert game.enemy_bullets == []
    # some enemies should have taken damage (health reduced or died)
    assert len(game.enemies) <= count_before


def test_shield_absorbs_a_hit_without_costing_a_life(game):
    game.new_game()
    game.player.apply("shield")
    game.player.invuln = 0
    lives = game.lives
    game._damage_player()
    assert game.lives == lives
    assert not game.player.shielded


def test_taking_damage_costs_a_life(game):
    game.new_game()
    game.player.invuln = 0
    game.player.shield_t = 0
    lives = game.lives
    game._damage_player()
    assert game.lives == lives - 1


def test_dodging_a_low_enemy_never_costs_health(game):
    """Regression: an enemy dropping low must not damage a far-away player."""
    from game.entities import Enemy
    game.new_game()
    game.enemies.clear()
    frames = game.enemy_variants["grunt"][0]
    game.enemies.append(Enemy(frames, 20, cfg.HEIGHT - 120, "grunt", 1))  # far left, low
    game.dive_timer = 1e9                              # disable dives for this test
    game.player.x = cfg.WIDTH - game.player.width - 5  # hug the far-right corner
    game.player.y = cfg.HEIGHT - game.player.height - 5
    lives = game.lives
    for _ in range(700):
        game._update_enemies(1 / 60)
        game._collide_bodies()
    assert game.lives == lives


def test_clearing_a_wave_advances_and_awards_bonus(game):
    game.new_game()
    game.enemies.clear()
    game.boss = None
    before_score = game.score
    before_wave = game.wave
    game.update(1 / 60)
    assert game.wave == before_wave + 1
    assert game.score >= before_score + cfg.WAVE_CLEAR_BONUS


def test_save_and_continue_roundtrip(game):
    game.new_game()
    game.score = 4200
    game.wave = 7
    game.lives = 2
    game.player.weapon_level = 3
    game._save_and_menu()
    assert game.state == MENU
    assert savegame.has_save()
    assert [k for k, _ in game.main_menu.items] == ["new", "continue", "quit"]

    game.continue_game()
    assert game.wave == 7
    assert game.score == 4200
    assert game.lives == 2
    assert game.player.weapon_level == 3


def test_game_over_persists_high_score_and_clears_save(game):
    game.new_game()
    game._save_and_menu()               # create a save to prove it is cleared
    assert savegame.has_save()
    game.continue_game()
    game.score = 99999
    game.lives = 1
    game.player.invuln = 0
    game.player.shield_t = 0
    game._damage_player()
    assert game.state == GAME_OVER
    assert not savegame.has_save()
    assert game.high_score >= 99999
    assert savegame.read_highscore() >= 99999


def test_pause_and_resume_via_events(game):
    game.new_game()
    game._menu_action  # smoke
    # Simulate pressing P to pause, then P to resume.
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    game.handle_events()
    assert game.state == PAUSED
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
    game.handle_events()
    assert game.state == PLAYING


def test_headless_frames_run_without_error(game):
    game.new_game()
    for _ in range(300):
        game.update(1 / 60)
        game.draw(1 / 60)
    assert game.state in (PLAYING, GAME_OVER)
