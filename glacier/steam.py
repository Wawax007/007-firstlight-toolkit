"""
steam.py — اكتشاف مسار اللعبة تلقائياً
steam.py — Auto-detect game installation
"""
import os
import re

GAME_FOLDER_NAME = "007 First Light"


def _steam_libraries():
    """يقرأ libraryfolders.vdf لإيجاد كل مكتبات Steam.
       Parse libraryfolders.vdf to find all Steam library roots."""
    libs = []
    candidates = [
        r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
        r"C:\Program Files\Steam\steamapps\libraryfolders.vdf",
        os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps\libraryfolders.vdf"),
        os.path.expanduser(r"~/.steam/steam/steamapps/libraryfolders.vdf"),
        os.path.expanduser(r"~/.local/share/Steam/steamapps/libraryfolders.vdf"),
    ]
    for vdf in candidates:
        if not os.path.isfile(vdf):
            continue
        try:
            text = open(vdf, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                libs.append(m.group(1).replace("\\\\", "\\"))
        except Exception:
            pass
    return libs


def find_game(folder_name=None):
    """يبحث عن مجلد اللعبة. يرجع المسار أو None.
       Search for the game folder. Returns path or None."""
    folder = folder_name or GAME_FOLDER_NAME
    seen = set()
    roots = []

    for lib in _steam_libraries():
        p = os.path.join(lib, "steamapps", "common", folder)
        if p not in seen:
            seen.add(p); roots.append(p)

    for drive in "CDEFGHI":
        for pat in [
            r"%s:\SteamLibrary\steamapps\common\%s",
            r"%s:\Program Files (x86)\Steam\steamapps\common\%s",
            r"%s:\Steam\steamapps\common\%s",
            r"%s:\Games\%s",
            r"%s:\%s",
        ]:
            roots.append(pat % (drive, folder))

    for p in roots:
        if os.path.isfile(os.path.join(p, "Runtime", "chunk0.rpkg")):
            return p
    return None


def chunk_paths(game_root):
    """يرجع قائمة بمسارات الـ chunks في اللعبة.
       Return list of chunk file paths in the game."""
    runtime = os.path.join(game_root, "Runtime")
    if not os.path.isdir(runtime):
        return []
    chunks = []
    for name in sorted(os.listdir(runtime)):
        if name.startswith("chunk") and name.endswith(".rpkg"):
            chunks.append(os.path.join(runtime, name))
    return chunks
