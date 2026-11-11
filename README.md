# Sirius & the Castle ★

**Cross-platform retro CLI cyber-buddy ecosystem for Windows, macOS, and Arch Linux.**

Inspired by BMO, the Castle houses a growing family of warm, single-task terminal buddies led by **Sirius** (the Master Study brain) and **Pomo** (the Clocktower focus & time tracker from `pomoclk`).

Each buddy carries:
- **`soul.md`** — an editable Markdown personality file driving replies today and ready to serve as a local LLM system prompt later.
- **`core.json`** — a versioned, evolving core that upgrades cleanly across releases and grows XP, ranks, and machine-scoped observations as you work together.

## Install

Clone from GitHub on any machine:
```sh
git clone https://github.com/justsepi/Sirius-Buddies.git
cd Sirius-Buddies
```

### Windows (PowerShell)
```powershell
pip install -e .
```
*(Run `sirius` or `castle`, or `python -m castle.cli` if `Scripts` is not on your `PATH`.)*

### macOS & Arch Linux (`zsh` / `bash`)
```sh
sh install.sh
source ~/.zshrc   # needed once in an already-open tab; new tabs work automatically
```
Or install manually with `pipx`:
```sh
pipx install .
pipx ensurepath
```

## Usage

Run `sirius` (or `castle`) with no arguments to open the interactive BMO-style Castle Hub, or run direct commands:

| Command | What it does |
|---------|-------------|
| `sirius` | Interactive BMO-style Castle TUI Hub |
| `sirius ask "start deep focus on api"` | Ask Sirius in natural phrasing to route/execute a task |
| `sirius status` | Castle & today's focus summary |
| `sirius buddies` | List all residents, rooms, core levels, and `soul.md` paths |
| `sirius summon pomo` | Open Pomo directly (or `sirius pomo start -p sprint -t api`) |
| `sirius log` | Recent Castle mission journal |
| `sirius soul sirius` | Inspect (or get path to edit) a buddy's `soul.md` |
| `sirius config [key] [value]` | View or update Castle settings |

Standalone `pomo` (`pomoclk`) remains completely independent—running `pomo` directly still works identically and shares `~/.pomoclk/` stats with Sirius.

## Data & Customization

All Castle data lives offline in `~/.castle/` (override with `CASTLE_DIR`):
- `config.json` — global settings (`user_name`, `brain_provider`, `animations_enabled`, `pomo_command`)
- `journal.json` — mission chronicle
- `buddies/<id>/soul.md` — editable buddy personality & reaction lines
- `buddies/<id>/core.json` — evolving core (`core_version`, `xp`, `level`, `rank`, `memory`, `machine_facts`, `evolution_log`)
