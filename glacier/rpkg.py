"""
rpkg.py — قراءة/كتابة موارد RPKG v2
rpkg.py — RPKG v2 resource I/O

المعمارية | Architecture:
  magic '2KPR' @ 0x00
  hashCount  @ 0x0D (u32)
  t1 size    @ 0x11 (u32)
  t2 size    @ 0x15 (u32)
  table1     @ 0x19           — 20 bytes per record: <Q hash><Q offset><I sizeField>
                                  sizeField bit31 = XOR scramble flag
                                  sizeField low30 = compressed size
  table2     @ 0x19 + t1size  — variable-length records:
                                  type[4] (reversed: LOCR→'RCOL'), dbs[4], dsz[4@+8], dbs bytes

  data blocks: optionally XOR-scrambled with the engine's fixed 8-byte key,
               then LZ4-compressed (high_compression level 12).
"""
import os
import struct
import time
import lz4.block as L

# ============================================================
# ثوابت التشفير | Crypto constants
# ============================================================
XTEA_KEY = [0x68AC3361, 0x562B4AA0, 0xB9F2771F, 0x28EB3CE7]
XTEA_DELTA = 0x9E3779B9
XTEA_ROUNDS = 32

XOR_KEY = bytes([0xDC, 0x45, 0xA6, 0x9C, 0xD3, 0x72, 0x4C, 0xAB])

# نوع البيانات يُخزَّن معكوساً في table2 | Type is stored reversed in table2
TYPE_LOCR = b"RCOL"   # UI strings
TYPE_DLGE = b"EGLD"   # Dialogue
TYPE_GFXF = b"FXFG"   # Fonts (Scaleform GFX)

# ============================================================
# XOR scramble
# ============================================================
def xor_scramble(data):
    """تشفير XOR متماثل (يفك ويشفّر بنفس العملية) | Symmetric XOR scramble."""
    return bytes(c ^ XOR_KEY[i & 7] for i, c in enumerate(data))

# ============================================================
# XTEA — تشفير النصوص داخل LOCR/DLGE | string-level XTEA for LOCR/DLGE
# ============================================================
def _xtea_enc_block(v0, v1):
    s = 0
    M = 0xFFFFFFFF
    for _ in range(XTEA_ROUNDS):
        v0 = (v0 + ((((v1 << 4) & M) ^ (v1 >> 5)) + v1 ^ (s + XTEA_KEY[s & 3]))) & M
        s = (s + XTEA_DELTA) & M
        v1 = (v1 + ((((v0 << 4) & M) ^ (v0 >> 5)) + v0 ^ (s + XTEA_KEY[(s >> 11) & 3]))) & M
    return v0, v1

def _xtea_dec_block(v0, v1):
    s = (XTEA_DELTA * XTEA_ROUNDS) & 0xFFFFFFFF
    M = 0xFFFFFFFF
    for _ in range(XTEA_ROUNDS):
        v1 = (v1 - ((((v0 << 4) & M) ^ (v0 >> 5)) + v0 ^ (s + XTEA_KEY[(s >> 11) & 3]))) & M
        s = (s - XTEA_DELTA) & M
        v0 = (v0 - ((((v1 << 4) & M) ^ (v1 >> 5)) + v1 ^ (s + XTEA_KEY[s & 3]))) & M
    return v0, v1

def xtea_encrypt(data):
    """تشفير XTEA مع padding صفري لمضاعفات 8 (null-terminate أيضاً).
       XTEA encrypt with null-terminator + zero-pad to multiple of 8."""
    pt = data + b"\x00"
    while len(pt) % 8:
        pt += b"\x00"
    out = bytearray()
    for i in range(0, len(pt), 8):
        v0, v1 = struct.unpack_from("<II", pt, i)
        v0, v1 = _xtea_enc_block(v0, v1)
        out += struct.pack("<II", v0, v1)
    return bytes(out), pt

def xtea_decrypt(data):
    """فك تشفير XTEA | XTEA decrypt. Returns plaintext bytes."""
    if len(data) % 8 != 0:
        raise ValueError(f"XTEA input length {len(data)} not multiple of 8")
    out = bytearray()
    for i in range(0, len(data), 8):
        v0, v1 = struct.unpack_from("<II", data, i)
        v0, v1 = _xtea_dec_block(v0, v1)
        out += struct.pack("<II", v0, v1)
    return bytes(out)

