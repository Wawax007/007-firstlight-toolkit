"""
install_font.py — أداة موحّدة: استخراج + بناء + حقن خط
install_font.py — All-in-one: extract + build + inject a font

الاستخدام | Usage:
  python tools/install_font.py --config examples/arabic/font_config.json
  python tools/install_font.py --config my.json --game-dir "D:/Games/007 First Light"
  python tools/install_font.py --restore

ما يسويه | What it does:
  1. يكتشف اللعبة تلقائياً  | Auto-detect game
  2. يستخرج الخط الأصلي     | Extract original font (one-time backup)
  3. يبني GFXF جديد         | Build new GFXF from your TTFs per config
  4. يحقن في chunk0          | Inject into chunk0 (tables backed up)
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg, gfxf, steam

FONT_HASH = "01DD9580958CDC9B"   # hash مورد الخط الإنجليزي في 007


def cmd_install(args):
    game = args.game_dir or steam.find_game()
    if not game:
        print("❌ ما لقيت اللعبة. مرّر المسار بـ --game-dir.")
        print("❌ Game not found. Pass the path with --game-dir.")
        return 2
    chunk0 = os.path.join(game, "Runtime", "chunk0.rpkg")
    if not os.path.isfile(chunk0):
        print(f"❌ chunk0 missing: {chunk0}"); return 2
    print(f"🎮 game: {game}")

    if not os.path.isfile(args.config):
        print(f"❌ config not found: {args.config}"); return 2
    print(f"📋 config: {args.config}")
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    backup_dir = os.path.join(game, "Runtime", "_font_backup")
    os.makedirs(backup_dir, exist_ok=True)

    print("\n📖 reading chunk0...")
    header, t1, t2 = rpkg.read_tables(chunk0)
    found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
    if found is None:
        print(f"❌ font resource missing: {FONT_HASH}"); return 3
    idx, off, sf = found
    rec_off = rpkg.t2_record_offset(t2, idx)
    type_str, _, dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   type = {type_str} | size = {dsz:,} B")

    orig_font = os.path.join(backup_dir, "original_font.GFXF")
    if not os.path.isfile(orig_font):
        print("\n📤 extracting original font (one-time backup)...")
        raw, _ = rpkg.read_resource(chunk0, t1, t2, idx)
        with open(orig_font, "wb") as f:
            f.write(raw)
        print(f"   ✅ saved: {orig_font}")
    else:
        print("\n💾 original font already backed up")

    print("\n💾 backing up tables...")
    rpkg.backup_chunk(chunk0, backup_dir)

    print("\n🔨 building new font...")
    src_bytes = open(orig_font, "rb").read()
    new_bytes = gfxf.build(src_bytes, config, verbose=True)
    print(f"✅ built ({len(new_bytes):,} B) — size-neutral")

    print("\n💉 injecting into chunk0...")
    old_size = os.path.getsize(chunk0)
    new_off, new_sf = rpkg.write_resource_eof(chunk0, t1, t2, idx, new_bytes)
    rpkg.commit_tables(chunk0, t1, t2)
    new_size = os.path.getsize(chunk0)

    print("\n" + "=" * 50)
    print("✅ Font installed successfully!")
    print("=" * 50)
    print(f"   new offset:    {new_off:,}")
    print(f"   compressed:    {new_sf & 0x3FFFFFFF:,} B")
    print(f"   chunk0 size:   {old_size:,} -> {new_size:,}")
    print(f"   backup:        {backup_dir}")
    print("\n🎮 Launch the game now.")
    return 0


def cmd_restore(args):
    game = args.game_dir or steam.find_game()
    if not game:
        print("❌ game not found"); return 2
    chunk0 = os.path.join(game, "Runtime", "chunk0.rpkg")
    backup_dir = os.path.join(game, "Runtime", "_font_backup")
    print(f"🔄 restoring chunk0 from {backup_dir}...")
    meta = rpkg.restore_chunk(chunk0, backup_dir)
    print(f"✅ restored. chunk0 size: {os.path.getsize(chunk0):,}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="007 First Light — Font Installer")
    ap.add_argument("--config", help="JSON config (TTF mapping + codepoints)")
    ap.add_argument("--game-dir", help="manually specify the game folder")
    ap.add_argument("--restore", action="store_true", help="restore the original font")
    args = ap.parse_args()

    if args.restore:
        return cmd_restore(args)
    if not args.config:
        ap.print_help(); return 1
    return cmd_install(args)


if __name__ == "__main__":
    sys.exit(main())
