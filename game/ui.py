"""Menus, HUD and overlay screens."""

from __future__ import annotations

import pygame

from game import settings as cfg


class Menu:
    """A simple keyboard-navigable vertical menu.

    Items are (key, label) pairs. `move` cycles the selection and `select`
    returns the key of the highlighted item.
    """

    def __init__(self, items: list[tuple[str, str]]):
        self.items = items
        self.index = 0

    def set_items(self, items: list[tuple[str, str]]) -> None:
        self.items = items
        self.index = min(self.index, len(items) - 1)

    def move(self, delta: int) -> None:
        if self.items:
            self.index = (self.index + delta) % len(self.items)

    def select(self) -> str:
        return self.items[self.index][0]

    def draw(self, win, font, center_x, start_y, gap=58) -> None:
        for i, (_, label) in enumerate(self.items):
            selected = i == self.index
            color = cfg.YELLOW if selected else cfg.WHITE
            text = ("> " + label + " <") if selected else label
            surface = font.render(text, True, color)
            win.blit(surface, surface.get_rect(center=(center_x, start_y + i * gap)))


def draw_center_text(win, text, font, color, cx, cy) -> None:
    surface = font.render(text, True, color)
    win.blit(surface, surface.get_rect(center=(cx, cy)))


def draw_dim(win, alpha=185) -> None:
    overlay = pygame.Surface((cfg.WIDTH, cfg.HEIGHT), pygame.SRCALPHA)
    overlay.fill((*cfg.DARK, alpha))
    win.blit(overlay, (0, 0))


def draw_hud(win, fonts, player, score, wave, lives, high_score, ship_icon, muted) -> None:
    small, tiny = fonts
    win.blit(small.render(f"Score: {score}", True, cfg.WHITE), (16, 14))
    win.blit(small.render(f"Wave: {wave}", True, cfg.CYAN), (16, 48))

    hs = small.render(f"High: {high_score}", True, cfg.YELLOW)
    win.blit(hs, (cfg.WIDTH - hs.get_width() - 16, 48))

    # Lives as small ship icons.
    for i in range(lives):
        win.blit(ship_icon, (cfg.WIDTH - 40 - i * 34, 82))

    # Weapon level.
    wl = small.render(f"Weapon Lv {player.weapon_level}", True, cfg.ORANGE)
    win.blit(wl, (16, 84))

    # Active power-up timers.
    x = 16
    y = 118
    for label, t, color in (
        ("RAPID", player.rapid_t, cfg.ORANGE),
        ("MULTI", player.multi_t, cfg.CYAN),
        ("SHIELD", player.shield_t, cfg.BLUE),
    ):
        if t > 0:
            chip = tiny.render(f"{label} {t:0.0f}s", True, color)
            win.blit(chip, (x, y))
            x += chip.get_width() + 14

    if muted:
        m = tiny.render("MUTED", True, cfg.RED)
        win.blit(m, (cfg.WIDTH // 2 - m.get_width() // 2, 14))