# ============================================================
# Header + tables
# ============================================================
def read_header(chunk_path):
    """يقرأ رأس RPKG ويرجع dict | Read RPKG header."""
    with open(chunk_path, "rb") as f:
        magic = f.read(4)
        if magic != b"2KPR":
            raise ValueError(f"Not an RPKG v2 file: magic={magic!r}")
        f.seek(0x0D)
        hashCount = struct.unpack("<I", f.read(4))[0]
        t1Size = struct.unpack("<I", f.read(4))[0]
        t2Size = struct.unpack("<I", f.read(4))[0]
    return {
        "hashCount": hashCount,
        "table1Size": t1Size,
        "table2Size": t2Size,
        "table1Offset": 0x19,
        "table2Offset": 0x19 + t1Size,
    }

def read_tables(chunk_path):
    """يرجع (header, t1_bytearray, t2_bytearray)."""
    h = read_header(chunk_path)
    with open(chunk_path, "rb") as f:
        f.seek(h["table1Offset"])
        t1 = bytearray(f.read(h["table1Size"]))
        f.seek(h["table2Offset"])
        t2 = bytearray(f.read(h["table2Size"]))
    return h, t1, t2

def t1_iter(t1, hashCount):
    """مولّد (index, hash, offset, sizeField) | yield each t1 record."""
    for i in range(hashCount):
        h, o, s = struct.unpack_from("<QQI", t1, i * 20)
        yield i, h, o, s

def find_resource(t1, hashCount, hash_value):
    """ابحث عن مورد بـ hash. يرجع (index, offset, sizeField) أو None.
       Find resource by hash. Returns (index, offset, sizeField) or None."""
    target = int(hash_value, 16) if isinstance(hash_value, str) else hash_value
    for i, h, o, s in t1_iter(t1, hashCount):
        if h == target:
            return i, o, s
    return None

def build_record_offsets(t2, hashCount):
    """احسب موقع كل سجل في table2 (مرّة واحدة، أسرع من إعادة الحساب).
       Compute record offset for each index (cached lookup)."""
    roff = [0] * hashCount
    pos = 0
    for i in range(hashCount):
        roff[i] = pos
        dbs = struct.unpack_from("<I", t2, pos + 4)[0]
        pos += 20 + dbs
    return roff

def t2_record_offset(t2, index):
    """احسب موقع سجل في table2 | compute t2 record offset for one index."""
    pos = 0
    for k in range(index):
        dbs = struct.unpack_from("<I", t2, pos + 4)[0]
        pos += 20 + dbs
    return pos

def t2_record_info(t2, rec_off):
    """يرجع (type_str, dbs, dsz) | record (type, data-block-size, decomp-size)."""
    type_rev = bytes(t2[rec_off:rec_off + 4])
    dbs = struct.unpack_from("<I", t2, rec_off + 4)[0]
    dsz = struct.unpack_from("<I", t2, rec_off + 8)[0]
    return type_rev[::-1].decode("latin-1", errors="replace"), dbs, dsz

# ============================================================
# Resource read/write
# ============================================================
def read_resource(chunk_path, t1, t2, index, roff=None):
    """يقرأ مورد ويفكّ ضغطه. يرجع (raw_bytes, type_str).
       Read & decompress a resource. Returns (raw_bytes, type_str)."""
    h, off, sf = struct.unpack_from("<QQI", t1, index * 20)
    comp = sf & 0x3FFFFFFF
    is_xor = (sf >> 31) & 1
    rec_off = roff[index] if roff is not None else t2_record_offset(t2, index)
    type_str, dbs, dsz = t2_record_info(t2, rec_off)
    with open(chunk_path, "rb") as f:
        f.seek(off)
        # comp == 0 means the resource is stored uncompressed (dsz bytes on disk),
        # possibly still XOR-scrambled (e.g. TEXT resources).
        blob = f.read(comp if comp else dsz)
    if is_xor:
        blob = xor_scramble(blob)
    if comp == 0 or comp == dsz:
        return blob[:dsz], type_str   # غير مضغوط | uncompressed
    try:
        raw = L.decompress(blob, uncompressed_size=dsz)
        return raw, type_str
    except Exception:
        return None, type_str

