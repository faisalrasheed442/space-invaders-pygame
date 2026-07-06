"""Procedural sprite generation.

Every ship in the game is drawn from scratch here with pygame's vector
primitives — no two enemy archetypes share a silhouette, and each instance
gets small random colour/detail variation so a wave never looks copy-pasted.
The player ship is redrawn per weapon level so upgrades are visible.

Sprites are drawn on a supersampled canvas and smooth-scaled down for clean,
anti-aliased edges.
"""

from __future__ import annotations

import random

import pygame

from game import settings as cfg

SS = 3  # supersample factor


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def _canvas(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)


def _down(surf: pygame.Surface, w: int, h: int) -> pygame.Surface:
    return pygame.transform.smoothscale(surf, (w, h))


def _poly(surf, color, pts) -> None:
    pygame.draw.polygon(surf, color, [(int(x), int(y)) for x, y in pts])


def _circle(surf, color, x, y, r) -> None:
    pygame.draw.circle(surf, color, (int(x), int(y)), int(r))


def _ellipse(surf, color, x, y, w, h) -> None:
    pygame.draw.ellipse(surf, color, (int(x), int(y), int(w), int(h)))


def _rrect(surf, color, x, y, w, h, radius) -> None:
    pygame.draw.rect(surf, color, (int(x), int(y), int(w), int(h)), border_radius=int(radius))


def _shift_hue(color, deg, s_mul=1.0, v_mul=1.0):
    c = pygame.Color(int(color[0]), int(color[1]), int(color[2]))
    h, s, v, a = c.hsva
    c.hsva = ((h + deg) % 360, max(0.0, min(100.0, s * s_mul)),
              max(0.0, min(100.0, v * v_mul)), 100.0)
    return (c.r, c.g, c.b)


def _lighten(color, f):
    return tuple(min(255, int(c + (255 - c) * f)) for c in color)


def _darken(color, f):
    return tuple(max(0, int(c * (1 - f))) for c in color)


def _seed_for(name: str) -> int:
    return sum(ord(ch) for ch in name)     # deterministic, no PYTHONHASHSEED effect


# --------------------------------------------------------------------------- #
# Player ship (upgrades with weapon level)
# --------------------------------------------------------------------------- #
# Accent colour brightens/heats up as the ship is upgraded.
_PLAYER_ACCENT = {
    1: (52, 152, 219),
    2: (26, 188, 156),
    3: (241, 196, 15),
    4: (230, 126, 34),
    5: (231, 76, 60),
}


def _draw_player(s, W, H, level, flame) -> None:
    cx = W / 2
    hull = (214, 219, 230)
    accent = _PLAYER_ACCENT[level]

    # Engine nozzles scale with level.
    if level <= 1:
        nozzles = [cx]
    elif level <= 3:
        nozzles = [cx - W * 0.12, cx + W * 0.12]
    else:
        nozzles = [cx - W * 0.22, cx, cx + W * 0.22]

    # Flames (behind hull).
    flen = (0.20 if flame else 0.12) * H
    for nx in nozzles:
        _poly(s, (255, 170, 40), [(nx - W * 0.05, H * 0.80), (nx + W * 0.05, H * 0.80),
                                  (nx, H * 0.80 + flen)])
        _poly(s, (255, 240, 160), [(nx - W * 0.022, H * 0.80), (nx + W * 0.022, H * 0.80),
                                   (nx, H * 0.80 + flen * 0.6)])

    # Wings.
    _poly(s, accent, [(cx - W * 0.12, H * 0.50), (cx - W * 0.38, H * 0.80), (cx - W * 0.12, H * 0.80)])
    _poly(s, accent, [(cx + W * 0.12, H * 0.50), (cx + W * 0.38, H * 0.80), (cx + W * 0.12, H * 0.80)])

    if level >= 3:  # extra top fins
        _poly(s, _darken(accent, 0.25), [(cx - W * 0.12, H * 0.44), (cx - W * 0.24, H * 0.30),
                                         (cx - W * 0.12, H * 0.56)])
        _poly(s, _darken(accent, 0.25), [(cx + W * 0.12, H * 0.44), (cx + W * 0.24, H * 0.30),
                                         (cx + W * 0.12, H * 0.56)])

    if level >= 4:  # side cannons
        for sx in (-1, 1):
            _rrect(s, _darken(hull, 0.3), cx + sx * W * 0.30 - W * 0.025, H * 0.40,
                   W * 0.05, H * 0.30, W * 0.02)
            _circle(s, accent, cx + sx * W * 0.30, H * 0.40, W * 0.03)

    # Fuselage.
    _poly(s, hull, [(cx, H * 0.05), (cx + W * 0.14, H * 0.50),
                    (cx + W * 0.11, H * 0.82), (cx - W * 0.11, H * 0.82),
                    (cx - W * 0.14, H * 0.50)])
    _poly(s, _lighten(hull, 0.35), [(cx, H * 0.05), (cx + W * 0.06, H * 0.32), (cx - W * 0.06, H * 0.32)])

    if level >= 5:  # crown fins
        _poly(s, accent, [(cx, H * 0.02), (cx + W * 0.05, H * 0.16), (cx - W * 0.05, H * 0.16)])

    # Cockpit.
    _ellipse(s, _darken(accent, 0.15), cx - W * 0.09, H * 0.24, W * 0.18, H * 0.20)
    _ellipse(s, _lighten((120, 220, 255), 0.1), cx - W * 0.06, H * 0.27, W * 0.12, H * 0.12)


