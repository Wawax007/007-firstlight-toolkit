"""
extract_font.py — استخراج خط GFXF من chunk0
extract_font.py — Extract a GFXF font resource from chunk0

الاستخدام | Usage:
  python extract_font.py <chunk0.rpkg> <hash> <output.GFXF>

مثال | Example (الخط الإنجليزي في 007 First Light):
  python extract_font.py chunk0.rpkg 01DD9580958CDC9B fonts_en.GFXF
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpkg

def main():
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(1)
    chunk_path, hash_hex, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isfile(chunk_path):
        print(f"❌ chunk not found: {chunk_path}"); sys.exit(2)

    print(f"📖 reading {chunk_path} ...")
    header, t1, t2 = rpkg.read_tables(chunk_path)
    print(f"   hashCount = {header['hashCount']:,}")

    found = rpkg.find_resource(t1, header["hashCount"], hash_hex)
    if found is None:
        print(f"❌ hash not found in chunk: {hash_hex}"); sys.exit(3)
    index, offset, sf = found
    rec_off = rpkg.t2_record_offset(t2, index)
    type_str, dbs, dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   index = {index} | type = {type_str} | offset = {offset} | decomp = {dsz:,} B")

    if type_str != "GFXF":
        print(f"⚠️  warning: type is {type_str}, not GFXF. Continuing anyway.")

    raw, _ = rpkg.read_resource(chunk_path, t1, t2, index)
    with open(out_path, "wb") as f: f.write(raw)
    print(f"✅ wrote {out_path} ({len(raw):,} B)")

if __name__ == "__main__":
    main()