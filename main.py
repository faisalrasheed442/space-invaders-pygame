"""
Space Adventure — a complete arcade shooter built with pygame.

Fly your ship through endless waves of enemies that shoot and dive at you,
grab power-up rewards, and survive boss fights. Includes a full menu system
with New Game, Continue (save/resume), and a persistent high score.

Controls
--------
    Arrow keys / WASD ... move
    Space .............. fire
    P / Esc ............ pause menu
    M .................. mute / unmute
    Enter .............. select menu item
    Up / Down .......... navigate menus

Run with:  python main.py
"""

import sys

from game.game import main

if __name__ == "__main__":
    main()
    sys.exit(0)