def make_player_frames(level: int) -> list[pygame.Surface]:
    level = max(1, min(cfg.MAX_WEAPON_LEVEL, level))
    w, h = cfg.PLAYER_SIZE
    frames = []
    for flame in (0, 1):
        s = _canvas(w, h)
        _draw_player(s, w * SS, h * SS, level, flame)
        frames.append(_down(s, w, h))
    return frames


# --------------------------------------------------------------------------- #
# Enemies (distinct silhouettes per archetype + per-instance variation)
# --------------------------------------------------------------------------- #
_ENEMY_PALETTE = {
    "grunt":   {"hull": (46, 204, 113), "accent": (26, 188, 156), "eye": (241, 196, 15)},
    "shooter": {"hull": (231, 76, 60),  "accent": (243, 156, 18), "eye": (255, 230, 120)},
    "diver":   {"hull": (155, 89, 182), "accent": (236, 240, 241), "eye": (52, 152, 219)},
    "tank":    {"hull": (127, 140, 141), "accent": (192, 57, 43), "eye": (241, 196, 15)},
}


def _enemy_params(kind, rng):
    base = _ENEMY_PALETTE[kind]
    hue = rng.uniform(-16, 16)
    return {
        "hull": _shift_hue(base["hull"], hue, v_mul=rng.uniform(0.9, 1.08)),
        "accent": _shift_hue(base["accent"], hue),
        "eye": base["eye"],
        "lights": rng.randint(4, 6),
    }


