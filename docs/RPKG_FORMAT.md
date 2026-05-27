# RPKG v2 Format — صيغة ملفات اللعبة
# RPKG v2 Format — Game archive format

تستخدمها لعبة 007 First Light (Glacier engine, 2025) وألعاب IO Interactive الحديثة.
Used by 007 First Light (Glacier engine, 2025) and recent IO Interactive titles.

> **ملاحظة**: هذا التوثيق نتيجة هندسة عكسية (reverse engineering). لا توجد مواصفات رسمية.
> **Note**: This documentation is the result of reverse engineering. No official specs exist.

---

## الرأس | Header (25 bytes)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00   | 4    | bytes | Magic `2KPR` (RPK2 backwards) |
| 0x04   | 1    | u8    | Version (= 1) |
| 0x05   | 8    | bytes | Unknown / padding |
| 0x0D   | 4    | u32   | `hashCount` — number of resources |
| 0x11   | 4    | u32   | `table1Size` — must equal `20 * hashCount` |
| 0x15   | 4    | u32   | `table2Size` — variable |
| 0x19   | —    | —    | **table1 begins here** |

---

## Table 1 — Resource Directory

تكرار بقيمة `hashCount`، كل سجل 20 بايت:
Repeats `hashCount` times, 20 bytes each:

```c
struct Table1Entry {
    uint64_t hash;        // Resource hash (FNV-1a-ish, IOI-internal)
    uint64_t offset;      // Absolute file offset to data blob
    uint32_t sizeField;
};
```

`sizeField` decomposition:
- **bit 31**: `1` if data blob is XOR-scrambled, `0` if plain.
- **bits 0–30**: compressed size on disk (low 30 bits).

```python
xor_scrambled = (sizeField >> 31) & 1
compressed_size = sizeField & 0x3FFFFFFF
```

---

## Table 2 — Type Directory

يبدأ مباشرة بعد table1 @ `0x19 + table1Size`. سجلات متغيّرة الطول.
Starts immediately after table1 @ `0x19 + table1Size`. Variable-length records.

```c
struct Table2Record {
    char     type[4];       // Type stored *reversed* — see below
    uint32_t dbs;           // Data block size (further metadata bytes that follow)
    uint32_t dsz;           // Decompressed size of the resource
    uint8_t  meta[dbs - 8]; // Additional type-specific metadata
};
```

**Stride** = `20 + dbs`.

### نوع المورد مخزّن معكوساً | Type stored reversed

| In-file | Logical |
|---------|---------|
| `RCOL`  | `LOCR` (localization, UI strings) |
| `EGLD`  | `DLGE` (dialogue) |
| `FXFG`  | `GFXF` (Scaleform GFX, fonts/UI) |
| `RDHS`  | `SHDR` (shader) |
| ...     | ...     |

---

## Data Blob

`offset` يشير لـ blob حجمه `compressed_size`. الترتيب:
`offset` points to a blob of size `compressed_size`. Order of operations:

1. **If `xor_scrambled` bit is set**: XOR with the fixed 8-byte key `DC 45 A6 9C D3 72 4C AB` (cycles every 8 bytes).
2. **If `compressed_size == dsz` or `compressed_size == 0`**: blob is uncompressed.
3. **Otherwise**: LZ4-block decompress (no header, `store_size=False`).

التشفير متماثل (XOR هو XOR) فالاتجاه عكسي للحقن:
The XOR is symmetric, so injection reverses the order:

1. LZ4-block compress (`mode=high_compression, compression=12, store_size=False`).
2. XOR-scramble.
3. Append at chunk EOF, patch table1 (new offset + sizeField with bit31 set), patch table2 (`dsz`).
4. Set `mtime=2020` on the chunk to force re-read.

---

## Recovery / Reload

- **Patches don't need to be in-place** — appending at EOF and updating table1 works fine.
- **The engine re-reads tables every launch**; there's no integrity gate.
- **`mtime=2020`** triggers reload (engine compares timestamps).

---

## Per-game Constants (007 First Light)

| Constant | Value |
|----------|-------|
| `chunk0` hashCount | 284,971 |
| `chunk1` hashCount | 464,014 |
| Font resource (English) | `01DD9580958CDC9B` (in chunk0) |
| String XTEA key | `0x68AC3361 0x562B4AA0 0xB9F2771F 0x28EB3CE7` |
| String XTEA rounds | 32 |
| String XTEA delta | `0x9E3779B9` |
| XOR scramble key | `DC 45 A6 9C D3 72 4C AB` |
| LOCR English lang_index | 1 |
| Number of LOCR languages | 15 |

---

## Per-resource Encryption

Some resource types have an additional layer **inside** the decompressed blob:

- **LOCR / DLGE**: Each individual string is XTEA-encrypted, null-terminated, then padded to a multiple of 8 bytes.
- **GFXF**: No additional encryption; it's a Scaleform GFX container.

See `glacier/locr.py` and `glacier/dlge.py` for the per-type structure.
