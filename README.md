# Pokemon Emerald But BETTER

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![Arcade](https://img.shields.io/badge/Arcade-3.3.3+-green.svg)

A Python-powered clone of the classic **Pokémon Emerald**, built from scratch using the [Python Arcade](https://api.arcade.academy/en/latest/) library. 

This project aims to recreate the overworld exploration and classic turn-based battle mechanics of the 3rd-generation Pokémon games, with modern software engineering practices and an ongoing goal to refactor the monolithic legacy-style game logic into a clean, MVC-based architecture.

## 🚀 Features

### Overworld Exploration
- **Tile-based map** navigation with strict tile collision handling.
- **Camera interpolation** that follows the player smoothly across Littleroot Town and beyond.
- Map transitions and **tall grass encounters** (15% chance to encounter a wild Pokémon per step).
- **Player animations** (Idle, Walk in 4 directions).
- Fully functional **inventory system (Bag)** to view items and Pokéballs.

### Battle System
- Authentic slide-in UI animations and classic battle flicker transition.
- **Turn-based loop** powered by a speed-based queue.
- **Damage calculations** factor in Base Power, STAB (Same-Type Attack Bonus), Type effectiveness, and Critical Hits.
- **Status Effects**: Sleep, Paralysis, Poison.
- **Stat modifier messages** ("Attack sharply rose!").
- Fully working **Evolution sequences**, featuring animated sprite pulsing and transitions.

## 🛠️ Architecture & Refactoring

Currently, the game is undergoing a massive refactoring effort to move away from legacy "God Classes" to a cleaner, MVC-based architecture utilizing DataModels (`pydantic` heavily).

**Key Architectural Goals:**
1. **Data Models:** Isolating pure state using Python `dataclasses` and `pydantic`.
2. **In-Memory Save Managers & Data Loaders:** Moving away from synchronous/redundant disk I/O on every HP update by reading into RAM and flushing to disk only when needed.
3. **MVC Battle System:** Splitting UI rendering (`battle_ui`), game logic (`battle_system`), and proxies (`battle_scene`).

*See `docs/refactoring_plan.md` for a full breakdown.*

## ⚠️ Current Status & Known Issues

This is an active work-in-progress, and as such, several defining features are currently missing.

**Not Yet Implemented:**
- Pokémon Centers (no healing) & Poké Marts.
- Trainer battles, NPCs, and dialogue.
- Gym battles, Badges, and overall game progression.
- Pokemon switching in battle and Catch logic (throw Pokéballs).
- In-game music and sound.

**Known Bugs:**
- Poison damage applies incorrectly (float logic instead of integer).
- Wild Pokémon only know "Tackle".
- Critical hits ignore stat stage modifications on defense.
*See `docs/game-status-report.md` for a fully up-to-date look at the game state.*

## 💻 Installation

This project utilizes `uv` to manage dependencies. Make sure you have python 3.14+ installed.

```bash
# 1. Clone the repository
git clone https://github.com/gazi04/pokemon-emerald-but-better.git
cd pokemon-emerald-but-better

# 2. Sync dependencies using uv
uv sync

# 3. Run the game!
uv run main.py
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| `Up/Down/Left/Right` | Move / Navigate menus |
| `Z` | Confirm / Interact |
| `ESC` | Cancel / Go back |
| `TAB` | Open bag in overworld |

---
*Created by [gazi04] and [YoshikageKira425]*