def _draw_enemy(s, W, H, kind, p, flame) -> None:
    cx = W / 2
    hull, accent, eye = p["hull"], p["accent"], p["eye"]

    if kind == "grunt":
        cy = H * 0.55
        _ellipse(s, hull, W * 0.08, cy - H * 0.10, W * 0.84, H * 0.26)
        _ellipse(s, _darken(hull, 0.32), W * 0.08, cy, W * 0.84, H * 0.18)
        _ellipse(s, accent, cx - W * 0.18, cy - H * 0.34, W * 0.36, H * 0.34)
        _ellipse(s, _lighten(accent, 0.45), cx - W * 0.10, cy - H * 0.30, W * 0.14, H * 0.16)
        n = p["lights"]
        for i in range(n):
            lx = W * 0.16 + (W * 0.68) * i / (n - 1)
            on = (i + flame) % 2 == 0
            _circle(s, eye if on else _darken(eye, 0.5), lx, cy + H * 0.085, W * 0.024)

    elif kind == "shooter":
        _poly(s, hull, [(cx, H * 0.92), (cx + W * 0.22, H * 0.45), (cx, H * 0.12), (cx - W * 0.22, H * 0.45)])
        _poly(s, accent, [(cx - W * 0.22, H * 0.40), (cx - W * 0.47, H * 0.26), (cx - W * 0.30, H * 0.60)])
        _poly(s, accent, [(cx + W * 0.22, H * 0.40), (cx + W * 0.47, H * 0.26), (cx + W * 0.30, H * 0.60)])
        for sx in (-1, 1):
            _rrect(s, _darken(hull, 0.35), cx + sx * W * 0.18 - W * 0.025, H * 0.58,
                   W * 0.05, H * 0.28, W * 0.02)
        _circle(s, (25, 20, 25), cx, H * 0.42, W * 0.11)
        _circle(s, eye, cx, H * 0.42, W * 0.08)
        _circle(s, _lighten(eye, 0.5), cx, H * 0.39, W * 0.035)
        _circle(s, _lighten(accent, 0.4) if flame else accent, cx, H * 0.15, W * 0.05)

    elif kind == "diver":
        _poly(s, hull, [(cx, H * 0.95), (cx + W * 0.14, H * 0.45), (cx + W * 0.10, H * 0.10),
                        (cx - W * 0.10, H * 0.10), (cx - W * 0.14, H * 0.45)])
        _poly(s, accent, [(cx - W * 0.10, H * 0.22), (cx - W * 0.36, H * 0.06), (cx - W * 0.12, H * 0.52)])
        _poly(s, accent, [(cx + W * 0.10, H * 0.22), (cx + W * 0.36, H * 0.06), (cx + W * 0.12, H * 0.52)])
        _poly(s, _lighten(hull, 0.4), [(cx, H * 0.9), (cx + W * 0.045, H * 0.5), (cx - W * 0.045, H * 0.5)])
        _circle(s, eye, cx, H * 0.33, W * 0.07)
        _circle(s, _lighten(accent, 0.4) if flame else accent, cx, H * 0.11, W * 0.06)

    elif kind == "tank":
        _rrect(s, hull, W * 0.10, H * 0.30, W * 0.80, H * 0.44, W * 0.12)
        _rrect(s, _darken(hull, 0.28), W * 0.16, H * 0.35, W * 0.68, H * 0.15, W * 0.06)
        for sx in (-1, 1):
            _rrect(s, _darken(hull, 0.38), cx + sx * W * 0.24 - W * 0.035, H * 0.68,
                   W * 0.07, H * 0.22, W * 0.02)
        pygame.draw.rect(s, accent, (int(W * 0.10), int(H * 0.55), int(W * 0.80), int(H * 0.05)))
        n = p["lights"]
        for i in range(n):
            rx = W * 0.20 + (W * 0.60) * i / (n - 1)
            _circle(s, _lighten(hull, 0.35), rx, H * 0.43, W * 0.02)
        _circle(s, (25, 20, 20), cx, H * 0.50, W * 0.09)
        _circle(s, eye if flame == 0 else _lighten(eye, 0.4), cx, H * 0.50, W * 0.065)


def make_enemy_variants(kind: str, count: int = 5) -> list[list[pygame.Surface]]:
    w, h = cfg.ENEMY_SIZE
    rng = random.Random(_seed_for(kind))
    variants = []
    for _ in range(count):
        params = _enemy_params(kind, rng)
        frames = []
        for flame in (0, 1):
            s = _canvas(w, h)
            _draw_enemy(s, w * SS, h * SS, kind, params, flame)
            frames.append(_down(s, w, h))
        variants.append(frames)
    return variants


