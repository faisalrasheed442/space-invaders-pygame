"""Game entities: Player, Bullet, Enemy, Boss, PowerUp and Explosion.

All motion is delta-time based (pixels/second) so behaviour is identical at
any frame rate.
"""

from __future__ import annotations

import math
import random

import pygame

from game import settings as cfg


class AnimatedSprite:
    """Time-based frame animation shared by ships and enemies."""

    def __init__(self, frames: list[pygame.Surface]):
        self.frames = frames
        self._t = 0.0
        self._i = 0

    def frame(self, dt: float, animate: bool = True) -> pygame.Surface:
        if animate and len(self.frames) > 1:
            self._t += dt
            while self._t >= cfg.ANIM_INTERVAL:
                self._t -= cfg.ANIM_INTERVAL
                self._i = (self._i + 1) % len(self.frames)
        else:
            self._i = 0
            self._t = 0.0
        return self.frames[self._i]


# --------------------------------------------------------------------------- #
# Bullets
# --------------------------------------------------------------------------- #
class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "radius", "color", "friendly", "damage")

    def __init__(self, x, y, vy, color, radius, friendly, vx=0.0, damage=1):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = radius
        self.color = color
        self.friendly = friendly
        self.damage = damage

    @property
    def rect(self) -> pygame.Rect:
        r = self.radius
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def update(self, dt: float) -> bool:
        """Move; return True when off-screen and ready to cull."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        return (self.y < -20 or self.y > cfg.HEIGHT + 20
                or self.x < -20 or self.x > cfg.WIDTH + 20)

    def draw(self, win: pygame.Surface) -> None:
        pygame.draw.circle(win, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(win, cfg.WHITE, (int(self.x), int(self.y)), max(1, self.radius - 3))


# --------------------------------------------------------------------------- #
# Player
# --------------------------------------------------------------------------- #
# Bullet streams per effective weapon level: (x_offset, angle_velocity).
# Higher levels add more streams and wider spread.
WEAPON_STREAMS = {
    1: [(0, 0.0)],
    2: [(-16, 0.0), (16, 0.0)],
    3: [(0, 0.0), (-18, -1.0), (18, 1.0)],
    4: [(-16, 0.0), (16, 0.0), (-26, -1.0), (26, 1.0)],
    5: [(0, 0.0), (-16, 0.0), (16, 0.0), (-30, -1.4), (30, 1.4)],
}


class Player(AnimatedSprite):
    def __init__(self, frames: list[pygame.Surface]):
        super().__init__(frames)
        self.width, self.height = frames[0].get_size()
        self.weapon_level = 1
        self.reset()

    def reset(self) -> None:
        self.x = float(cfg.WIDTH // 2 - self.width // 2)
        self.y = float(cfg.HEIGHT - self.height - 24)
        self.invuln = 0.0
        self.moving = False
        self._cooldown = 0.0
        self.rapid_t = 0.0
        self.multi_t = 0.0
        self.shield_t = 0.0
        self.weapon_level = 1

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) + 12, int(self.y) + 8,
                           self.width - 24, self.height - 16)

    @property
    def gun(self) -> tuple[int, int]:
        return int(self.x + self.width / 2), int(self.y + 4)

    @property
    def shielded(self) -> bool:
        return self.shield_t > 0

    def hit(self) -> None:
        self.invuln = cfg.INVULN_TIME
        # Losing a life knocks the weapon down a level (never below 1).
        self.weapon_level = max(1, self.weapon_level - 1)

    def apply(self, kind: str) -> None:
        if kind == "rapid":
            self.rapid_t = cfg.POWERUP_DURATION
        elif kind == "multi":
            self.multi_t = cfg.POWERUP_DURATION
        elif kind == "shield":
            self.shield_t = cfg.POWERUP_DURATION
        elif kind == "upgrade":
            self.weapon_level = min(cfg.MAX_WEAPON_LEVEL, self.weapon_level + 1)

    def can_fire(self) -> bool:
        return self._cooldown <= 0

    @property
    def effective_level(self) -> int:
        """Weapon level plus a temporary Multi-Shot boost."""
        boost = 1 if self.multi_t > 0 else 0
        return min(cfg.MAX_WEAPON_LEVEL, self.weapon_level + boost)

    def fire(self) -> list[Bullet]:
        self._cooldown = cfg.RAPID_FIRE_COOLDOWN if self.rapid_t > 0 else cfg.PLAYER_FIRE_COOLDOWN
        gx, gy = self.gun
        speed = cfg.PLAYER_BULLET_SPEED
        level = self.effective_level
        damage = 2 if self.weapon_level >= cfg.WEAPON_HEAVY_LEVEL else 1
        radius = cfg.PLAYER_BULLET_RADIUS + (1 if damage > 1 else 0)
        color = cfg.ORANGE if damage > 1 else cfg.YELLOW
        bullets = []
        for x_off, ang in WEAPON_STREAMS[level]:
            bullets.append(Bullet(gx + x_off, gy, -speed, color, radius, True,
                                  vx=ang * cfg.MULTISHOT_SPREAD, damage=damage))
        return bullets

    def update(self, dt: float, keys) -> None:
        moving = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= cfg.PLAYER_SPEED * dt; moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += cfg.PLAYER_SPEED * dt; moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= cfg.PLAYER_SPEED * dt; moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += cfg.PLAYER_SPEED * dt; moving = True

        self.x = max(5, min(self.x, cfg.WIDTH - self.width - 5))
        self.y = max(cfg.HEIGHT // 2, min(self.y, cfg.HEIGHT - self.height - 5))
        self.moving = moving

        for attr in ("invuln", "rapid_t", "multi_t", "shield_t", "_cooldown"):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, max(0.0, v - dt))

    def draw(self, win: pygame.Surface, dt: float) -> None:
        image = self.frame(dt, animate=self.moving)
        if self.invuln > 0 and int(self.invuln * 12) % 2 == 0:
            return  # flash while invulnerable
        win.blit(image, (int(self.x), int(self.y)))
        if self.shielded:
            cx, cy = int(self.x + self.width / 2), int(self.y + self.height / 2)
            radius = int(self.width * 0.7)
            alpha = 90 + int(60 * abs(math.sin(self.shield_t * 6)))
            ring = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*cfg.CYAN, alpha), (radius, radius), radius, 4)
            win.blit(ring, (cx - radius, cy - radius))


# --------------------------------------------------------------------------- #
# Enemy
# --------------------------------------------------------------------------- #
class Enemy(AnimatedSprite):
    def __init__(self, frames, x, y, kind: str, wave: int):
        super().__init__(frames)
        spec = cfg.ENEMY_KINDS[kind]
        self.width, self.height = frames[0].get_size()
        self.kind = kind
        self.home_x = float(x)          # formation anchor
        self.x = float(x)
        self.y = float(y)
        self.max_health = spec["health"] + wave // 3
        self.health = self.max_health
        self.points = spec["points"]
        self.can_shoot = spec["can_shoot"]
        self.state = "formation"        # or "diving"
        self.dive_vx = 0.0
        self.dive_vy = 0.0
        self._shoot_timer = random.uniform(1.0, cfg.SHOOTER_FIRE_INTERVAL)

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    @property
    def alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int = 1) -> None:
        self.health -= amount

    def start_dive(self, target_x: float, target_y: float) -> None:
        self.state = "diving"
        dx, dy = target_x - self.x, target_y - self.y
        dist = max(1.0, math.hypot(dx, dy))
        self.dive_vx = cfg.DIVE_SPEED * dx / dist
        self.dive_vy = cfg.DIVE_SPEED * abs(dy) / dist

    def update_formation(self, dt: float, group_dx: float, drift: float) -> None:
        """Move as part of the formation. group_dx already includes dt."""
        if self.state == "formation":
            self.home_x += group_dx
            self.x = self.home_x
            self.y += drift * dt
        else:  # diving
            self.x += self.dive_vx * dt
            self.y += self.dive_vy * dt
            if self.y > cfg.HEIGHT + self.height:      # wrap back to the top
                self.state = "formation"
                self.y = -self.height
                self.home_x = self.x = max(10, min(self.x, cfg.WIDTH - self.width - 10))

    def maybe_shoot(self, dt: float, player_pos) -> Bullet | None:
        if not self.can_shoot or self.state != "formation":
            return None
        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = random.uniform(cfg.SHOOTER_FIRE_INTERVAL * 0.6,
                                               cfg.SHOOTER_FIRE_INTERVAL * 1.4)
            px, py = player_pos
            cx = self.x + self.width / 2
            cy = self.y + self.height
            dx = px - cx
            dist = max(1.0, math.hypot(dx, py - cy))
            vx = cfg.ENEMY_BULLET_SPEED * 0.5 * dx / dist
            return Bullet(cx, cy, cfg.ENEMY_BULLET_SPEED, cfg.RED,
                          cfg.ENEMY_BULLET_RADIUS, False, vx=vx)
        return None

    def draw(self, win: pygame.Surface, dt: float) -> None:
        win.blit(self.frame(dt), (int(self.x), int(self.y)))
        if self.health < self.max_health:
            w = self.width
            pct = max(0.0, self.health / self.max_health)
            pygame.draw.rect(win, cfg.RED, (int(self.x), int(self.y) - 10, w, 5))
            pygame.draw.rect(win, cfg.GREEN, (int(self.x), int(self.y) - 10, int(w * pct), 5))


# --------------------------------------------------------------------------- #
# Boss
# --------------------------------------------------------------------------- #
class Boss:
    def __init__(self, image: pygame.Surface, tier: int, kind: str):
        spec = cfg.BOSS_SPECS[kind]
        self.image = image
        self.kind = kind
        self.name = spec["name"]
        self.patterns = spec["patterns"]
        self.width, self.height = image.get_size()
        self.x = float(cfg.WIDTH // 2 - self.width // 2)
        self.y = 60.0
        self.base_y = self.y
        self.max_health = cfg.BOSS_HEALTH_BASE + cfg.BOSS_HEALTH_PER_TIER * (tier - 1)
        self.health = self.max_health
        self.points = cfg.BOSS_POINTS * tier
        self._t = 0.0
        self._attack_timer = cfg.BOSS_ATTACK_INTERVAL
        self._spawn_timer = cfg.BOSS_SPAWN_INTERVAL * spec["spawn_mult"]
        self._spawn_interval = cfg.BOSS_SPAWN_INTERVAL * spec["spawn_mult"]
        self._pattern_idx = 0
        self._spiral = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) + 10, int(self.y) + 10,
                           self.width - 20, self.height - 20)

    @property
    def alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int = 1) -> None:
        self.health -= amount

    def update(self, dt: float) -> None:
        self._t += dt
        self.x = (cfg.WIDTH / 2 - self.width / 2) + math.sin(self._t * 0.9) * (cfg.WIDTH / 2 - self.width)
        self.y = self.base_y + math.sin(self._t * 1.7) * 24
        self._attack_timer -= dt
        self._spawn_timer -= dt

    def ready_attack(self) -> bool:
        return self._attack_timer <= 0

    def do_attack(self, player_pos) -> list[Bullet]:
        self._attack_timer = cfg.BOSS_ATTACK_INTERVAL
        pattern = self.patterns[self._pattern_idx % len(self.patterns)]
        self._pattern_idx += 1
        speed = cfg.ENEMY_BULLET_SPEED
        cx = self.x + self.width / 2
        cy = self.y + self.height
        bullets: list[Bullet] = []

        if pattern == "spread":
            for angle in range(-60, 61, 20):
                rad = math.radians(angle)
                bullets.append(Bullet(cx, cy, speed * math.cos(rad), cfg.PURPLE,
                                      cfg.ENEMY_BULLET_RADIUS, False, vx=speed * math.sin(rad)))
        elif pattern == "aimed":
            px, py = player_pos
            dx, dy = px - cx, max(1.0, py - cy)
            dist = math.hypot(dx, dy)
            for spread in (-0.15, 0.0, 0.15):
                bullets.append(Bullet(cx, cy, speed * dy / dist, cfg.RED,
                                      cfg.ENEMY_BULLET_RADIUS, False,
                                      vx=speed * (dx / dist + spread)))
        elif pattern == "rain":
            for i in range(7):
                x = self.width / 6 * i + self.x
                bullets.append(Bullet(x, cy, speed * 0.9, cfg.BLUE,
                                      cfg.ENEMY_BULLET_RADIUS, False))
        elif pattern == "spiral":
            self._spiral += 0.6
            for k in range(6):
                rad = self._spiral + k * (math.pi / 3)
                bullets.append(Bullet(cx, cy, speed * math.cos(rad) * 0.7 + speed * 0.4,
                                      cfg.ORANGE, cfg.ENEMY_BULLET_RADIUS, False,
                                      vx=speed * math.sin(rad)))
        return bullets

    def ready_spawn(self) -> bool:
        if self._spawn_timer <= 0:
            self._spawn_timer = self._spawn_interval
            return True
        return False

    def draw(self, win: pygame.Surface) -> None:
        win.blit(self.image, (int(self.x), int(self.y)))
        # Big health bar pinned to the top of the screen.
        bar_w, bar_h = cfg.WIDTH - 200, 16
        bx, by = 100, 18
        pct = max(0.0, self.health / self.max_health)
        pygame.draw.rect(win, (60, 20, 20), (bx, by, bar_w, bar_h))
        pygame.draw.rect(win, cfg.RED, (bx, by, int(bar_w * pct), bar_h))
        pygame.draw.rect(win, cfg.WHITE, (bx, by, bar_w, bar_h), 2)


# --------------------------------------------------------------------------- #
# Power-up
# --------------------------------------------------------------------------- #
class PowerUp:
    def __init__(self, x, y, kind: str):
        self.x = float(x)
        self.y = float(y)
        self.kind = kind
        self.label, self.color = cfg.POWERUPS[kind]
        self.size = cfg.POWERUP_SIZE
        self._t = 0.0

    @property
    def rect(self) -> pygame.Rect:
        s = self.size
        return pygame.Rect(int(self.x) - s // 2, int(self.y) - s // 2, s, s)

    def update(self, dt: float) -> bool:
        self.y += cfg.POWERUP_FALL_SPEED * dt
        self._t += dt
        return self.y > cfg.HEIGHT + self.size

    def draw(self, win: pygame.Surface, font: pygame.font.Font) -> None:
        s = self.size
        bob = int(math.sin(self._t * 5) * 2)
        cx, cy = int(self.x), int(self.y) + bob
        pygame.draw.rect(win, self.color, (cx - s // 2, cy - s // 2, s, s), border_radius=8)
        pygame.draw.rect(win, cfg.WHITE, (cx - s // 2, cy - s // 2, s, s), 2, border_radius=8)
        glyph = font.render(self.label, True, cfg.BLACK)
        win.blit(glyph, glyph.get_rect(center=(cx, cy)))


# --------------------------------------------------------------------------- #
# Explosion (visual juice)
# --------------------------------------------------------------------------- #
class Explosion:
    def __init__(self, x, y, color=cfg.ORANGE, size=42):
        self.x = x
        self.y = y
        self.color = color
        self.max = size
        self.t = 0.0
        self.life = 0.35

    def update(self, dt: float) -> bool:
        self.t += dt
        return self.t >= self.life

    def draw(self, win: pygame.Surface) -> None:
        p = self.t / self.life
        radius = int(self.max * p)
        alpha = max(0, int(220 * (1 - p)))
        surf = pygame.Surface((self.max * 2, self.max * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.max, self.max), radius, 4)
        pygame.draw.circle(surf, (*cfg.YELLOW, alpha), (self.max, self.max), max(1, radius // 2))
        win.blit(surf, (int(self.x) - self.max, int(self.y) - self.max))
