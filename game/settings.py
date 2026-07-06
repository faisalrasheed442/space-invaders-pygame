"""Central configuration for Space Adventure.

All tunable gameplay values live here so balancing the game never means
hunting through logic. Speeds are in pixels/second and durations in seconds,
so everything is frame-rate independent.
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #
WIDTH, HEIGHT = 1280, 720
FPS = 60
CAPTION = "Space Adventure"

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT_DIR / "pic"
SAVE_FILE = ROOT_DIR / "savegame.json"
HIGHSCORE_FILE = ROOT_DIR / "highscore.txt"

# --------------------------------------------------------------------------- #
# Colors
# --------------------------------------------------------------------------- #
WHITE = (245, 246, 250)
BLACK = (5, 6, 12)
DARK = (12, 14, 28)
RED = (232, 65, 24)
GREEN = (68, 189, 50)
YELLOW = (251, 197, 49)
ORANGE = (245, 148, 30)
CYAN = (0, 200, 220)
BLUE = (52, 152, 219)
PURPLE = (156, 89, 209)
GREY = (120, 130, 150)

# --------------------------------------------------------------------------- #
# Player
# --------------------------------------------------------------------------- #
PLAYER_SIZE = (72, 72)
PLAYER_SPEED = 460
PLAYER_FIRE_COOLDOWN = 0.28
RAPID_FIRE_COOLDOWN = 0.10
START_LIVES = 3
MAX_LIVES = 5
INVULN_TIME = 1.6
ANIM_INTERVAL = 0.05

# Weapon upgrades: collecting an "upgrade" reward raises the weapon level,
# adding more bullet streams and (at higher tiers) more damage. Taking a hit
# knocks the weapon down one level, so upgrades are worth protecting.
MAX_WEAPON_LEVEL = 5
WEAPON_HEAVY_LEVEL = 4          # at/above this level each bullet deals +1 damage

# --------------------------------------------------------------------------- #
# Bullets
# --------------------------------------------------------------------------- #
PLAYER_BULLET_SPEED = 820
PLAYER_BULLET_RADIUS = 6
ENEMY_BULLET_SPEED = 380
ENEMY_BULLET_RADIUS = 7
MAX_PLAYER_BULLETS = 14
MULTISHOT_SPREAD = 190      # horizontal velocity of angled multishot bullets

# --------------------------------------------------------------------------- #
# Enemies
# --------------------------------------------------------------------------- #
ENEMY_SIZE = (72, 72)
ENEMY_BASE_SPEED = 95           # horizontal formation speed
ENEMY_SPEED_PER_WAVE = 12
ENEMY_EDGE_DESCEND = 26         # drop when the formation hits a screen edge
ENEMY_DRIFT_SPEED = 7           # constant downward drift (per wave scaled)
ENEMY_DRIFT_PER_WAVE = 2
ENEMY_FLOOR = HEIGHT - 150      # if enemies pass this, the player loses a life
DIVE_SPEED = 360
DIVE_INTERVAL = 2.6             # seconds between dive attempts (per wave faster)
SHOOTER_FIRE_INTERVAL = 2.2     # avg seconds between a shooter's shots

# Enemy archetypes: health, points, tint (None = original art), fire?
ENEMY_KINDS = {
    "grunt":   {"health": 3, "points": 10, "tint": None,             "can_shoot": False},
    "shooter": {"health": 4, "points": 20, "tint": (255, 120, 90),   "can_shoot": True},
    "diver":   {"health": 3, "points": 25, "tint": (120, 230, 140),  "can_shoot": False},
    "tank":    {"health": 10, "points": 45, "tint": (150, 155, 175), "can_shoot": True},
}

# --------------------------------------------------------------------------- #
# Boss
# --------------------------------------------------------------------------- #
BOSS_EVERY = 5                  # every Nth wave is a boss wave
BOSS_SIZE = (168, 168)
BOSS_HEALTH_BASE = 90
BOSS_HEALTH_PER_TIER = 60
BOSS_SPEED = 170
BOSS_POINTS = 500
BOSS_ATTACK_INTERVAL = 1.7
BOSS_SPAWN_INTERVAL = 6.0       # seconds between minion spawns

# Distinct boss types, cycled by boss tier. Each has its own colour, attack
# rotation, and how aggressively it summons minions (lower = more often).
BOSS_KINDS = ["warlord", "spreader", "summoner", "overlord"]
BOSS_SPECS = {
    "warlord":  {"tint": (180, 70, 210), "patterns": ["spread", "aimed"],
                 "spawn_mult": 1.0, "name": "The Warlord"},
    "spreader": {"tint": (70, 150, 230), "patterns": ["rain", "spread"],
                 "spawn_mult": 1.3, "name": "The Spreader"},
    "summoner": {"tint": (90, 200, 120), "patterns": ["aimed", "spread"],
                 "spawn_mult": 0.5, "name": "The Summoner"},
    "overlord": {"tint": (230, 80, 60),  "patterns": ["spiral", "spread", "aimed"],
                 "spawn_mult": 0.8, "name": "The Overlord"},
}

# --------------------------------------------------------------------------- #
# Power-ups (rewards)
# --------------------------------------------------------------------------- #
POWERUP_SIZE = 34
POWERUP_FALL_SPEED = 165
POWERUP_DURATION = 8.0          # duration of timed buffs
POWERUP_DROP_CHANCE = 0.16      # chance a normal kill drops a reward
SCORE_BONUS = 500

# kind -> (label, color). Weighted drop table below.
POWERUPS = {
    "rapid":   ("R", ORANGE),
    "multi":   ("M", CYAN),
    "shield":  ("S", BLUE),
    "life":    ("+", GREEN),
    "bomb":    ("B", RED),
    "score":   ("$", YELLOW),
    "upgrade": ("^", PURPLE),
}
POWERUP_WEIGHTS = {
    "rapid": 20, "multi": 16, "shield": 16, "life": 7,
    "bomb": 11, "score": 16, "upgrade": 14,
}

# --------------------------------------------------------------------------- #
# Waves
# --------------------------------------------------------------------------- #
WAVE_CLEAR_BONUS = 150
