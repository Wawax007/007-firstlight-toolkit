"""
rpkg.py — مكتبة قراءة/كتابة موارد RPKG v2 للعبة 007 First Light
rpkg.py — RPKG v2 read/write library for 007 First Light

كل السكربتات الأخرى تستورد من هذا الملف.
All other scripts import from this module.
"""
import os, struct, time
import lz4.block as L

# ============================================================
# ثوابت التشفير / Crypto constants
# ============================================================
XTEA_KEY = [0x68AC3361, 0x562B4AA0, 0xB9F2771F, 0x28EB3CE7]
XTEA_DELTA = 0x9E3779B9
XTEA_ROUNDS = 32

# مفتاح XOR على الـ blob المضغوط (دوري كل 8 بايت)
# XOR scramble key on the compressed blob (cycles every 8 bytes)
XOR_KEY = bytes([0xDC, 0x45, 0xA6, 0x9C, 0xD3, 0x72, 0x4C, 0xAB])

def xor_scramble(data):
    """تشفير/فك تشفير XOR | XOR encrypt/decrypt (symmetric)"""
    return bytes(c ^ XOR_KEY[i & 7] for i, c in enumerate(data))

# ============================================================
# XTEA
# ============================================================
def _xtea_enc_block(v0, v1):
    s = 0
    for _ in range(XTEA_ROUNDS):
        v0 = (v0 + (((v1 << 4) ^ (v1 >> 5)) + v1 ^ (s + XTEA_KEY[s & 3]))) & 0xFFFFFFFF
        s = (s + XTEA_DELTA) & 0xFFFFFFFF
        v1 = (v1 + (((v0 << 4) ^ (v0 >> 5)) + v0 ^ (s + XTEA_KEY[(s >> 11) & 3]))) & 0xFFFFFFFF
    return v0, v1

def _xtea_dec_block(v0, v1):
    s = (XTEA_DELTA * XTEA_ROUNDS) & 0xFFFFFFFF
    for _ in range(XTEA_ROUNDS):
        v1 = (v1 - (((v0 << 4) ^ (v0 >> 5)) + v0 ^ (s + XTEA_KEY[(s >> 11) & 3]))) & 0xFFFFFFFF
        s = (s - XTEA_DELTA) & 0xFFFFFFFF
        v0 = (v0 - (((v1 << 4) ^ (v1 >> 5)) + v1 ^ (s + XTEA_KEY[s & 3]))) & 0xFFFFFFFF
    return v0, v1

def xtea_encrypt(data):
    """تشفير XTEA مع padding صفري لمضاعفات 8 | XTEA encrypt with zero padding to multiple of 8"""
    pad = (-len(data)) % 8
    data = data + b"\x00" * pad
    out = bytearray()
    for i in range(0, len(data), 8):
        v0, v1 = struct.unpack_from("<II", data, i)
        v0, v1 = _xtea_enc_block(v0, v1)
        out += struct.pack("<II", v0, v1)
    return bytes(out)

def xtea_decrypt(data):
    """فك تشفير XTEA | XTEA decrypt"""
    assert len(data) % 8 == 0, "XTEA data must be a multiple of 8 bytes"
    out = bytearray()
    for i in range(0, len(data), 8):
        v0, v1 = struct.unpack_from("<II", data, i)
        v0, v1 = _xtea_dec_block(v0, v1)
        out += struct.pack("<II", v0, v1)
    return bytes(out)

# ============================================================
# RPKG v2 header / tables
# magic '2KPR' @ 0x00, hashCount @ 0x0D, t1Size @ 0x11, t2Size @ 0x15, t1 begins @ 0x19
# ============================================================
def read_header(chunk_path):
    """يقرأ رأس RPKG ويرجع dict | Read RPKG header"""
    with open(chunk_path, "rb") as f:
        magic = f.read(4)
        if magic != b"2KPR":
            raise ValueError(f"Not an RPKG v2 file: magic={magic!r}")
        f.seek(0x0D)
        hashCount = struct.unpack("<I", f.read(4))[0]
        t1Size    = struct.unpack("<I", f.read(4))[0]
        t2Size    = struct.unpack("<I", f.read(4))[0]
    return {
        "hashCount": hashCount,
        "table1Size": t1Size, "table2Size": t2Size,
        "table1Offset": 0x19, "table2Offset": 0x19 + t1Size,
    }

def read_tables(chunk_path):
    """يرجع (header, t1_bytearray, t2_bytearray)"""
    h = read_header(chunk_path)
    with open(chunk_path, "rb") as f:
        f.seek(h["table1Offset"]); t1 = bytearray(f.read(h["table1Size"]))
        f.seek(h["table2Offset"]); t2 = bytearray(f.read(h["table2Size"]))
    return h, t1, t2

