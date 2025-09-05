# Zach's Spider Adventure

A retro-style platformer game built with Python and Pygame.

## How to Play

- **Move**: Arrow keys or WASD
- **Jump**: Spacebar, Up arrow, or W
- **Goal**: Jump on spiders to defeat them and progress through levels
- **Lives**: You start with 2 blocks (lives) and can grow to 3
- **Combo System**: Chain kills in the air for bonus points
- **Restart**: Press 'R' when game over

## Features

- 10 levels with increasing difficulty
- Combo scoring system with multipliers
- High score tracking
- Procedural audio effects
- Level-specific background music

## Requirements

- Python 3.6+
- Pygame
- NumPy

## Installation

```bash
pip install pygame numpy
```

## Run

```bash
python main.py
```

## Game Mechanics

- Jump on spiders from above to defeat them
- Avoid side/bottom collisions (they cost lives)
- Build combos by staying airborne
- Complete all 10 levels to win
