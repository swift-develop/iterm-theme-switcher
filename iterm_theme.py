import asyncio
import iterm2
import json
import os
import plistlib
import subprocess
import sys
import termios
import tty

WINDOW_SIZE = 10
FAVORITES_FILE = os.path.expanduser("~/.iterm_theme_favorites.json")
DEFAULT_FAVORITES = [
    "Banana Blueberry",
    "Cobalt Neon",
    "synthwave everything",
    "Builtin Solarized Light",
]

COLOR_ATTRS = [
    "foreground_color", "background_color", "bold_color", "link_color",
    "selection_color", "selected_text_color", "cursor_color", "cursor_text_color",
] + [f"ansi_{i}_color" for i in range(16)]

def load_favorites():
    try:
        with open(FAVORITES_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_FAVORITES[:]

def save_favorites(favorites):
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favorites, f, indent=2)

def load_all_theme_names():
    result = subprocess.run(
        ["defaults", "export", "com.googlecode.iterm2", "-"],
        capture_output=True
    )
    prefs = plistlib.loads(result.stdout)
    return sorted(prefs.get("Custom Color Presets", {}).keys())

def build_items(favorites, all_names):
    fav_set = set(favorites)
    items = [(name, True) for name in favorites]
    others = [name for name in all_names if name not in fav_set]
    if others:
        items.append(None)
        items.extend((name, False) for name in others)
    return items

def selectable(items):
    return [i for i, item in enumerate(items) if item is not None]

async def save_colors(profile):
    return {attr: getattr(profile, attr) for attr in COLOR_ATTRS}

async def restore_colors(profile, colors):
    for attr, value in colors.items():
        if value is not None:
            await getattr(profile, f"async_set_{attr}")(value)

async def apply_preset(connection, session, name):
    try:
        preset = await iterm2.ColorPreset.async_get(connection, name)
        profile = await session.async_get_profile()
        await profile.async_set_color_preset(preset)
    except Exception:
        pass

def render(items, sel, offset, full_mode):
    visible = min(WINDOW_SIZE, len(items))
    sys.stdout.write("\033[H\033[J")
    sys.stdout.write("iTerm2 Theme Switcher\r\n")
    sys.stdout.write("─" * 30 + "\r\n")
    for i in range(visible):
        idx = offset + i
        if idx >= len(items):
            sys.stdout.write("\r\n")
            continue
        item = items[idx]
        if item is None:
            sys.stdout.write(f"\033[2m{'─' * 28}\033[0m\r\n")
            continue
        name, is_fav = item
        highlighted = idx == sel
        if is_fav:
            line = f"● {name}"
            fmt = "\033[7;1m" if highlighted else "\033[1m"
        else:
            line = f"  {name}"
            fmt = "\033[7m" if highlighted else "\033[2m"
        sys.stdout.write(f"{fmt}{line}\033[0m\r\n")
    scroll = f"  ({offset + 1}–{offset + min(WINDOW_SIZE, len(items))} of {len(items)})" if len(items) > WINDOW_SIZE else ""
    hints = ["↑↓ PgUp/Dn", "Enter=apply"]
    if full_mode:
        hints.append("Space=favorite")
    hints.append("q=quit")
    sys.stdout.write(f"\r\n{'  '.join(hints)}{scroll}\r\n")
    sys.stdout.flush()

