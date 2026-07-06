"""Main game orchestration: state machine, waves, combat, and persistence."""

from __future__ import annotations

import math
import os
import random

import pygame

from game import assets, settings as cfg, savegame, ui
from game.entities import Boss, Bullet, Enemy, Explosion, Player, PowerUp


# States
MENU, PLAYING, PAUSED, GAME_OVER = "menu", "playing", "paused", "game_over"


def weighted_choice(weights: dict[str, int]) -> str:
    total = sum(weights.values())
    roll = random.uniform(0, total)
    upto = 0.0
    for key, w in weights.items():
        upto += w
        if roll <= upto:
            return key
    return next(iter(weights))


class Game:
    def __init__(self) -> None:
        self.win = pygame.display.set_mode((cfg.WIDTH, cfg.HEIGHT))
        pygame.display.set_caption(cfg.CAPTION)
        pygame.display.set_icon(assets.load_image("icon.png", (32, 32)))

        # --- assets ---
        self.bg = assets.load_image("bg.jpg", (cfg.WIDTH, cfg.HEIGHT))
        self.ship_frames = assets.load_frames("s", 9, cfg.PLAYER_SIZE)
        self.ship_icon = pygame.transform.smoothscale(self.ship_frames[0], (28, 28))
        self.enemy_frames = {
            kind: assets.load_frames("e", 9, cfg.ENEMY_SIZE, spec["tint"])
            for kind, spec in cfg.ENEMY_KINDS.items()
        }
        self.boss_images = {
            kind: assets.load_image("e1.png", cfg.BOSS_SIZE, tint=spec["tint"])
            for kind, spec in cfg.BOSS_SPECS.items()
        }
        self.fire_sound = assets.load_sound("fire.wav")
        self.hit_sound = assets.load_sound("hit.wav")
        self._music_ok = assets.load_music("bgg.mp3")

        # --- fonts ---
        self.f_title = assets.font(110)
        self.f_big = assets.font(84)
        self.f_mid = assets.font(52)
        self.f_small = assets.font(34)
        self.f_tiny = assets.font(26)

        self.clock = pygame.time.Clock()
        self.muted = False
        self.high_score = savegame.read_highscore()

        self.player = Player(self.ship_frames)
        self.main_menu = ui.Menu(self._main_menu_items())
        self.pause_menu = ui.Menu([("resume", "Resume"),
                                   ("save_quit", "Save & Quit to Menu"),
                                   ("quit", "Quit Game")])
        self.over_menu = ui.Menu([("restart", "Play Again"),
                                  ("menu", "Main Menu"),
                                  ("quit", "Quit Game")])
        self.state = MENU
        self._init_run_state()

    # ------------------------------------------------------------------ #
    # Run / wave setup
    # ------------------------------------------------------------------ #
    def _main_menu_items(self):
        items = [("new", "New Game")]
        if savegame.has_save():
            items.append(("continue", "Continue"))
        items.append(("quit", "Quit"))
        return items

    def _init_run_state(self) -> None:
        self.player.reset()
        self.enemies: list[Enemy] = []
        self.boss: Boss | None = None
        self.player_bullets: list[Bullet] = []
        self.enemy_bullets: list[Bullet] = []
        self.powerups: list[PowerUp] = []
        self.explosions: list[Explosion] = []
        self.score = 0
        self.lives = cfg.START_LIVES
        self.wave = 0
        self.group_dir = 1
        self.dive_timer = cfg.DIVE_INTERVAL

    def new_game(self) -> None:
        savegame.delete_save()
        self._init_run_state()
        self.state = PLAYING
        self._next_wave()
        self._play_music()

    def continue_game(self) -> None:
        data = savegame.load_game()
        if not data:
            self.new_game()
            return
        self._init_run_state()
        self.score = int(data.get("score", 0))
        self.lives = max(1, int(data.get("lives", cfg.START_LIVES)))
        self.high_score = max(self.high_score, int(data.get("high", 0)))
        self.wave = max(0, int(data.get("wave", 1)) - 1)  # _next_wave increments
        self.state = PLAYING
        self._next_wave()
        self.player.weapon_level = max(1, min(cfg.MAX_WEAPON_LEVEL,
                                              int(data.get("weapon", 1))))
        self._play_music()

    def _next_wave(self) -> None:
        self.wave += 1
        self.enemies.clear()
        self.boss = None
        self.group_dir = 1
        self.dive_timer = max(1.0, cfg.DIVE_INTERVAL - 0.15 * self.wave)

        if self.wave % cfg.BOSS_EVERY == 0:
            tier = self.wave // cfg.BOSS_EVERY
            kind = cfg.BOSS_KINDS[(tier - 1) % len(cfg.BOSS_KINDS)]
            self.boss = Boss(self.boss_images[kind], tier, kind)
            return

        count = min(6 + self.wave * 2, 24)
        cols = min(8, count)
        rows = math.ceil(count / cols)
        margin = 130
        gap_x = (cfg.WIDTH - 2 * margin) / max(1, cols - 1) if cols > 1 else 0
        placed = 0
        for r in range(rows):
            for c in range(cols):
                if placed >= count:
                    break
                x = margin + c * gap_x
                y = 70 + r * 84
                kind = self._pick_kind(r)
                self.enemies.append(Enemy(self.enemy_frames[kind], x, y, kind, self.wave))
                placed += 1

    def _pick_kind(self, row: int) -> str:
        pool = ["grunt"]
        if self.wave >= 2:
            pool += ["shooter", "shooter"]
        if self.wave >= 3:
            pool += ["diver"]
        if self.wave >= 4:
            pool += ["shooter", "diver"]
        if self.wave >= 6:
            pool += ["tank"]          # tough enemies join the deeper waves
        if self.wave >= 9:
            pool += ["tank", "diver"]
        return random.choice(pool)

    # ------------------------------------------------------------------ #
    # Audio
    # ------------------------------------------------------------------ #
    def _play_music(self) -> None:
        if self._music_ok and not self.muted:
            try:
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def _stop_music(self) -> None:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        if not pygame.mixer.get_init():
            return
        if self.muted:
            pygame.mixer.music.pause()
        elif self._music_ok:
            pygame.mixer.music.unpause()

    def _sfx(self, sound) -> None:
        if not self.muted:
            sound.play()

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_m:
                self._toggle_mute()

            if self.state == MENU:
                if not self._menu_input(self.main_menu, event):
                    return False
            elif self.state == PLAYING:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.pause_menu.index = 0
                    self.state = PAUSED
            elif self.state == PAUSED:
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.state = PLAYING
                elif not self._menu_input(self.pause_menu, event):
                    return False
            elif self.state == GAME_OVER:
                if not self._menu_input(self.over_menu, event):
                    return False
        return True

    def _menu_input(self, menu: ui.Menu, event) -> bool:
        """Drive a menu. Returns False only when the action is to quit."""
        if event.key in (pygame.K_UP, pygame.K_w):
            menu.move(-1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            menu.move(1)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return self._menu_action(menu.select())
        elif event.key == pygame.K_q:
            return False
        return True

    def _menu_action(self, action: str) -> bool:
        if action == "quit":
            return False
        if action == "new" or action == "restart":
            self.new_game()
        elif action == "continue":
            self.continue_game()
        elif action == "resume":
            self.state = PLAYING
        elif action == "save_quit":
            self._save_and_menu()
        elif action == "menu":
            self._to_menu()
        return True

    def _save_and_menu(self) -> None:
        savegame.save_game({"score": self.score, "wave": self.wave,
                            "lives": self.lives, "high": self.high_score,
                            "weapon": self.player.weapon_level})
        self._to_menu()

    def _to_menu(self) -> None:
        self._stop_music()
        self.main_menu.set_items(self._main_menu_items())
        self.main_menu.index = 0
        self.state = MENU

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        if keys[pygame.K_SPACE] and self.player.can_fire() \
                and len(self.player_bullets) < cfg.MAX_PLAYER_BULLETS:
            self.player_bullets.extend(self.player.fire())
            self._sfx(self.fire_sound)

        self._update_bullets(dt)
        self._update_enemies(dt)
        self._update_boss(dt)
        self._update_powerups(dt)
        for ex in self.explosions[:]:
            if ex.update(dt):
                self.explosions.remove(ex)

        self._collide_player_bullets()
        self._collide_enemy_bullets()
        self._collide_bodies()

        # Wave cleared?
        if not self.enemies and self.boss is None:
            self.score += cfg.WAVE_CLEAR_BONUS
            self._next_wave()

    def _update_bullets(self, dt: float) -> None:
        for b in self.player_bullets[:]:
            if b.update(dt):
                self.player_bullets.remove(b)
        for b in self.enemy_bullets[:]:
            if b.update(dt):
                self.enemy_bullets.remove(b)

    def _update_enemies(self, dt: float) -> None:
        formation = [e for e in self.enemies if e.state == "formation"]
        drift = cfg.ENEMY_DRIFT_SPEED + cfg.ENEMY_DRIFT_PER_WAVE * (self.wave - 1)
        speed = cfg.ENEMY_BASE_SPEED + cfg.ENEMY_SPEED_PER_WAVE * (self.wave - 1)

        descend = False
        if formation:
            min_x = min(e.x for e in formation)
            max_x = max(e.x + e.width for e in formation)
            step = self.group_dir * speed * dt
            if self.group_dir > 0 and max_x + step >= cfg.WIDTH - 5:
                self.group_dir = -1
                descend = True
            elif self.group_dir < 0 and min_x + step <= 5:
                self.group_dir = 1
                descend = True
        group_dx = self.group_dir * speed * dt

        player_pos = (self.player.x + self.player.width / 2, self.player.y)
        for e in self.enemies[:]:
            e.update_formation(dt, group_dx, drift)
            if descend and e.state == "formation":
                e.y += cfg.ENEMY_EDGE_DESCEND
            bullet = e.maybe_shoot(dt, player_pos)
            if bullet:
                self.enemy_bullets.append(bullet)
            # Breached the floor line -> costs the player a life.
            if e.y + e.height >= cfg.ENEMY_FLOOR:
                self.enemies.remove(e)
                self.explosions.append(Explosion(e.x + e.width / 2, e.y + e.height / 2, cfg.RED))
                self._damage_player()

        # Trigger dive-bombs.
        self.dive_timer -= dt
        if self.dive_timer <= 0:
            self.dive_timer = max(0.9, cfg.DIVE_INTERVAL - 0.15 * self.wave)
            candidates = [e for e in self.enemies if e.state == "formation"]
            divers = [e for e in candidates if e.kind == "diver"] or candidates
            if divers:
                random.choice(divers).start_dive(*player_pos)

    def _update_boss(self, dt: float) -> None:
        if self.boss is None:
            return
        self.boss.update(dt)
        player_pos = (self.player.x + self.player.width / 2, self.player.y)
        if self.boss.ready_attack():
            self.enemy_bullets.extend(self.boss.do_attack(player_pos))
        if self.boss.ready_spawn() and len(self.enemies) < 6:
            x = random.randint(120, cfg.WIDTH - 200)
            self.enemies.append(Enemy(self.enemy_frames["shooter"], x, 150, "shooter", self.wave))

    def _update_powerups(self, dt: float) -> None:
        for p in self.powerups[:]:
            if p.update(dt):
                self.powerups.remove(p)
                continue
            if p.rect.colliderect(self.player.rect):
                self.powerups.remove(p)
                self._collect(p.kind)

    # ------------------------------------------------------------------ #
    # Collisions
    # ------------------------------------------------------------------ #
    def _collide_player_bullets(self) -> None:
        for b in self.player_bullets[:]:
            hit = False
            for e in self.enemies[:]:
                if e.rect.colliderect(b.rect):
                    e.take_damage(b.damage)
                    self._sfx(self.hit_sound)
                    self.score += 1
                    hit = True
                    if not e.alive:
                        self._kill_enemy(e, drop=True)
                    break
            if hit:
                self.player_bullets.remove(b)
                continue
            if self.boss and self.boss.rect.colliderect(b.rect):
                self.boss.take_damage(b.damage)
                self._sfx(self.hit_sound)
                self.score += 1
                self.player_bullets.remove(b)
                if not self.boss.alive:
                    self._kill_boss()

    def _collide_enemy_bullets(self) -> None:
        if self.player.invuln > 0:
            return
        for b in self.enemy_bullets[:]:
            if b.rect.colliderect(self.player.rect):
                self.enemy_bullets.remove(b)
                self._damage_player()
                break

    def _collide_bodies(self) -> None:
        if self.player.invuln > 0:
            return
        prect = self.player.rect
        for e in self.enemies[:]:
            if e.rect.colliderect(prect):
                self._kill_enemy(e, drop=False)
                self._damage_player()
                return
        if self.boss and self.boss.rect.colliderect(prect):
            self._damage_player()

    def _kill_enemy(self, enemy: Enemy, drop: bool) -> None:
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        self.score += enemy.points
        self.explosions.append(Explosion(enemy.x + enemy.width / 2, enemy.y + enemy.height / 2))
        if drop and random.random() < cfg.POWERUP_DROP_CHANCE:
            self.powerups.append(PowerUp(enemy.x + enemy.width / 2,
                                         enemy.y + enemy.height / 2,
                                         weighted_choice(cfg.POWERUP_WEIGHTS)))

    def _kill_boss(self) -> None:
        if self.boss is None:
            return
        self.score += self.boss.points
        for i in range(6):
            self.explosions.append(Explosion(
                self.boss.x + random.randint(0, self.boss.width),
                self.boss.y + random.randint(0, self.boss.height),
                random.choice((cfg.ORANGE, cfg.YELLOW, cfg.RED)), size=60))
        # Guaranteed reward for beating a boss.
        self.powerups.append(PowerUp(self.boss.x + self.boss.width / 2,
                                     self.boss.y + self.boss.height / 2,
                                     weighted_choice(cfg.POWERUP_WEIGHTS)))
        self.boss = None

    def _damage_player(self) -> None:
        if self.player.invuln > 0:
            return
        if self.player.shielded:
            self.player.shield_t = 0.0
            self.player.invuln = 0.7
            self.explosions.append(Explosion(*self.player.gun, cfg.CYAN))
            return
        self.lives -= 1
        self.player.hit()
        self.explosions.append(Explosion(self.player.x + self.player.width / 2,
                                         self.player.y + self.player.height / 2, cfg.RED))
        if self.lives <= 0:
            self._game_over()

    def _collect(self, kind: str) -> None:
        if kind in ("rapid", "multi", "shield", "upgrade"):
            self.player.apply(kind)
        elif kind == "life":
            self.lives = min(cfg.MAX_LIVES, self.lives + 1)
        elif kind == "score":
            self.score += cfg.SCORE_BONUS
        elif kind == "bomb":
            self.enemy_bullets.clear()
            for e in self.enemies[:]:
                e.take_damage(3)
                if not e.alive:
                    self._kill_enemy(e, drop=False)
            if self.boss:
                self.boss.take_damage(6)
                if not self.boss.alive:
                    self._kill_boss()

    def _game_over(self) -> None:
        self.state = GAME_OVER
        self.over_menu.index = 0
        savegame.delete_save()
        if self.score > self.high_score:
            self.high_score = self.score
            savegame.write_highscore(self.high_score)
        self._stop_music()

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def draw(self, dt: float) -> None:
        self.win.blit(self.bg, (0, 0))
        if self.state == MENU:
            self._draw_menu()
        else:
            self._draw_world(dt)
            if self.state == PAUSED:
                self._draw_pause()
            elif self.state == GAME_OVER:
                self._draw_game_over()
        pygame.display.flip()

    def _draw_menu(self) -> None:
        cx = cfg.WIDTH // 2
        ui.draw_center_text(self.win, cfg.CAPTION, self.f_title, cfg.WHITE, cx, 150)
        ui.draw_center_text(self.win, "Boss fights - power-ups - endless waves",
                            self.f_small, cfg.CYAN, cx, 225)
        self.main_menu.draw(self.win, self.f_mid, cx, 340)
        ui.draw_center_text(self.win, f"High Score: {self.high_score}",
                            self.f_small, cfg.YELLOW, cx, 560)
        ui.draw_center_text(self.win,
                            "Arrows/WASD move   Space shoot   P pause   M mute   Enter select",
                            self.f_tiny, cfg.GREY, cx, 660)

    def _draw_world(self, dt: float) -> None:
        for e in self.enemies:
            e.draw(self.win, dt)
        if self.boss:
            self.boss.draw(self.win)
            ui.draw_center_text(self.win, self.boss.name, self.f_tiny,
                                cfg.WHITE, cfg.WIDTH // 2, 46)
        for p in self.powerups:
            p.draw(self.win, self.f_tiny)
        for b in self.enemy_bullets:
            b.draw(self.win)
        for b in self.player_bullets:
            b.draw(self.win)
        for ex in self.explosions:
            ex.draw(self.win)
        self.player.draw(self.win, dt)
        ui.draw_hud(self.win, (self.f_small, self.f_tiny), self.player,
                    self.score, self.wave, self.lives, self.high_score,
                    self.ship_icon, self.muted)

    def _draw_pause(self) -> None:
        ui.draw_dim(self.win)
        cx = cfg.WIDTH // 2
        ui.draw_center_text(self.win, "PAUSED", self.f_big, cfg.WHITE, cx, 210)
        self.pause_menu.draw(self.win, self.f_mid, cx, 340)

    def _draw_game_over(self) -> None:
        ui.draw_dim(self.win)
        cx = cfg.WIDTH // 2
        ui.draw_center_text(self.win, "GAME OVER", self.f_big, cfg.RED, cx, 180)
        ui.draw_center_text(self.win, f"Score: {self.score}    High: {self.high_score}",
                            self.f_mid, cfg.WHITE, cx, 260)
        self.over_menu.draw(self.win, self.f_mid, cx, 360)

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self, max_frames: int | None = None, screenshot: str | None = None) -> None:
        running = True
        frame = 0
        while running:
            dt = min(self.clock.tick(cfg.FPS) / 1000.0, 0.05)
            running = self.handle_events()
            if self.state == PLAYING:
                self.update(dt)
            self.draw(dt)

            frame += 1
            if screenshot and frame == max(1, (max_frames or 2) - 1):
                pygame.image.save(self.win, screenshot)
            if max_frames is not None and frame >= max_frames:
                running = False


def main() -> None:
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # No audio device (headless/CI) — the game still runs silently.

    game = Game()

    max_frames = int(os.environ.get("SELFTEST_FRAMES", "0")) or None
    screenshot = os.environ.get("SELFTEST_SCREENSHOT") or None
    if max_frames or screenshot:
        game.new_game()

    try:
        game.run(max_frames=max_frames, screenshot=screenshot)
    finally:
        pygame.quit()
