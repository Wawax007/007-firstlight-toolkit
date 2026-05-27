"""
install_translation.py — المثبّت الموحّد للترجمة الكاملة
install_translation.py — All-in-one translation installer

ينفّذ كل شي بأمر واحد | Does everything in one command:
  1. تركيب الخط (لو متوفّر)   | Install font (if provided)
  2. حقن نصوص الواجهة (LOCR)  | Inject UI translations (LOCR)
  3. حقن نصوص الحوار (DLGE)   | Inject dialogue translations (DLGE)
  4. حقن أسماء المتحدّثين     | Inject speaker name translations

الاستخدام | Usage:
  python tools/install_translation.py --config my_translation.json

صيغة config | Config schema (JSON):
{
  "language": "arabic",         // اسم اللغة (يحدّد طريقة الـ shaping)
                                // language name (selects shaping mode)
  "font": "path/to/font.json",  // إعداد الخط (اختياري)
                                // font config (optional)
  "ui": "path/to/ui.json",      // ترجمة الواجهة (اختياري)
                                // UI translation (optional)
  "dialogue": "path/to/dialogue.json",  // ترجمة الحوار (اختياري)
  "speakers": "path/to/speakers.json",  // أسماء المتحدّثين (اختياري)
  "game_dir": "..."             // مسار اللعبة (اختياري - يكتشف تلقائياً)
}

اللغات اللي تستخدم shaping | Languages that use shaping:
  arabic, persian, urdu, pashto, kashmiri, sindhi

غيرهم → identity (نص خام).
Others → identity (raw text passthrough).
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg, locr, dlge, gfxf, shaping, steam

FONT_HASH = "01DD9580958CDC9B"


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_install(config_path, dry_run=False):
    if not os.path.isfile(config_path):
        print(f"❌ config not found: {config_path}"); return 2
    config_dir = os.path.dirname(os.path.abspath(config_path))
    config = load_json(config_path)

    # حلّ المسارات النسبية للملفات المُشار إليها داخل config
    # resolve relative paths in config to absolute paths
    def resolve(p):
        if p is None: return None
        return p if os.path.isabs(p) else os.path.join(config_dir, p)

    language = config.get("language", "none")
    font_cfg_path = resolve(config.get("font"))
    ui_path = resolve(config.get("ui"))
    dlg_path = resolve(config.get("dialogue"))
    spk_path = resolve(config.get("speakers"))
    game = config.get("game_dir") or steam.find_game()

    if not game or not os.path.isfile(os.path.join(game, "Runtime", "chunk0.rpkg")):
        print("❌ game not found. Set game_dir in config or pass --game-dir.")
        return 2
    print(f"🎮 game: {game}")
    print(f"🌐 language: {language}")
    print(f"   font:      {font_cfg_path or '(none)'}")
    print(f"   ui:        {ui_path or '(none)'}")
    print(f"   dialogue:  {dlg_path or '(none)'}")
    print(f"   speakers:  {spk_path or '(none)'}")
    if dry_run:
        print("\n*** DRY RUN — no writes ***\n")

    # اختر دالة الـ shaping | pick shaping function
    if language in ("arabic", "persian", "urdu", "pashto", "kashmiri", "sindhi"):
        if not shaping.AVAILABLE:
            print("⚠️  install: pip install arabic_reshaper python-bidi")
            print("    (shaping not available — proceeding without it; "
                  "RTL languages will likely render wrong)")
            shape_fn = shaping.identity
            shape_block_fn = lambda t: t
        else:
            shape_fn = shaping.shape_line
            shape_block_fn = shaping.shape_block
    else:
        shape_fn = shaping.identity
        shape_block_fn = lambda t: t

    # حمّل ملفات الترجمة | load translation files
    ui_data = load_json(ui_path) if ui_path else {}
    dlg_data = load_json(dlg_path) if dlg_path else {}
    spk_data = load_json(spk_path) if spk_path else {}
    spk_clean = {k: v for k, v in spk_data.items() if v}   # تجاهل القيم الفارغة

    chunks = steam.chunk_paths(game)
    if not chunks:
        print(f"❌ no chunks in {game}/Runtime/"); return 3

    backup_dir = os.path.join(game, "Runtime", "_toolkit_backup")
    os.makedirs(backup_dir, exist_ok=True)

    for chunk in chunks:
        name = os.path.basename(chunk)
        print(f"\n=== {name} ===")
        if not dry_run:
            rpkg.backup_chunk(chunk, os.path.join(backup_dir, name))

        header, t1, t2 = rpkg.read_tables(chunk)
        roff = rpkg.build_record_offsets(t2, header["hashCount"])
        n_ui = n_dlg = n_spk = 0

        # 1) LOCR
        if ui_data:
            for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
                if bytes(t2[roff[idx]:roff[idx] + 4]) != rpkg.TYPE_LOCR:
                    continue
                hh = "%016X" % h
                if hh not in ui_data:
                    continue
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                # shape كل سلسلة في الـ resource | shape every string
                translations = {k.upper(): shape_block_fn(v)
                                for k, v in ui_data[hh].items()}
                try:
                    new_raw, ginj = locr.rebuild(raw, translations, lang_index=1)
                except Exception:
                    continue
                if ginj == 0:
                    continue
                n_ui += ginj
                if dry_run: continue
                rpkg.write_resource_eof(chunk, t1, t2, idx, new_raw, roff)

        # 2+3) DLGE + speakers
        if dlg_data or spk_clean:
            for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
                if bytes(t2[roff[idx]:roff[idx] + 4]) != rpkg.TYPE_DLGE:
                    continue
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                hh = "%016X" % h
                changed = False

                # نص الحوار | dialogue text
                if hh in dlg_data:
                    segs = dlg_data[hh].get("segments")
                    if segs:
                        new_raw = dlge.inject_spoken(raw, segs, shape_fn=shape_block_fn)
                        if new_raw is not None:
                            raw = new_raw; changed = True; n_dlg += 1

                # اسم المتحدّث | speaker name
                if spk_clean:
                    new_raw = dlge.inject_speaker(raw, spk_clean, shape_fn=shape_fn)
                    if new_raw is not None:
                        raw = new_raw; changed = True; n_spk += 1

                if not changed: continue
                if dry_run: continue
                rpkg.write_resource_eof(chunk, t1, t2, idx, raw, roff)

        # 4) FONT (chunk0 only)
        if font_cfg_path and chunk == chunks[0]:
            found = rpkg.find_resource(t1, header["hashCount"], FONT_HASH)
            if found is not None:
                idx_f, _, _ = found
                # استخرج الأصلي لو ما هو محفوظ | extract original if needed
                font_backup = os.path.join(backup_dir, "original_font.GFXF")
                if not os.path.isfile(font_backup):
                    raw_f, _ = rpkg.read_resource(chunk, t1, t2, idx_f, roff)
                    with open(font_backup, "wb") as f: f.write(raw_f)
                src_bytes = open(font_backup, "rb").read()
                font_config = load_json(font_cfg_path)
                new_font = gfxf.build(src_bytes, font_config, verbose=False)
                print(f"   font: built {len(new_font):,} B")
                if not dry_run:
                    rpkg.write_resource_eof(chunk, t1, t2, idx_f, new_font, roff)

        if not dry_run:
            rpkg.commit_tables(chunk, t1, t2)
        print(f"   UI strings: {n_ui:,}  |  dialogue: {n_dlg:,}  |  speakers: {n_spk:,}")

    print("\n" + "=" * 50)
    if dry_run:
        print("✅ Dry run complete — no changes written.")
    else:
        print("✅ Translation installed successfully!")
        print(f"   backup: {backup_dir}")
        print("\n🎮 Launch the game now.")
    print("=" * 50)
    return 0


def cmd_restore(game_dir):
    game = game_dir or steam.find_game()
    if not game:
        print("❌ game not found"); return 2
    backup_dir = os.path.join(game, "Runtime", "_toolkit_backup")
    if not os.path.isdir(backup_dir):
        print(f"❌ no backup at {backup_dir}"); return 3
    chunks = steam.chunk_paths(game)
    for chunk in chunks:
        name = os.path.basename(chunk)
        sub = os.path.join(backup_dir, name)
        if os.path.isdir(sub):
            print(f"🔄 restoring {name}...")
            rpkg.restore_chunk(chunk, sub)
    print("✅ restored.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="007 First Light — Translation Installer")
    ap.add_argument("--config", help="JSON config with paths to ui/dialogue/speakers/font")
    ap.add_argument("--game-dir", help="manually specify the game folder")
    ap.add_argument("--dry", action="store_true", help="dry run — no writes")
    ap.add_argument("--restore", action="store_true", help="restore from backup")
    args = ap.parse_args()

    if args.restore:
        return cmd_restore(args.game_dir)
    if not args.config:
        ap.print_help(); return 1
    return cmd_install(args.config, dry_run=args.dry)


if __name__ == "__main__":
    sys.exit(main())
