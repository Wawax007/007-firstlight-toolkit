"""
list_resources.py — استعراض الموارد داخل chunk
list_resources.py — List resources inside a chunk

الاستخدام | Usage:
  python tools/list_resources.py <chunk.rpkg>
  python tools/list_resources.py <chunk.rpkg> --type GFXF
  python tools/list_resources.py <chunk.rpkg> --type LOCR --hash 01179467BC0E9F2F
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from glacier import rpkg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chunk", help="path to chunk*.rpkg")
    ap.add_argument("--type", help="filter by resource type (GFXF, LOCR, DLGE, ...)")
    ap.add_argument("--hash", help="filter by specific hash (hex)")
    args = ap.parse_args()

    if not os.path.isfile(args.chunk):
        print(f"❌ chunk not found: {args.chunk}")
        return 2

    header, t1, t2 = rpkg.read_tables(args.chunk)
    print(f"📦 {args.chunk}")
    print(f"   hashCount = {header['hashCount']:,}\n")
    print(f"{'idx':>8}  {'hash':>16}  {'type':<5}  {'offset':>14}  {'comp':>12}  {'decomp':>12}")
    print("-" * 80)

    filt_type = args.type.upper() if args.type else None
    filt_hash = args.hash.upper() if args.hash else None
    count = 0

    for idx, h, off, sf in rpkg.t1_iter(t1, header["hashCount"]):
        hex_hash = "%016X" % h
        if filt_hash and hex_hash != filt_hash:
            continue
        rec_off = rpkg.t2_record_offset(t2, idx)
        type_str, dbs, dsz = rpkg.t2_record_info(t2, rec_off)
        if filt_type and type_str != filt_type:
            continue
        comp = sf & 0x3FFFFFFF
        print(f"{idx:>8}  {hex_hash}  {type_str:<5}  {off:>14,}  {comp:>12,}  {dsz:>12,}")
        count += 1

    print(f"\n✅ {count:,} resource(s) listed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
