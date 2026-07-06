"""Fault-tolerant asset loading.

Every loader returns a usable object even when a file is missing or the audio
device is unavailable, so the game never hard-crashes on a bad asset and can
run headless (CI, servers) without sound.
"""

from __future__ import annotations

import pygame

from game import settings as cfg


class NullSound:
    """Silent stand-in used when audio is unavailable."""

    def play(self, *args, **kwargs) -> None:
        return None

    def stop(self, *args, **kwargs) -> None:
        return None


def load_image(name: str, size: tuple[int, int] | None = None,
               tint: tuple[int, int, int] | None = None) -> pygame.Surface:
    """Load and convert an image. Returns a magenta placeholder if missing."""
    try:
        image = pygame.image.load(str(cfg.ASSET_DIR / name)).convert_alpha()
    except (pygame.error, FileNotFoundError):
        image = pygame.Surface(size or (64, 64), pygame.SRCALPHA)
        image.fill((255, 0, 255, 160))
    if size is not None:
        image = pygame.transform.smoothscale(image, size)
    if tint is not None:
        image = apply_tint(image, tint)
    return image


def apply_tint(surface: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
    """Return a copy of *surface* tinted toward *color*, preserving alpha."""
    tinted = surface.copy()
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, 130))
    tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def load_frames(prefix: str, count: int, size: tuple[int, int],
                tint: tuple[int, int, int] | None = None) -> list[pygame.Surface]:
    """Load an animation strip such as s1..s9 or e1..e9."""
    return [load_image(f"{prefix}{i}.png", size, tint) for i in range(1, count + 1)]


def load_sound(name: str):
    """Load a sound effect, or a silent stub if the mixer/file is unavailable."""
    if not pygame.mixer.get_init():
        return NullSound()
    try:
        return pygame.mixer.Sound(str(cfg.ASSET_DIR / name))
    except (pygame.error, FileNotFoundError):
        return NullSound()


def load_music(name: str) -> bool:
    """Queue background music. Returns True on success."""
    if not pygame.mixer.get_init():
        return False
    try:
        pygame.mixer.music.load(str(cfg.ASSET_DIR / name))
        pygame.mixer.music.set_volume(0.35)
        return True
    except pygame.error:
        return False


def font(size: int) -> pygame.font.Font:
    """A reliable built-in font at the requested size."""
    return pygame.font.Font(None, size)
