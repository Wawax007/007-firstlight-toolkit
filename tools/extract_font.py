"""
extract_font.py — استخراج خط GFXF من chunk
extract_font.py — Extract a GFXF font resource from a chunk

الاستخدام | Usage:
  python tools/extract_font.py <chunk.rpkg> <hash_hex> <output.GFXF>

مثال (الخط الإنجليزي في 007 First Light):
Example (English font in 007 First Light):
  python tools/extract_font.py chunk0.rpkg 01DD9580958CDC9B fonts_en.GFXF
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg


def main():
    if len(sys.argv) != 4:
        print(__doc__); return 1
    chunk_path, hash_hex, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isfile(chunk_path):
        print(f"❌ chunk not found: {chunk_path}"); return 2

    print(f"📖 reading {chunk_path}")
    header, t1, t2 = rpkg.read_tables(chunk_path)
    print(f"   hashCount = {header['hashCount']:,}")

    found = rpkg.find_resource(t1, header["hashCount"], hash_hex)
    if found is None:
        print(f"❌ hash not found: {hash_hex}"); return 3
    idx, off, sf = found
    rec_off = rpkg.t2_record_offset(t2, idx)
    type_str, _, dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   idx = {idx} | type = {type_str} | offset = {off:,} | decomp = {dsz:,}")

    if type_str != "GFXF":
        print(f"⚠️  warning: type is {type_str}, expected GFXF. Continuing.")

    raw, _ = rpkg.read_resource(chunk_path, t1, t2, idx)
    if raw is None:
        print("❌ failed to decompress resource"); return 4

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(raw)
    print(f"✅ wrote {out_path} ({len(raw):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
