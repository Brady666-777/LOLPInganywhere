# LoLPing · Windows

A Windows port of [LoLPing-Mac](https://github.com/AllenTHT/LoLPing-Mac) by **[AllenTHT](https://github.com/AllenTHT)** — a League of Legends-style tactical ping wheel for your desktop.

> **Credit:** The original concept, artwork, sound assets, and macOS implementation are by [AllenTHT](https://github.com/AllenTHT). This repository is a Windows adaptation only.

---

## What it does

Displays an 8-way radial ping wheel on your screen — outside the game, on your desktop. It does **not** send pings to your teammates in-game; it's a personal desktop visual/audio tool.

## How to use

1. Launch `LoLPing.exe`
2. Tick **启用全局 Ping** (Enable Global Ping)
3. Hold **Alt** (or **G**, selectable in the dropdown)
4. **Right-click and hold** anywhere on screen → the wheel appears
5. Drag toward a ping slice to select it
6. **Release RMB** to fire the ping
7. Drag back to center, or **left-click** to cancel

## Download

👉 **[Download LoLPing.exe (v1.0)](https://github.com/Brady666-777/LOLPInganywhere/releases/latest/download/LoLPing.exe)**

No Python or installation required — just download and run. Windows 10/11 x64.

## Build from source

Requires Python 3.10+.

```bat
scripts\build-exe.bat
```

Output: `dist\LoLPing.exe`

Or run directly without building:

```bat
pip install -r windows\requirements.txt
python windows\main.py
```

## Credits

| | |
|---|---|
| **Original author** | [AllenTHT](https://github.com/AllenTHT) — [LoLPing-Mac](https://github.com/AllenTHT/LoLPing-Mac) |
| **Windows port** | [Brady666-777](https://github.com/Brady666-777) |
| **Icons** | CommunityDragon 15.24 wheel atlas (Riot Games assets) |
| **Sounds** | [alibaztomars/lol-ping-overlay](https://github.com/alibaztomars/lol-ping-overlay) |
| **UI framework** | [PySide6 / Qt](https://www.qt.io/) |

Game assets belong to Riot Games. LoLPing is an independent personal desktop tool and is not an official Riot product.
