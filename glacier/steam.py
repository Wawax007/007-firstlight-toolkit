"""
steam.py — اكتشاف مسار اللعبة تلقائياً
steam.py — Auto-detect game installation

يكتشف اللعبة على أي متجر أو مسار (Steam / GOG / Epic / Xbox / مجلد مخصص).
Detects the game on any store or path (Steam / GOG / Epic / Xbox / custom folder).
لا يعتمد على Steam إطلاقاً — الحقن يعمل على ملفات Glacier الخام مباشرة.
No Steam/DRM dependency — injection operates on the raw Glacier chunk files.
"""
import os
import re
import string

GAME_FOLDER_NAME = "007 First Light"
SENTINEL = os.path.join("Runtime", "chunk0.rpkg")   # علامة اللعبة | game sentinel


def _valid(path):
    """يتحقق إن المسار يحوي اللعبة فعلاً. | True if path holds the game."""
    return bool(path) and os.path.isfile(os.path.join(path, SENTINEL))


def _drives():
    """كل أقراص النظام المتوفّرة. | All available drive roots."""
    out = []
    for letter in string.ascii_uppercase:
        root = "%s:\\" % letter
        if os.path.isdir(root):
            out.append(root)
    if not out:              # لينكس / ماك | POSIX fallback
        out = ["/"]
    return out


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


def _store_paths(folder):
    """مسارات المتاجر المعروفة على كل قرص (Steam/GOG/Epic/generic).
       Known store install paths across every drive."""
    roots = []
    # مكتبات Steam من الـ VDF | Steam libraries from VDF
    for lib in _steam_libraries():
        roots.append(os.path.join(lib, "steamapps", "common", folder))
    # أنماط ثابتة على كل قرص | fixed patterns on every drive
    for d in _drives():
        dl = d.rstrip("\\/")            # "C:" أو "" على POSIX
        for tail in [
            r"SteamLibrary\steamapps\common\%s",
            r"Program Files (x86)\Steam\steamapps\common\%s",
            r"Steam\steamapps\common\%s",
            r"GOG Games\%s",
            r"GOG Galaxy\Games\%s",
            r"Program Files (x86)\GOG Galaxy\Games\%s",
            r"Epic Games\%s",
            r"Program Files\Epic Games\%s",
            r"Games\%s",
            r"%s",
        ]:
            roots.append(os.path.join(dl + os.sep, tail % folder))
    return roots


def _xbox_paths():
    """مسارات Xbox / Game Pass (مع طبقة Content الإضافية).
       Xbox / Game Pass paths (extra Content layer)."""
    roots = []
    for d in _drives():
        for box in ("XboxGames", "Xbox", "Games"):
            base = os.path.join(d, box)
            if not os.path.isdir(base):
                continue
            try:
                for child in os.listdir(base):
                    cp = os.path.join(base, child)
                    roots.append(os.path.join(cp, "Content"))
                    roots.append(cp)
            except Exception:
                pass
    return roots


# مجلدات نظام نتخطّاها في المسح الشامل | system dirs to skip in full scan
_SKIP = {
    "windows", "$recycle.bin", "system volume information", "appdata",
    "programdata", "perflogs", "recovery", "msocache", "onedrive",
    "windows.old", "intel", "amd", "nvidia", "drivers", "temp", "tmp",
    "node_modules", ".git", "boot", "config.msi", "$windows.~bt",
    "$windows.~ws", "windowsapps", "dosdevices",
}
_MAXDEPTH = 7


def _full_scan(folder):
    """مسح كامل مقيّد العمق لكل قرص يدوّر Runtime\\chunk0.rpkg.
       Depth-bounded walk of every drive for Runtime\\chunk0.rpkg.
       يغطّي النسخ DRM-free في مجلدات مخصّصة. | Covers DRM-free custom folders."""
    for d in _drives():
        for cur, dirs, files in os.walk(d):
            rel = os.path.relpath(cur, d)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth >= _MAXDEPTH:
                dirs[:] = []
                continue
            dirs[:] = [x for x in dirs
                       if x.lower() not in _SKIP and not x.startswith("$")]
            if "chunk0.rpkg" in files and os.path.basename(cur).lower() == "runtime":
                cand = os.path.dirname(cur)
                if _valid(cand):
                    return cand
    return None


def find_game(folder_name=None):
    """يبحث عن مجلد اللعبة عبر أربع طبقات. يرجع المسار أو None.
       Locate the game via four stages. Returns path or None.

       1. Steam (VDF) + known store paths (GOG / Epic / generic) on every drive
       2. Xbox / Game Pass directories
       3. Full depth-bounded scan of every drive (DRM-free / custom folders)
       أول تطابق يفوز. الـ GUI يوفّر منتقي يدوي كطبقة أخيرة.
       First match wins. The GUI provides a manual picker as the final fallback."""
    folder = folder_name or GAME_FOLDER_NAME
    seen = set()

    for p in _store_paths(folder) + _xbox_paths():
        if p in seen:
            continue
        seen.add(p)
        if _valid(p):
            return p

    return _full_scan(folder)


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
