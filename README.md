# iterm-theme-switcher

A minimal CLI for switching iTerm2 color themes using the official Python API — no fzf, no curses, no nonsense.

## Features

- Curated favorites list for fast switching
- `--full` mode to browse all 300+ installed themes
- `--preview` mode to live-preview themes as you navigate, reverting on quit
- Space to toggle favorites from the full list
- Favorites persisted to `~/.iterm_theme_favorites.json`

## Requirements

- iTerm2 with the Python API enabled  
  (**iTerm2 → Settings → General → Magic → Enable Python API**)

## Install

```sh
git clone https://github.com/swift-develop/iterm-theme-switcher.git
cd iterm-theme-switcher
```

Add an alias to your `.zshrc`:

```sh
alias theme='"/Users/YOUR_USERNAME/Library/Application Support/iTerm2/iterm2env/versions/3.14.0/bin/python3" ~/Developer/git/iterm-theme-switcher/iterm_theme.py'
```

## Usage

```sh
theme              # pick from favorites
theme -f           # browse all installed themes
theme -p           # favorites with live preview
theme -f -p        # full list with live preview
```

### Keys

| Key        | Action                        |
|------------|-------------------------------|
| ↑ / ↓      | Navigate                      |
| PgUp / PgDn| Jump a page                   |
| Enter      | Apply theme                   |
| Space      | Toggle favorite (full mode)   |
| q          | Quit / revert preview         |

## Adding themes

Download `.itermcolors` files from [iterm2colorschemes.com](https://iterm2colorschemes.com) and import via:  
**Preferences → Profiles → Colors → Color Presets → Import**