# --------------------------------------------------------------------------- #
# Bosses (large, unique silhouettes per type)
# --------------------------------------------------------------------------- #
def _draw_boss(s, W, H, kind) -> None:
    cx = W / 2

    if kind == "warlord":
        hull, accent, eye = (108, 52, 140), (180, 70, 210), (255, 90, 90)
        _poly(s, _darken(hull, 0.2), [(W * 0.15, H * 0.35), (W * 0.02, H * 0.58), (W * 0.22, H * 0.62)])
        _poly(s, _darken(hull, 0.2), [(W * 0.85, H * 0.35), (W * 0.98, H * 0.58), (W * 0.78, H * 0.62)])
        _poly(s, hull, [(cx, H * 0.12), (W * 0.86, H * 0.36), (W * 0.80, H * 0.72),
                        (W * 0.20, H * 0.72), (W * 0.14, H * 0.36)])
        _poly(s, accent, [(cx, H * 0.20), (W * 0.70, H * 0.42), (W * 0.30, H * 0.42)])
        _circle(s, (28, 10, 38), cx, H * 0.48, W * 0.15)
        _circle(s, eye, cx, H * 0.48, W * 0.11)
        _circle(s, _lighten(eye, 0.5), cx, H * 0.44, W * 0.05)
        for i in range(5):
            tx = W * 0.28 + (W * 0.44) * i / 4
            pygame.draw.rect(s, _darken(hull, 0.3), (int(tx - W * 0.02), int(H * 0.72), int(W * 0.045), int(H * 0.10)))

    elif kind == "spreader":
        hull, accent, eye = (41, 108, 176), (52, 152, 219), (255, 236, 130)
        _poly(s, hull, [(W * 0.06, H * 0.5), (W * 0.22, H * 0.30), (W * 0.78, H * 0.30),
                        (W * 0.94, H * 0.5), (W * 0.82, H * 0.66), (W * 0.18, H * 0.66)])
        _rrect(s, accent, W * 0.30, H * 0.24, W * 0.40, H * 0.16, W * 0.06)
        _circle(s, (10, 30, 50), cx, H * 0.42, W * 0.10)
        _circle(s, eye, cx, H * 0.42, W * 0.07)
        for i in range(8):  # turret row
            tx = W * 0.14 + (W * 0.72) * i / 7
            _circle(s, _darken(hull, 0.35), tx, H * 0.68, W * 0.035)
            pygame.draw.rect(s, _darken(hull, 0.3), (int(tx - W * 0.012), int(H * 0.68), int(W * 0.024), int(H * 0.09)))

    elif kind == "summoner":
        hull, accent, eye = (39, 148, 96), (46, 204, 113), (255, 120, 200)
        for dx, dy, r in ((0.0, 0.0, 0.26), (-0.24, 0.06, 0.16), (0.24, 0.06, 0.16),
                          (-0.14, -0.14, 0.12), (0.14, -0.14, 0.12)):
            _circle(s, hull, cx + W * dx, H * 0.46 + H * dy, W * r)
        for dx, dy, r in ((-0.24, 0.06, 0.07), (0.24, 0.06, 0.07), (0.0, 0.22, 0.08)):  # egg pods
            _circle(s, _lighten(accent, 0.3), cx + W * dx, H * 0.46 + H * dy, W * r)
        _circle(s, (12, 40, 28), cx, H * 0.44, W * 0.14)
        _circle(s, eye, cx, H * 0.44, W * 0.10)
        _circle(s, _lighten(eye, 0.5), cx, H * 0.41, W * 0.045)

    elif kind == "overlord":
        hull, accent, eye = (176, 46, 40), (230, 80, 60), (255, 210, 90)
        for i in range(7):  # spiky lower edge
            x0 = W * 0.16 + (W * 0.68) * i / 7
            x1 = W * 0.16 + (W * 0.68) * (i + 1) / 7
            _poly(s, _darken(hull, 0.15), [(x0, H * 0.6), (x1, H * 0.6), ((x0 + x1) / 2, H * 0.8)])
        _poly(s, hull, [(cx, H * 0.10), (W * 0.90, H * 0.40), (W * 0.80, H * 0.62),
                        (W * 0.20, H * 0.62), (W * 0.10, H * 0.40)])
        _poly(s, accent, [(cx, H * 0.16), (W * 0.66, H * 0.40), (W * 0.34, H * 0.40)])
        _poly(s, _darken(hull, 0.25), [(W * 0.10, H * 0.40), (W * 0.0, H * 0.30), (W * 0.16, H * 0.30)])
        _poly(s, _darken(hull, 0.25), [(W * 0.90, H * 0.40), (W * 1.0, H * 0.30), (W * 0.84, H * 0.30)])
        _circle(s, (40, 8, 8), cx, H * 0.42, W * 0.13)
        _circle(s, eye, cx, H * 0.42, W * 0.09)
        _circle(s, _lighten(eye, 0.5), cx, H * 0.39, W * 0.04)


def make_boss(kind: str) -> pygame.Surface:
    w, h = cfg.BOSS_SIZE
    s = _canvas(w, h)
    _draw_boss(s, w * SS, h * SS, kind)
    return _down(s, w, h)


# --------------------------------------------------------------------------- #
# Icon
# --------------------------------------------------------------------------- #
def make_icon() -> pygame.Surface:
    return _down(make_player_frames(3)[0], 32, 32)
