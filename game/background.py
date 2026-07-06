"""Animated, parallax deep-space background.

Replaces the static image with a living starfield: several depth layers of
stars scroll at different speeds (parallax), brighter stars twinkle, a soft
nebula drifts behind everything, and shooting stars streak past now and then.
Everything is delta-time based so it moves at a constant real-world speed.
"""

from __future__ import annotations

import math
import random

import pygame

from game import settings as cfg


class Star:
    __slots__ = ("x", "y", "r", "speed", "base", "amp", "freq", "phase")

    def __init__(self, rng: random.Random, speed: float, r: int, base: int, twinkle: float):
        self.x = rng.uniform(0, cfg.WIDTH)
        self.y = rng.uniform(0, cfg.HEIGHT)
        self.r = r
        self.speed = speed
        self.base = base
        self.amp = twinkle
        self.freq = rng.uniform(1.5, 4.0)
        self.phase = rng.uniform(0, math.tau)

    def update(self, dt: float) -> None:
        self.y += self.speed * dt
        if self.y > cfg.HEIGHT + 2:
            self.y -= cfg.HEIGHT + 4
            self.x = random.uniform(0, cfg.WIDTH)

    def draw(self, win: pygame.Surface, t: float) -> None:
        b = self.base + self.amp * math.sin(t * self.freq + self.phase)
        c = max(0, min(255, int(b)))
        color = (c, c, min(255, c + 12))
        if self.r <= 1:
            win.set_at((int(self.x), int(self.y)), color)
        else:
            pygame.draw.circle(win, color, (int(self.x), int(self.y)), self.r)


class ShootingStar:
    __slots__ = ("x", "y", "vx", "vy", "life", "t")

    def __init__(self, rng: random.Random):
        self.x = rng.uniform(0, cfg.WIDTH * 0.8)
        self.y = rng.uniform(0, cfg.HEIGHT * 0.4)
        angle = rng.uniform(math.radians(20), math.radians(45))
        speed = rng.uniform(700, 1000)
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.life = rng.uniform(0.5, 0.9)
        self.t = 0.0

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.t += dt
        return self.t >= self.life or self.x > cfg.WIDTH or self.y > cfg.HEIGHT

    def draw(self, win: pygame.Surface) -> None:
        fade = max(0.0, 1.0 - self.t / self.life)
        tail = 26
        ex = self.x - self.vx * 0.02
        ey = self.y - self.vy * 0.02
        col = (int(200 * fade), int(220 * fade), int(255 * fade))
        pygame.draw.line(win, col, (int(ex), int(ey)), (int(self.x), int(self.y)), 2)
        pygame.draw.circle(win, (int(230 * fade), int(240 * fade), 255),
                           (int(self.x), int(self.y)), 2)


class Background:
    def __init__(self, seed: int = 1234):
        rng = random.Random(seed)
        self._t = 0.0
        self._h2 = cfg.HEIGHT * 2
        self._nebula = self._make_nebula(rng)
        self._scroll = 0.0
        self._neb_speed = 14.0

        # Parallax star layers (far -> near): slower/dimmer to faster/brighter.
        self.stars: list[Star] = []
        for _ in range(90):
            self.stars.append(Star(rng, speed=16, r=1, base=110, twinkle=35))
        for _ in range(55):
            self.stars.append(Star(rng, speed=38, r=1, base=160, twinkle=55))
        for _ in range(28):
            self.stars.append(Star(rng, speed=78, r=2, base=210, twinkle=45))

        self._shooters: list[ShootingStar] = []
        self._next_shooter = rng.uniform(2.0, 6.0)
        self._rng = rng

    @staticmethod
    def _soft_blob(color, size, max_alpha) -> pygame.Surface:
        """A small radial-falloff sprite, scaled up for a smooth nebula cloud."""
        s = 48
        g = pygame.Surface((s, s), pygame.SRCALPHA)
        c = s / 2
        for y in range(s):
            for x in range(s):
                d = math.hypot(x - c, y - c) / c
                if d < 1.0:
                    a = int(max_alpha * (1 - d) ** 2)
                    if a > 0:
                        g.set_at((x, y), (color[0], color[1], color[2], a))
        return pygame.transform.smoothscale(g, (int(size), int(size)))

    def _make_nebula(self, rng: random.Random) -> pygame.Surface:
        """A tall, vertically-seamless nebula surface to scroll behind stars."""
        surf = pygame.Surface((cfg.WIDTH, self._h2))
        # Seamless vertical gradient (periodic so top meets bottom cleanly).
        strip = pygame.Surface((1, self._h2))
        for y in range(self._h2):
            k = (math.sin(math.tau * y / self._h2) + 1) / 2
            strip.set_at((0, y), (int(7 + 6 * k), int(9 + 8 * k), int(20 + 16 * k)))
        surf.blit(pygame.transform.smoothscale(strip, (cfg.WIDTH, self._h2)), (0, 0))

        # Faint, soft nebula clouds (low alpha, big soft falloff).
        palettes = [(70, 45, 120), (35, 70, 130), (95, 45, 110), (30, 95, 115)]
        for _ in range(6):
            cx = rng.uniform(0, cfg.WIDTH)
            cy = rng.uniform(220, self._h2 - 220)
            size = rng.uniform(360, 620)
            color = rng.choice(palettes)
            blob = self._soft_blob(color, size, rng.uniform(26, 44))
            surf.blit(blob, (int(cx - size / 2), int(cy - size / 2)))
        return surf

    def update(self, dt: float) -> None:
        self._t += dt
        self._scroll = (self._scroll + self._neb_speed * dt) % self._h2
        for s in self.stars:
            s.update(dt)

        self._next_shooter -= dt
        if self._next_shooter <= 0:
            self._next_shooter = self._rng.uniform(3.0, 8.0)
            self._shooters.append(ShootingStar(self._rng))
        for sh in self._shooters[:]:
            if sh.update(dt):
                self._shooters.remove(sh)

    def draw(self, win: pygame.Surface) -> None:
        off = int(self._scroll)
        win.blit(self._nebula, (0, off - self._h2))
        win.blit(self._nebula, (0, off))
        for s in self.stars:
            s.draw(win, self._t)
        for sh in self._shooters:
            sh.draw(win)