def write_resource_eof(chunk_path, t1, t2, index, raw_bytes, roff=None):
    """يكتب مورد بإلحاقه في نهاية الـ chunk ويعدّل الجدولين.
       Append a resource at EOF and patch tables in-memory.
       يرجع (new_off, sf_with_flag) | returns (new_off, sf)."""
    nc = L.compress(raw_bytes, mode="high_compression", compression=12, store_size=False)
    nd = xor_scramble(nc)
    # تحقق round-trip | round-trip readback gate
    if L.decompress(xor_scramble(nd), uncompressed_size=len(raw_bytes)) != raw_bytes:
        raise RuntimeError("Round-trip verification failed; refusing to write")
    h, _, _ = struct.unpack_from("<QQI", t1, index * 20)
    with open(chunk_path, "r+b") as f:
        f.seek(0, 2)
        noff = f.tell()
        f.write(nd)
    sf = len(nd) | 0x80000000
    struct.pack_into("<QQI", t1, index * 20, h, noff, sf)
    rec_off = roff[index] if roff is not None else t2_record_offset(t2, index)
    struct.pack_into("<I", t2, rec_off + 8, len(raw_bytes))
    return noff, sf

def commit_tables(chunk_path, t1, t2):
    """اكتب الجدولين للقرص + اضبط mtime=2020 لإجبار إعادة التحميل.
       Write tables to disk and stamp mtime=2020 to force engine reload."""
    h = read_header(chunk_path)
    with open(chunk_path, "r+b") as f:
        f.seek(h["table1Offset"])
        f.write(t1)
        f.seek(h["table2Offset"])
        f.write(t2)
        f.flush()
        os.fsync(f.fileno())
    t = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, -1))
    os.utime(chunk_path, (t, t))

def backup_chunk(chunk_path, backup_dir):
    """نسخة احتياطية للجدولين + ميتاداتا. | Backup tables + size metadata."""
    import json
    os.makedirs(backup_dir, exist_ok=True)
    h, t1, t2 = read_tables(chunk_path)
    with open(os.path.join(backup_dir, "table1.bin"), "wb") as f:
        f.write(t1)
    with open(os.path.join(backup_dir, "table2.bin"), "wb") as f:
        f.write(t2)
    with open(os.path.join(backup_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "chunk_path": chunk_path,
            "chunk_size": os.path.getsize(chunk_path),
            "hashCount": h["hashCount"],
            "table1Size": h["table1Size"],
            "table2Size": h["table2Size"],
        }, f, indent=2)
    return h, t1, t2

def restore_chunk(chunk_path, backup_dir):
    """يسترجع chunk من النسخة الاحتياطية. | Restore chunk from backup."""
    import json
    meta_file = os.path.join(backup_dir, "meta.json")
    t1_file = os.path.join(backup_dir, "table1.bin")
    t2_file = os.path.join(backup_dir, "table2.bin")
    for f in (meta_file, t1_file, t2_file):
        if not os.path.isfile(f):
            raise FileNotFoundError(f"Backup incomplete: {f}")
    meta = json.load(open(meta_file, encoding="utf-8"))
    with open(chunk_path, "r+b") as f:
        f.truncate(meta["chunk_size"])
        f.seek(0x19)
        f.write(open(t1_file, "rb").read())
        f.seek(0x19 + meta["table1Size"])
        f.write(open(t2_file, "rb").read())
        f.flush()
        os.fsync(f.fileno())
    t = time.mktime((2020, 1, 1, 0, 0, 0, 0, 0, -1))
    os.utime(chunk_path, (t, t))
    return meta

# ============================================================
# قراءة u32 محصّنة | safe u32 read
# ============================================================
def u32(buf, off):
    """قراءة u32 محصّنة ضد الخروج عن النطاق. | Bounds-safe u32 read."""
    if 0 <= off <= len(buf) - 4:
        return struct.unpack_from("<I", buf, off)[0]
    return 0xFFFFFFFF
