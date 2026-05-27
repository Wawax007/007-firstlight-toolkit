"""
extract_text.py — استخراج كل النصوص من chunks للترجمة
extract_text.py — Extract all translatable text from chunks

ينتج 3 ملفات | Produces 3 files:
  <output_dir>/ui.json          نصوص الواجهة (LOCR)         | UI strings (LOCR)
  <output_dir>/dialogue.json    نصوص الحوار (DLGE)          | Dialogue strings (DLGE)
  <output_dir>/speakers.json    أسماء المتحدّثين الفريدة     | Unique speaker names

الاستخدام | Usage:
  python tools/extract_text.py --game-dir "D:/.../007 First Light" --out texts/
  python tools/extract_text.py --chunks chunk0.rpkg chunk1.rpkg --out texts/

اللغة الافتراضية للاستخراج | Default language to extract = 1 (English).
"""
import sys
import os
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg, locr, dlge, steam


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--game-dir", help="game install directory (auto-finds chunks)")
    src.add_argument("--chunks", nargs="+", help="explicit chunk file paths")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--lang-index", type=int, default=1,
                    help="LOCR language index to extract (default 1 = English)")
    args = ap.parse_args()

    # حدّد chunks | resolve chunks
    if args.game_dir:
        chunks = steam.chunk_paths(args.game_dir)
        if not chunks:
            print(f"❌ no chunks found under {args.game_dir}/Runtime/"); return 2
    else:
        chunks = args.chunks

    os.makedirs(args.out, exist_ok=True)
    ui_strings = {}
    dialogue_entries = {}
    speaker_names = set()

    for chunk in chunks:
        if not os.path.isfile(chunk):
            print(f"⚠️  skip (not found): {chunk}"); continue
        print(f"\n📖 reading {chunk}")
        header, t1, t2 = rpkg.read_tables(chunk)
        roff = rpkg.build_record_offsets(t2, header["hashCount"])
        print(f"   hashCount = {header['hashCount']:,}")

        c_locr = c_dlge = 0
        for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
            type_rev = bytes(t2[roff[idx]:roff[idx] + 4])

            if type_rev == rpkg.TYPE_LOCR:
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                strings = locr.extract_strings(raw, args.lang_index)
                if strings:
                    ui_strings.setdefault("%016X" % h, {}).update(strings)
                    c_locr += len(strings)

            elif type_rev == rpkg.TYPE_DLGE:
                raw, _ = rpkg.read_resource(chunk, t1, t2, idx, roff)
                if raw is None: continue
                text = dlge.get_base_text(raw)
                if text is None: continue
                speaker = dlge.parse_speaker(text)
                segments = dlge.parse_segments(text)
                if speaker is None or not segments: continue
                # نسجّل اسم المتحدّث | record speaker name
                if speaker["speaker_name"]:
                    speaker_names.add(speaker["speaker_name"])
                dialogue_entries["%016X" % h] = {
                    "speaker_name": speaker["speaker_name"],
                    "speaker_code": speaker["speaker_code"],
                    "has_zero_placeholder": speaker["has_zero_placeholder"],
                    "segments": segments,
                }
                c_dlge += 1

        print(f"   UI resources extracted: {c_locr:,}")
        print(f"   DLGE entries extracted: {c_dlge:,}")

    # اكتب الملفات | write files
    ui_path = os.path.join(args.out, "ui.json")
    dlg_path = os.path.join(args.out, "dialogue.json")
    spk_path = os.path.join(args.out, "speakers.json")

    with open(ui_path, "w", encoding="utf-8") as f:
        json.dump(ui_strings, f, ensure_ascii=False, indent=2)
    with open(dlg_path, "w", encoding="utf-8") as f:
        json.dump(dialogue_entries, f, ensure_ascii=False, indent=2)
    # خريطة أسماء فارغة جاهزة للتعبئة | empty name map ready to fill
    speakers_template = {name: "" for name in sorted(speaker_names)}
    with open(spk_path, "w", encoding="utf-8") as f:
        json.dump(speakers_template, f, ensure_ascii=False, indent=2)

    print(f"\n✅ wrote:")
    print(f"   {ui_path}      ({sum(len(v) for v in ui_strings.values()):,} UI strings "
          f"across {len(ui_strings):,} resources)")
    print(f"   {dlg_path}     ({len(dialogue_entries):,} dialogue entries)")
    print(f"   {spk_path}     ({len(speakers_template):,} unique speaker names — "
          f"fill in translations)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
