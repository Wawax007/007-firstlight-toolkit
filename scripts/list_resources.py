"""
list_resources.py — استعرض الموارد داخل ملف chunk
list_resources.py — List resources in a chunk file

الاستخدام | Usage:
  python list_resources.py <chunk.rpkg> [--type GFXF|LOCR|DLGE|...]
  python list_resources.py <chunk.rpkg> --hash <hash_hex>
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpkg

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    chunk_path = args[0]
    filt_type = None; filt_hash = None
    i = 1
    while i < len(args):
        if args[i] == "--type" and i + 1 < len(args):
            filt_type = args[i + 1].upper(); i += 2
        elif args[i] == "--hash" and i + 1 < len(args):
            filt_hash = args[i + 1].upper(); i += 2
        else:
            print(f"❌ unknown arg: {args[i]}"); sys.exit(1)

    header, t1, t2 = rpkg.read_tables(chunk_path)
    print(f"📦 {chunk_path}")
    print(f"   hashCount = {header['hashCount']:,}\n")
    print(f"{'idx':>8}  {'hash':>16}  {'type':<5}  {'offset':>12}  {'comp':>10}  {'decomp':>10}")
    print("-" * 80)

    count = 0
    for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
        hex_hash = f"{h:016X}"
        if filt_hash and hex_hash != filt_hash: continue
        rec_off = rpkg.t2_record_offset(t2, idx)
        type_str, dbs, dsz = rpkg.t2_record_info(t2, rec_off)
        if filt_type and type_str != filt_type: continue
        comp = sf & 0x3FFFFFFF
        print(f"{idx:>8}  {hex_hash}  {type_str:<5}  {off:>12,}  {comp:>10,}  {dsz:>10,}")
        count += 1

    print(f"\n✅ {count:,} resource(s) listed")

if __name__ == "__main__":
    main()