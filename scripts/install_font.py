"""
install_font.py — أداة موحّدة: استخراج + بناء + حقن خط في 007 First Light
install_font.py — All-in-one: extract + build + inject a font into 007 First Light

الاستخدام للمستخدم العادي | Typical usage:
  python install_font.py --config examples/arabic/font_config.json

ما يسويه | What it does:
  1. يكتشف مسار اللعبة تلقائياً (Steam library) | Auto-detect game via Steam libraries
  2. يستخرج الخط الأصلي من chunk0 (نسخة احتياطية) | Extract original font from chunk0 (backup)
  3. يبني GFXF جديد من الـ TTF حقّك حسب config | Build new GFXF from your TTF per config
  4. يحقن في chunk0 (نسخة احتياطية للجدولين) | Inject into chunk0 (tables backed up)

استخدام متقدّم | Advanced (provide game path manually):
  python install_font.py --config my.json --game "D:\\Games\\007 First Light"

استرجاع | Restore the original font:
  python install_font.py --restore
"""
import sys, os, json, argparse, re, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpkg

# ============================================================
# اكتشاف اللعبة | Game discovery
# ============================================================
GAME_FOLDER = "007 First Light"
FONT_HASH = "01DD9580958CDC9B"   # المورد الرسومي للخط الإنجليزي (fonts_en)

