"""
Space Adventure — a classic arcade shooter built with pygame.

Fly your ship, blast waves of enemies, and chase a high score. The game is
frame-rate independent (movement is scaled by delta time), so it plays the
same on any machine, and every asset/audio load degrades gracefully instead
of crashing.

Controls
--------
    Arrow keys / WASD ... move
    Space .............. fire
    P .................. pause
    M .................. mute / unmute
    Enter .............. start / restart
    Esc / Q ............ quit

Run with:  python main.py
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import pygame

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
WIDTH, HEIGHT = 1280, 720
FPS = 60
CAPTION = "Space Adventure"

ASSET_DIR = Path(__file__).resolve().parent / "pic"
HIGHSCORE_FILE = Path(__file__).resolve().parent / "highscore.txt"

# Gameplay tuning (speeds are in pixels/second so they are FPS-independent).
PLAYER_SPEED = 420
BULLET_SPEED = 780
BULLET_COOLDOWN = 0.22          # seconds between shots
BULLET_RADIUS = 6
MAX_BULLETS = 12
START_LIVES = 3
INVULN_TIME = 1.4               # seconds of invulnerability after being hit
ANIM_INTERVAL = 0.05            # seconds per animation frame

ENEMY_BASE_SPEED = 170
ENEMY_SPEED_PER_WAVE = 28
ENEMY_BASE_HEALTH = 6
ENEMY_DESCEND = 26              # pixels dropped each time an enemy bounces
HIT_SCORE = 1
KILL_SCORE = 15

# Colors
WHITE = (245, 246, 250)
RED = (232, 65, 24)
GREEN = (68, 189, 50)
DARK = (12, 14, 28)
YELLOW = (251, 197, 49)
CYAN = (0, 200, 220)


# --------------------------------------------------------------------------- #
# Asset loading (fault tolerant)
# --------------------------------------------------------------------------- #
def load_image(name: str, size: tuple[int, int] | None = None) -> pygame.Surface:
    """Load an image, converting for fast blitting. Returns a placeholder
    surface if the file is missing so the game never hard-crashes on assets."""
    path = ASSET_DIR / name
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (pygame.error, FileNotFoundError):
        image = pygame.Surface((size or (64, 64)), pygame.SRCALPHA)
        image.fill((255, 0, 255, 160))
    if size is not None:
        image = pygame.transform.smoothscale(image, size)
    return image


class NullSound:
    """Stand-in used when audio is unavailable so calls are safe no-ops."""

    def play(self, *args, **kwargs) -> None:  # noqa: D401
        return None


def load_sound(name: str):
    """Load a sound effect, returning a silent stub if the mixer/file fails."""
    if not pygame.mixer.get_init():
        return NullSound()
    try:
        return pygame.mixer.Sound(str(ASSET_DIR / name))
    except (pygame.error, FileNotFoundError):
        return NullSound()


def load_frames(prefix: str, count: int, size: tuple[int, int]) -> list[pygame.Surface]:
    """Load an animation strip named e.g. s1..s9 / e1..e9."""
    frames = [load_image(f"{prefix}{i}.png", size) for i in range(1, count + 1)]
    return frames


def read_highscore() -> int:
    try:
        return int(HIGHSCORE_FILE.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return 0


def write_highscore(value: int) -> None:
    try:
        HIGHSCORE_FILE.write_text(str(int(value)), encoding="utf-8")
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Game objects
# --------------------------------------------------------------------------- #
class AnimatedSprite:
    """Small mixin providing time-based frame animation."""

    def __init__(self, frames: list[pygame.Surface]):
        self.frames = frames
        self._anim_time = 0.0
        self._frame = 0

    def advance_animation(self, dt: float, animate: bool = True) -> pygame.Surface:
        if animate and len(self.frames) > 1:
            self._anim_time += dt
            while self._anim_time >= ANIM_INTERVAL:
                self._anim_time -= ANIM_INTERVAL
                self._frame = (self._frame + 1) % len(self.frames)
        else:
            self._frame = 0
            self._anim_time = 0.0
        return self.frames[self._frame]


class Player(AnimatedSprite):
    def __init__(self, frames: list[pygame.Surface]):
        super().__init__(frames)
        self.width, self.height = frames[0].get_size()
        self.reset()

    def reset(self) -> None:
        self.x = float(WIDTH // 2 - self.width // 2)
        self.y = float(HEIGHT - self.height - 20)
        self.invuln = 0.0
        self.moving = False

    @property
    def rect(self) -> pygame.Rect:
        # Slightly inset hitbox so collisions feel fair.
        return pygame.Rect(int(self.x) + 12, int(self.y) + 8, self.width - 24, self.height - 16)

    @property
    def gun_x(self) -> int:
        return int(self.x + self.width / 2)

    def hit(self) -> None:
        self.invuln = INVULN_TIME

    def update(self, dt: float, keys) -> None:
        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= PLAYER_SPEED * dt
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += PLAYER_SPEED * dt
            moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= PLAYER_SPEED * dt
            moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += PLAYER_SPEED * dt
            moving = True

        # Clamp to the screen so the ship can never leave the play field.
        self.x = max(5, min(self.x, WIDTH - self.width - 5))
        self.y = max(HEIGHT // 2, min(self.y, HEIGHT - self.height - 5))
        self.moving = moving

        if self.invuln > 0:
            self.invuln = max(0.0, self.invuln - dt)

    def draw(self, win: pygame.Surface, dt: float) -> None:
        image = self.advance_animation(dt, animate=self.moving)
        # Flash while invulnerable (skip drawing on alternate ticks).
        if self.invuln > 0 and int(self.invuln * 12) % 2 == 0:
            return
        win.blit(image, (int(self.x), int(self.y)))


class Enemy(AnimatedSprite):
    def __init__(self, frames: list[pygame.Surface], x: float, y: float, speed: float, health: int):
        super().__init__(frames)
        self.width, self.height = frames[0].get_size()
        self.x = float(x)
        self.y = float(y)
        self.vel_x = speed if random.random() < 0.5 else -speed
        self.max_health = health
        self.health = health

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int = 1) -> None:
        self.health -= amount

    def update(self, dt: float) -> bool:
        """Move the enemy. Returns True if it reached the bottom edge."""
        self.x += self.vel_x * dt
        if self.x <= 5:
            self.x = 5
            self.vel_x = abs(self.vel_x)
            self.y += ENEMY_DESCEND
        elif self.x + self.width >= WIDTH - 5:
            self.x = WIDTH - self.width - 5
            self.vel_x = -abs(self.vel_x)
            self.y += ENEMY_DESCEND
        return self.y + self.height >= HEIGHT - 90

    def draw(self, win: pygame.Surface, dt: float) -> None:
        image = self.advance_animation(dt)
        win.blit(image, (int(self.x), int(self.y)))
        # Health bar
        bar_w = self.width
        pct = max(0.0, self.health / self.max_health)
        pygame.draw.rect(win, RED, (int(self.x), int(self.y) - 12, bar_w, 6))
        pygame.draw.rect(win, GREEN, (int(self.x), int(self.y) - 12, int(bar_w * pct), 6))


class Bullet:
    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int):
        self.x = float(x)
        self.y = float(y)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - BULLET_RADIUS, int(self.y) - BULLET_RADIUS,
                           BULLET_RADIUS * 2, BULLET_RADIUS * 2)

    def update(self, dt: float) -> bool:
        """Move up. Returns True when off-screen and should be culled."""
        self.y -= BULLET_SPEED * dt
        return self.y < -BULLET_RADIUS

    def draw(self, win: pygame.Surface) -> None:
        pygame.draw.circle(win, YELLOW, (int(self.x), int(self.y)), BULLET_RADIUS)
        pygame.draw.circle(win, WHITE, (int(self.x), int(self.y)), BULLET_RADIUS - 3)


# --------------------------------------------------------------------------- #
# Game
# --------------------------------------------------------------------------- #
class Game:
    STATE_START = "start"
    STATE_PLAYING = "playing"
    STATE_PAUSED = "paused"
    STATE_OVER = "over"

    def __init__(self) -> None:
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(CAPTION)
        icon = load_image("icon.png", (32, 32))
        pygame.display.set_icon(icon)

        # Assets
        self.bg = load_image("bg.jpg", (WIDTH, HEIGHT))
        self.ship_frames = load_frames("s", 9, (72, 72))
        self.enemy_frames = load_frames("e", 9, (72, 72))
        self.fire_sound = load_sound("fire.wav")
        self.hit_sound = load_sound("hit.wav")
        self.font_big = pygame.font.Font(None, 96)
        self.font_mid = pygame.font.Font(None, 52)
        self.font_small = pygame.font.Font(None, 34)

        self._music_ok = False
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(str(ASSET_DIR / "bgg.mp3"))
                pygame.mixer.music.set_volume(0.4)
                self._music_ok = True
            except pygame.error:
                self._music_ok = False

        self.clock = pygame.time.Clock()
        self.muted = False
        self.high_score = read_highscore()
        self.player = Player(self.ship_frames)
        self.state = self.STATE_START
        self.reset()

    # -- state ------------------------------------------------------------- #
    def reset(self) -> None:
        self.player.reset()
        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.score = 0
        self.lives = START_LIVES
        self.wave = 0
        self._fire_timer = 0.0
        self.spawn_wave()

    def spawn_wave(self) -> None:
        self.wave += 1
        count = min(2 + self.wave, 8)
        speed = ENEMY_BASE_SPEED + ENEMY_SPEED_PER_WAVE * (self.wave - 1)
        health = ENEMY_BASE_HEALTH + (self.wave - 1)
        for i in range(count):
            x = random.randint(20, WIDTH - 92)
            y = 40 + (i % 3) * 90
            self.enemies.append(Enemy(self.enemy_frames, x, y, speed, health))

    def start_game(self) -> None:
        self.reset()
        self.state = self.STATE_PLAYING
        self.play_music()

    # -- audio ------------------------------------------------------------- #
    def play_music(self) -> None:
        if self._music_ok and not self.muted:
            try:
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass

    def toggle_mute(self) -> None:
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

    # -- input ------------------------------------------------------------- #
    def handle_events(self) -> bool:
        """Process the event queue. Returns False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
                if event.key == pygame.K_m:
                    self.toggle_mute()
                if self.state in (self.STATE_START, self.STATE_OVER) and event.key in (
                    pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                ):
                    self.start_game()
                elif self.state == self.STATE_PLAYING and event.key == pygame.K_p:
                    self.state = self.STATE_PAUSED
                elif self.state == self.STATE_PAUSED and event.key == pygame.K_p:
                    self.state = self.STATE_PLAYING
        return True

    def fire(self) -> None:
        if self._fire_timer <= 0 and len(self.bullets) < MAX_BULLETS:
            self.bullets.append(Bullet(self.player.gun_x, int(self.player.y)))
            self._fire_timer = BULLET_COOLDOWN
            self._sfx(self.fire_sound)

    # -- update ------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        if self._fire_timer > 0:
            self._fire_timer = max(0.0, self._fire_timer - dt)
        if keys[pygame.K_SPACE]:
            self.fire()

        # Bullets (iterate over a copy so we can cull safely).
        for bullet in self.bullets[:]:
            if bullet.update(dt):
                self.bullets.remove(bullet)

        # Enemies
        for enemy in self.enemies[:]:
            reached_bottom = enemy.update(dt)
            if reached_bottom:
                self.enemies.remove(enemy)
                self.damage_player()
                continue

            # Bullet collisions
            for bullet in self.bullets[:]:
                if enemy.rect.colliderect(bullet.rect):
                    self.bullets.remove(bullet)
                    enemy.take_damage()
                    self._sfx(self.hit_sound)
                    self.score += HIT_SCORE
                    if not enemy.alive:
                        self.score += KILL_SCORE
                        if enemy in self.enemies:
                            self.enemies.remove(enemy)
                    break

            # Player collision
            if enemy.alive and enemy in self.enemies and self.player.invuln <= 0:
                if enemy.rect.colliderect(self.player.rect):
                    self.enemies.remove(enemy)
                    self.damage_player()

        if not self.enemies:
            self.spawn_wave()

    def damage_player(self) -> None:
        self.lives -= 1
        self.player.hit()
        if self.lives <= 0:
            self.game_over()

    def game_over(self) -> None:
        self.state = self.STATE_OVER
        if self.score > self.high_score:
            self.high_score = self.score
            write_highscore(self.high_score)
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()

    # -- render ------------------------------------------------------------ #
    def _text(self, text: str, font, color, center) -> None:
        surface = font.render(text, True, color)
        self.win.blit(surface, surface.get_rect(center=center))

    def draw_hud(self) -> None:
        self.win.blit(self.font_small.render(f"Score: {self.score}", True, WHITE), (16, 14))
        self.win.blit(self.font_small.render(f"Wave: {self.wave}", True, CYAN), (16, 48))
        hs = self.font_small.render(f"High: {self.high_score}", True, YELLOW)
        self.win.blit(hs, (WIDTH - hs.get_width() - 16, 14))
        # Lives as small ship icons
        for i in range(self.lives):
            self.win.blit(pygame.transform.smoothscale(self.ship_frames[0], (28, 28)),
                          (WIDTH - 40 - i * 34, 50))
        if self.muted:
            self.win.blit(self.font_small.render("MUTED", True, RED), (WIDTH // 2 - 40, 14))

    def draw(self, dt: float) -> None:
        self.win.blit(self.bg, (0, 0))

        if self.state == self.STATE_START:
            self._text(CAPTION, self.font_big, WHITE, (WIDTH // 2, HEIGHT // 2 - 90))
            self._text("Press ENTER to play", self.font_mid, YELLOW, (WIDTH // 2, HEIGHT // 2))
            self._text("Arrows/WASD move   -   Space shoot   -   P pause   -   M mute   -   Q quit",
                       self.font_small, WHITE, (WIDTH // 2, HEIGHT // 2 + 70))
            self._text(f"High score: {self.high_score}", self.font_small, CYAN,
                       (WIDTH // 2, HEIGHT // 2 + 120))
        else:
            for enemy in self.enemies:
                enemy.draw(self.win, dt)
            for bullet in self.bullets:
                bullet.draw(self.win)
            self.player.draw(self.win, dt)
            self.draw_hud()

            if self.state == self.STATE_PAUSED:
                self._dim()
                self._text("PAUSED", self.font_big, WHITE, (WIDTH // 2, HEIGHT // 2 - 20))
                self._text("Press P to resume", self.font_mid, YELLOW, (WIDTH // 2, HEIGHT // 2 + 60))
            elif self.state == self.STATE_OVER:
                self._dim()
                self._text("GAME OVER", self.font_big, RED, (WIDTH // 2, HEIGHT // 2 - 70))
                self._text(f"Score: {self.score}    High: {self.high_score}", self.font_mid,
                           WHITE, (WIDTH // 2, HEIGHT // 2))
                self._text("Press ENTER to play again   -   Q to quit", self.font_small,
                           YELLOW, (WIDTH // 2, HEIGHT // 2 + 60))

        pygame.display.flip()

    def _dim(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*DARK, 180))
        self.win.blit(overlay, (0, 0))

    # -- main loop --------------------------------------------------------- #
    def run(self, max_frames: int | None = None, screenshot: str | None = None) -> None:
        running = True
        frame = 0
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # clamp to avoid tunneling after a long stall
            running = self.handle_events()

            if self.state == self.STATE_PLAYING:
                self.update(dt)
            self.draw(dt)

            frame += 1
            if screenshot and frame == max(1, (max_frames or 1) - 1):
                pygame.image.save(self.win, screenshot)
            if max_frames is not None and frame >= max_frames:
                running = False


def main() -> None:
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # No audio device (e.g. CI/headless) — the game still runs silently.

    game = Game()

    # Optional headless self-test / screenshot hooks (used by CI, harmless otherwise).
    max_frames = int(os.environ.get("SELFTEST_FRAMES", "0")) or None
    screenshot = os.environ.get("SELFTEST_SCREENSHOT") or None
    if max_frames or screenshot:
        game.start_game()

    try:
        game.run(max_frames=max_frames, screenshot=screenshot)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
    sys.exit(0)
