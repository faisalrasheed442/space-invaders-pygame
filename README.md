<h1 align="center">🚀 Space Adventure</h1>

<p align="center">
  A fast, polished arcade shooter built from scratch in <b>Python</b> with <b>pygame</b>.<br>
  Fly your ship, clear escalating waves of enemies, and chase the high score.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white">
  <img alt="pygame" src="https://img.shields.io/badge/pygame-2.5%2B-1B9E4B">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-informational">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
</p>

<p align="center">
  <img src="pic/screenshot.png" alt="Space Adventure gameplay" width="80%">
</p>

---

## ✨ Features

- **Smooth 60 FPS, frame-rate independent** — all movement is scaled by delta time, so the game plays identically on any hardware (no more "too fast on a fast PC").
- **Wave-based progression** — each wave spawns more enemies that move faster and take more hits.
- **Lives & scoring** — start with 3 lives, earn points per hit and bonus points per kill, with a **persistent high score** saved between sessions.
- **Responsive controls** — Arrow keys *or* WASD, with animated ship thrust.
- **Health bars, HUD & lives display** — clear at-a-glance game state.
- **Full game loop** — start screen, pause, game-over, and instant restart.
- **Robust & crash-resistant** — missing images or an unavailable audio device degrade gracefully instead of crashing; the game still runs on headless machines.
- **Zero-freeze design** — no blocking sleeps anywhere in the loop; hit feedback uses a non-blocking invulnerability timer.

## 🎮 Controls

| Action        | Keys                         |
| ------------- | ---------------------------- |
| Move          | `← ↑ ↓ →` or `W A S D`       |
| Fire          | `Space`                      |
| Pause / Resume| `P`                          |
| Mute / Unmute | `M`                          |
| Start / Restart | `Enter`                    |
| Quit          | `Esc` or `Q`                 |

## 🛠️ Getting Started

### Prerequisites
- Python **3.8+**

### Installation & Run

```bash
# 1. Clone the repository
git clone https://github.com/faisalrasheed442/space-invaders-pygame.git
cd space-invaders-pygame

# 2. (Recommended) create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

# 3. Install dependencies
pip install -r Requirements.txt

# 4. Play!
python main.py
```

## 🧩 How It Works

The game is a single, well-structured module organized around a small object model:

| Component | Responsibility |
| --------- | -------------- |
| `Game`    | Owns the main loop, state machine (`start → playing → paused → over`), input, collision, HUD and rendering. |
| `Player`  | Movement, screen clamping, thrust animation, and invulnerability frames after a hit. |
| `Enemy`   | Horizontal patrol with descent-on-bounce, health, and a health bar. |
| `Bullet`  | Lightweight projectile (`__slots__`) with upward motion and off-screen culling. |
| `AnimatedSprite` | Shared, time-based frame animation used by the ship and enemies. |

**Design highlights**

- **Delta-time movement** (`speed × dt`) keeps gameplay consistent regardless of frame rate, and `dt` is clamped to prevent "tunneling" through collisions after a stall.
- **Fault-tolerant asset loading** — every image and sound is loaded through a helper that returns a safe placeholder / silent stub if a file or audio device is missing.
- **Safe iteration** — bullets and enemies are culled by iterating over copies of their lists, avoiding the classic mutate-while-iterating bug.
- **Cross-platform paths** via `pathlib`, so it runs the same on Windows, macOS, and Linux.

## 📁 Project Structure

```
space-invaders-pygame/
├── main.py            # Complete game (entry point)
├── Requirements.txt   # Python dependencies
├── pic/               # Sprites, background, audio
│   ├── s1..s9.png     #   ship animation frames
│   ├── e1..e9.png     #   enemy animation frames
│   ├── bg.jpg         #   background
│   └── *.wav / *.mp3  #   sound effects & music
└── README.md
```

## 📄 License

Released under the **MIT License** — see [`LICENSE`](LICENSE). Sprite and audio
assets are used for educational/demo purposes.

---

<p align="center">Made with 🐍 and pygame by <a href="https://github.com/faisalrasheed442">Faisal Rasheed</a></p>