def t1_iter(t1, hashCount):
    """مولّد (index, hash, offset, sizeField) | yields each t1 record"""
    for i in range(hashCount):
        h, o, s = struct.unpack_from("<QQI", t1, i * 20)
        yield i, h, o, s

def find_resource(t1, hashCount, hash_value):
    """ابحث عن مورد بـ hash. hash_value سلسلة hex أو int.
       Find a resource by hash. Returns (index, offset, sizeField) or None."""
    target = int(hash_value, 16) if isinstance(hash_value, str) else hash_value
    for i, h, o, s in t1_iter(t1, hashCount):
        if h == target:
            return i, o, s
    return None

def t2_record_offset(t2, index):
    """احسب موقع سجل index في table2 | compute the t2 record offset for index"""
    pos = 0
    for k in range(index):
        dbs = struct.unpack_from("<I", t2, pos + 4)[0]
        pos += 20 + dbs
    return pos

def t2_record_info(t2, rec_off):
    """يرجع (type_str, dbs, dsz) للسجل | record (type, data-block-size, decomp-size)"""
    type_rev = bytes(t2[rec_off:rec_off + 4])
    dbs = struct.unpack_from("<I", t2, rec_off + 4)[0]
    dsz = struct.unpack_from("<I", t2, rec_off + 8)[0]
    return type_rev[::-1].decode("latin-1", errors="replace"), dbs, dsz

# ============================================================
# قراءة/كتابة موارد | Resource read/write
# ============================================================
def read_resource(chunk_path, t1, t2, index):
    """يقرأ مورد ويفكّ ضغطه. يرجع (raw_bytes, type_str)
       Read & decompress a resource. Returns (raw_bytes, type_str)."""
    h, off, sf = struct.unpack_from("<QQI", t1, index * 20)
    comp_size = sf & 0x3FFFFFFF
    is_xor = (sf >> 31) & 1
    rec_off = t2_record_offset(t2, index)
    type_str, dbs, dsz = t2_record_info(t2, rec_off)
    with open(chunk_path, "rb") as f:
        f.seek(off); blob = f.read(comp_size)
    if is_xor: blob = xor_scramble(blob)
    if comp_size == 0 or comp_size == dsz:
        return blob[:dsz], type_str    # غير مضغوط | uncompressed
    raw = L.decompress(blob, uncompressed_size=dsz)
    return raw, type_str

def write_resource_eof(chunk_path, t1, t2, index, raw_bytes):
    """يكتب مورد جديد بإلحاقه في نهاية الملف ويعدّل الجدولين.
       Write a new resource by appending at EOF; patch t1 + t2 in-memory.
       يرجع (new_offset, new_comp_size_with_xor_flag) | returns (new_off, sf)."""
    nc = L.compress(raw_bytes, mode="high_compression", compression=12, store_size=False)
    nd = xor_scramble(nc)
    # تحقق round-trip قبل الكتابة | round-trip readback gate
    assert L.decompress(xor_scramble(nd), uncompressed_size=len(raw_bytes)) == raw_bytes, \
        "Round-trip verification failed; refusing to write"
    h, _, _ = struct.unpack_from("<QQI", t1, index * 20)
    with open(chunk_path, "r+b") as f:
        f.seek(0, 2); noff = f.tell(); f.write(nd)
    sf = len(nd) | 0x80000000
    struct.pack_into("<QQI", t1, index * 20, h, noff, sf)
    rec_off = t2_record_offset(t2, index)
    struct.pack_into("<I", t2, rec_off + 8, len(raw_bytes))
    return noff, sf

def commit_tables(chunk_path, t1, t2):
    """اكتب الجدولين للقرص + اضبط mtime=2020 لإجبار إعادة التحميل.
       Write tables to disk + set mtime=2020 to force reload."""
    h = read_header(chunk_path)
    with open(chunk_path, "r+b") as f:
        f.seek(h["table1Offset"]); f.write(t1)
        f.seek(h["table2Offset"]); f.write(t2)
        f.flush(); os.fsync(f.fileno())
    t = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, -1))
    os.utime(chunk_path, (t, t))

def backup_chunk(chunk_path, backup_dir):
    """نسخة احتياطية للجدولين + ميتاداتا | Backup tables + size meta"""
    import json
    os.makedirs(backup_dir, exist_ok=True)
    h, t1, t2 = read_tables(chunk_path)
    with open(os.path.join(backup_dir, "table1.bin"), "wb") as f: f.write(t1)
    with open(os.path.join(backup_dir, "table2.bin"), "wb") as f: f.write(t2)
    with open(os.path.join(backup_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "chunk_path": chunk_path,
            "chunk_size": os.path.getsize(chunk_path),
            "hashCount": h["hashCount"],
            "table1Size": h["table1Size"],
            "table2Size": h["table2Size"],
        }, f, indent=2)
    return h, t1, t2