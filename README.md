# Sirius & the Castle ✦

**Cross-platform retro CLI cyber-buddy & offline device-helper hub for macOS (`zsh`), Windows (`Git Bash` / `PowerShell` in Windows Terminal), and Linux.**

**Sirius** is a floating bright-white and blue retro star buddy with a visible floating shadow, 12 expressive CLI moods, and practical pure-offline device utilities—driven completely from your keyboard with zero cloud or AI dependencies. Alongside Sirius, the Castle can also summon specialist buddies like **Pomo** (`pomoclk`) when installed.

## Install (Beta)

Clone the `beta` branch from GitHub:
```sh
git clone -b beta https://github.com/justsepi/Sirius-Buddies.git
cd Sirius-Buddies
```

### macOS (`zsh` / `bash`) & Linux
```sh
sh install.sh
source ~/.zshrc   # needed once in an already-open tab; new tabs work automatically
```

### Windows Terminal — Git Bash (`bash`)
Open a **Git Bash** tab inside **Windows Terminal** and run:
```sh
sh install.sh
source ~/.bashrc
```
*(We recommend running Git Bash inside Windows Terminal rather than standalone Mintty so interactive keyboard control runs directly over ConPTY.)*

### Windows — PowerShell (Editable Dev Install)
```powershell
pip install -e .
```
*(Run `sirius` or `castle`, or `python -m castle.cli` if `Scripts` is not on your `PATH`.)*

## Keyboard TUI & CLI Commands

Run `sirius` (or `castle`) with no arguments to open the interactive keyboard-driven Hub:
- `↑` / `↓` (or `j` / `k`) + `Enter` — navigate and launch Device Helpers
- `1`–`6` — quick-launch **System Pulse**, **Repo & Git Scout**, **Port Inspector**, **Cache Sweep**, **Quick Timer**, or **Summon Pomo**
- `p` **Poke Sirius** · `f` **Toss Snack** · `o` **Cosmic Flip / Roll / Oracle** · `m` **Moods Gallery**
- `d` **Castle Buddies** · `l` **Mission Log** · `s` **Settings** · `q` / `Esc` **Quit**

Or call any offline helper directly from your terminal:

| Command | What it does |
|---------|--------------|
| `sirius` | Open interactive keyboard TUI Hub |
| `sirius pulse` | Inspect OS, CPU, RAM, disk, battery & local IP |
| `sirius repo [path]` | Scout Git branch, dirty worktree, commits & stack |
| `sirius ports [port...]` | Inspect listening localhost TCP ports & dev servers |
| `sirius sweep [path]` | Scan safe dev caches (`__pycache__`, `.pytest_cache`, `.DS_Store`) |
| `sirius sweep --clean` | Safely clear confirmed cache clutter (`-y` to skip prompt) |
| `sirius timer [minutes]` | Built-in offline keyboard countdown timer (default 25m) |
| `sirius poke` / `snack` | Cyber-buddy interactions with live expression changes |
| `sirius flip` / `roll` / `oracle` | Offline coin flip, d20/dN dice roll & cosmic call |
| `sirius mood [name]` | Preview Sirius's 12 CLI expressions |
| `sirius pomo [args...]` | Summon Pomo (`pomoclk`) if installed |
| `sirius buddies` | List Castle buddies, rooms & evolving cores |
| `sirius soul [buddy]` | Inspect a buddy's `soul.md` & `core.json` |
| `sirius log` | Recent Castle mission chronicle |
| `sirius config [key] [value]` | View or update Castle settings |

## Offline Data & Customization

All Castle data lives locally in `~/.castle/` (override with `CASTLE_DIR`):
- `config.json` — settings (`user_name`, `animations_enabled`, `show_shadow`, `pomo_command`)
- `journal.json` — bounded mission log
- `buddies/<id>/soul.md` — editable buddy personality & reaction lines
- `buddies/<id>/core.json` — evolving core (`core_version`, `xp`, `level`, `rank`, `memory`, `machine_facts`, `evolution_log`)

## Running Tests

```sh
pip install -e ".[dev]"
python -m pytest -v
```