def _steam_libraries():
    """يقرأ libraryfolders.vdf لإيجاد كل مكتبات Steam | Read Steam library list."""
    libs = []
    candidates = [
        r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
        r"C:\Program Files\Steam\steamapps\libraryfolders.vdf",
        os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steamapps\libraryfolders.vdf"),
    ]
    for vdf in candidates:
        if not os.path.isfile(vdf): continue
        try:
            text = open(vdf, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                libs.append(m.group(1).replace("\\\\", "\\"))
        except Exception: pass
    return libs

def find_game():
    """يبحث عن مجلد اللعبة في كل المسارات المحتملة | Search common game paths."""
    seen = set(); roots = []
    for lib in _steam_libraries():
        p = os.path.join(lib, "steamapps", "common", GAME_FOLDER)
        if p not in seen: seen.add(p); roots.append(p)
    for drive in "CDEFGHI":
        for pat in [r"%s:\SteamLibrary\steamapps\common\%s",
                    r"%s:\Program Files (x86)\Steam\steamapps\common\%s",
                    r"%s:\Steam\steamapps\common\%s",
                    r"%s:\Games\%s",
                    r"%s:\%s"]:
            roots.append(pat % (drive, GAME_FOLDER))
    for p in roots:
        if os.path.isfile(os.path.join(p, "Runtime", "chunk0.rpkg")):
            return p
    return None

# ============================================================
# الاستخراج + البناء + الحقن | Extract + Build + Inject
# ============================================================
def cmd_install(args):
    # 1) إيجاد اللعبة | Locate game
    game = args.game or find_game()
    if not game:
        print("❌ ما لقيت اللعبة | game not found. استخدم --game لتمرير المسار يدوياً.")
        return 2
    chunk0 = os.path.join(game, "Runtime", "chunk0.rpkg")
    if not os.path.isfile(chunk0):
        print(f"❌ chunk0 غير موجود في: {chunk0}"); return 2
    print(f"🎮 اللعبة | game: {game}")

    # 2) قراءة الـ config | Load config
    if not os.path.isfile(args.config):
        print(f"❌ ملف الإعداد غير موجود | config not found: {args.config}"); return 2
    print(f"📋 الإعداد | config: {args.config}")

    # 3) مجلدات العمل + النسخ الاحتياطية | Work dir + backups
    backup_dir = os.path.join(game, "Runtime", "_font_backup")
    work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_work")
    work_dir = os.path.abspath(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(backup_dir, exist_ok=True)

    # 4) قراءة الجدولين + إيجاد مورد الخط | Read tables + find font resource
    print("\n📖 قراءة chunk0 | reading chunk0...")
    header, t1, t2 = rpkg.read_tables(chunk0)
    found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
    if found is None:
        print(f"❌ مورد الخط مو موجود | font resource missing: {FONT_HASH}"); return 3
    idx, off, sf = found
    rec_off = rpkg.t2_record_offset(t2, idx)
    type_str, _, dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   نوع | type = {type_str} | الحجم | size = {dsz:,} B")

    # 5) استخراج الخط الأصلي (مرّة واحدة) | Extract original font (once)
    orig_font = os.path.join(backup_dir, "original_font.GFXF")
    if not os.path.isfile(orig_font):
        print("\n📤 استخراج الخط الأصلي | extracting original font...")
        raw, _ = rpkg.read_resource(chunk0, t1, t2, idx)
        with open(orig_font, "wb") as f: f.write(raw)
        print(f"   ✅ محفوظ في | saved: {orig_font}")
    else:
        print(f"\n💾 الخط الأصلي محفوظ مسبقاً | original font already backed up")

    # 6) نسخة احتياطية من الجدولين | Backup tables
    print("\n💾 نسخة احتياطية للجدولين | backing up tables...")
    rpkg.backup_chunk(chunk0, backup_dir)

    # 7) بناء الخط الجديد | Build new font
    new_font = os.path.join(work_dir, "new_font.GFXF")
    print("\n🔨 بناء الخط الجديد | building new font...")
    import build_font, sys as _sys
    _argv_save = _sys.argv
    _sys.argv = ["build_font.py", "--src", orig_font, "--out", new_font, "--config", args.config]
    try: build_font.main()
    finally: _sys.argv = _argv_save

    # 8) حقن في chunk0 | Inject into chunk0
    print("\n💉 حقن في chunk0 | injecting into chunk0...")
    raw = open(new_font, "rb").read()
    old_size = os.path.getsize(chunk0)
    new_off, new_sf = rpkg.write_resource_eof(chunk0, t1, t2, idx, raw)
    rpkg.commit_tables(chunk0, t1, t2)
    new_size = os.path.getsize(chunk0)

    print("\n" + "=" * 50)
    print("✅ تم تركيب الخط بنجاح! | Font installed successfully!")
    print("=" * 50)
    print(f"   إزاحة جديدة | new offset:    {new_off:,}")
    print(f"   حجم مضغوط | compressed:     {new_sf & 0x3FFFFFFF:,} B")
    print(f"   حجم chunk0:                 {old_size:,} → {new_size:,}")
    print(f"   نسخة احتياطية | backup:     {backup_dir}")
    print("\n🎮 شغّل اللعبة الآن | launch the game now")
    return 0

# ============================================================
# الاسترجاع | Restore
# ============================================================
def cmd_restore(args):
    game = args.game or find_game()
    if not game: print("❌ ما لقيت اللعبة | game not found"); return 2
    chunk0 = os.path.join(game, "Runtime", "chunk0.rpkg")
    backup_dir = os.path.join(game, "Runtime", "_font_backup")
    orig_font = os.path.join(backup_dir, "original_font.GFXF")
    meta_file = os.path.join(backup_dir, "meta.json")
    t1_file = os.path.join(backup_dir, "table1.bin")
    t2_file = os.path.join(backup_dir, "table2.bin")

    for f in (orig_font, meta_file, t1_file, t2_file):
        if not os.path.isfile(f):
            print(f"❌ نسخة احتياطية ناقصة | backup incomplete: {f}"); return 3

    meta = json.load(open(meta_file, encoding="utf-8"))
    print(f"🔄 استرجاع | restoring chunk0...")
    print(f"   حجم أصلي | original size: {meta['chunk_size']:,}")

    # ارجع للحجم الأصلي | truncate to original size, restore tables
    with open(chunk0, "r+b") as f:
        f.truncate(meta["chunk_size"])
        f.seek(0x19); f.write(open(t1_file, "rb").read())
        f.seek(0x19 + meta["table1Size"]); f.write(open(t2_file, "rb").read())
        f.flush(); os.fsync(f.fileno())
    import time
    t = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, -1))
    os.utime(chunk0, (t, t))
    print(f"✅ تم الاسترجاع | restored. حجم chunk0: {os.path.getsize(chunk0):,}")
    return 0

# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="007 First Light — Font Installer / مثبّت خطوط",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("--config", help="JSON config (TTF mapping + codepoints)")
    ap.add_argument("--game", help="manually specify the game folder")
    ap.add_argument("--restore", action="store_true", help="restore original font")
    args = ap.parse_args()

    if args.restore: sys.exit(cmd_restore(args))
    if not args.config:
        ap.print_help(); sys.exit(1)
    sys.exit(cmd_install(args))

if __name__ == "__main__":
    main()