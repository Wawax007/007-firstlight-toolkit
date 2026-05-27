"""
inject_font.py — حقن GFXF في chunk0 (طريقة EOF-append)
inject_font.py — Inject a GFXF into chunk0 (EOF-append method)

الاستخدام | Usage:
  python inject_font.py --chunk <chunk0.rpkg> --hash <hex> --gfxf <font.GFXF> \
      [--backup <dir>]

ما يسويه | What it does:
  1. ياخذ نسخة احتياطية من جدولي chunk0 (إن طُلب)
  2. يلحق الـ GFXF الجديد بنهاية الـ chunk
  3. يعدّل table1 (offset + sizeField | XOR flag)
  4. يعدّل table2 (decompressed size)
  5. يضبط mtime=2020 لإجبار اللعبة تعيد التحميل
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpkg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", required=True, help="path to chunk0.rpkg")
    ap.add_argument("--hash", required=True, help="resource hash (hex)")
    ap.add_argument("--gfxf", required=True, help="GFXF file to inject")
    ap.add_argument("--backup", help="backup directory (recommended)")
    args = ap.parse_args()

    if not os.path.isfile(args.chunk): sys.exit(f"❌ chunk not found: {args.chunk}")
    if not os.path.isfile(args.gfxf): sys.exit(f"❌ GFXF not found: {args.gfxf}")

    print(f"📖 reading {args.chunk}")
    header, t1, t2 = rpkg.read_tables(args.chunk)

    if args.backup:
        print(f"💾 backing up tables → {args.backup}")
        rpkg.backup_chunk(args.chunk, args.backup)

    found = rpkg.find_resource(t1, header["hashCount"], args.hash)
    if found is None: sys.exit(f"❌ hash not found: {args.hash}")
    idx, old_off, old_sf = found
    rec_off = rpkg.t2_record_offset(t2, idx)
    type_str, _, old_dsz = rpkg.t2_record_info(t2, rec_off)
    print(f"   index = {idx} | type = {type_str} | old offset = {old_off:,} | "
          f"old decomp = {old_dsz:,}")
    if type_str != "GFXF":
        print(f"⚠️  warning: type is {type_str}, expected GFXF. Continuing.")

    raw = open(args.gfxf, "rb").read()
    print(f"📦 injecting {len(raw):,} B")
    old_size = os.path.getsize(args.chunk)
    new_off, new_sf = rpkg.write_resource_eof(args.chunk, t1, t2, idx, raw)
    rpkg.commit_tables(args.chunk, t1, t2)
    new_size = os.path.getsize(args.chunk)

    print(f"\n✅ INJECTED")
    print(f"   new offset = {new_off:,}")
    print(f"   new comp = {new_sf & 0x3FFFFFFF:,}  (XOR flag = {new_sf >> 31})")
    print(f"   chunk size = {new_size:,}  (+{new_size - old_size:,})")
    print(f"   mtime armed to 2020 — game will reload on next launch")

if __name__ == "__main__":
    main()