async def pick_theme(favorites, all_names=None, connection=None, session=None, preview=False):
    full_mode = all_names is not None
    items = build_items(favorites, all_names) if full_mode else [(n, True) for n in favorites]
    sel = 0
    offset = 0
    loop = asyncio.get_event_loop()

    original_colors = None
    if preview and session:
        profile = await session.async_get_profile()
        original_colors = await save_colors(profile)

    def move(direction):
        nonlocal sel, offset
        indices = selectable(items)
        cur = indices.index(sel) if sel in indices else 0
        nxt = max(0, cur - 1) if direction < 0 else min(len(indices) - 1, cur + 1)
        sel = indices[nxt]
        visible = min(WINDOW_SIZE, len(items))
        if sel < offset:
            offset = sel
        elif sel >= offset + visible:
            offset = sel - visible + 1
        return items[sel][0] if items[sel] else None

    def page(direction):
        nonlocal sel, offset
        indices = selectable(items)
        cur = indices.index(sel) if sel in indices else 0
        nxt = max(0, cur - WINDOW_SIZE) if direction < 0 else min(len(indices) - 1, cur + WINDOW_SIZE)
        sel = indices[nxt]
        visible = min(WINDOW_SIZE, len(items))
        offset = max(0, min(sel - visible // 2, len(items) - visible))
        return items[sel][0] if items[sel] else None

    def read_char():
        return sys.stdin.read(1)

    sys.stdout.write("\033[?25l")
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    result_name = None
    quit_preview = False

    try:
        tty.setraw(fd)
        while True:
            render(items, sel, offset, full_mode)
            ch = await loop.run_in_executor(None, read_char)
            preview_name = None

            if ch == "\x1b":
                seq = await loop.run_in_executor(None, lambda: sys.stdin.read(2))
                if seq == "[A":
                    preview_name = move(-1)
                elif seq == "[B":
                    preview_name = move(1)
                elif seq == "[5":
                    await loop.run_in_executor(None, lambda: sys.stdin.read(1))
                    preview_name = page(-1)
                elif seq == "[6":
                    await loop.run_in_executor(None, lambda: sys.stdin.read(1))
                    preview_name = page(1)

            elif ch in ("\r", "\n"):
                item = items[sel]
                if item is not None:
                    result_name = item[0]
                break

            elif ch == " " and full_mode:
                item = items[sel]
                if item is not None:
                    name, is_fav = item
                    if is_fav:
                        favorites = [f for f in favorites if f != name]
                    else:
                        favorites = sorted(favorites + [name], key=str.lower)
                    save_favorites(favorites)
                    items = build_items(favorites, all_names)
                    if is_fav:
                        # stayed in favorites — land on previous fav, or first if none
                        fav_indices = [i for i, it in enumerate(items) if it is not None and it[1]]
                        if fav_indices:
                            sel = max((i for i in fav_indices if i < sel), default=fav_indices[0])
                        else:
                            sel = 0
                    else:
                        for i, it in enumerate(items):
                            if it is not None and it[0] == name:
                                sel = i
                                break
                    visible = min(WINDOW_SIZE, len(items))
                    if sel < offset:
                        offset = sel
                    elif sel >= offset + visible:
                        offset = sel - visible + 1

            elif ch == "q":
                quit_preview = True
                break

            if preview and preview_name and connection and session:
                await apply_preset(connection, session, preview_name)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\033[?25h\033[H\033[J")
        sys.stdout.flush()

    if quit_preview and preview and session and original_colors:
        profile = await session.async_get_profile()
        await restore_colors(profile, original_colors)

    return result_name

async def main(connection):
    favorites = load_favorites()
    args = set(sys.argv[1:])
    full_mode = "--full" in args or "-f" in args
    preview_mode = "--preview" in args or "-p" in args
    all_names = load_all_theme_names() if full_mode else None

    session = None
    if preview_mode:
        app = await iterm2.async_get_app(connection)
        session = app.current_terminal_window.current_tab.current_session

    name = await pick_theme(
        favorites, all_names,
        connection=connection if preview_mode else None,
        session=session,
        preview=preview_mode,
    )

    if name is None:
        os._exit(0)

    try:
        preset = await iterm2.ColorPreset.async_get(connection, name)
    except Exception:
        print(f"Theme '{name}' not found.")
        print("Import via: Preferences → Profiles → Colors → Color Presets → Import")
        os._exit(1)

    if not preview_mode:
        app = await iterm2.async_get_app(connection)
        session = app.current_terminal_window.current_tab.current_session

    profile = await session.async_get_profile()
    await profile.async_set_color_preset(preset)
    print(f"Applied: {name}")
    os._exit(0)

iterm2.run_until_complete(main)
