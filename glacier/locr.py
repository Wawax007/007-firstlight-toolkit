"""
locr.py — استخراج/حقن نصوص الواجهة (LOCR)
locr.py — UI strings (LOCR) extraction & injection

تخطيط LOCR | LOCR layout:
  byte 0:    flags
  bytes 1..: nLang * u32 offsets to per-language blocks
  each block at its offset:
    u32 count
    repeated count times:
      u32 keyHash
      u32 cipherLen
      cipherLen bytes XTEA-encrypted UTF-8 (null-terminated, padded to 8)
      1 byte separator (0x00)

  Languages by index (007 First Light, 15 langs):
    0  = unused/marker
    1  = English  ← localization target for this game (OFFLINE base)
    2..14 = other languages
"""
import re
import struct
from . import rpkg

# tokens داخل النص اللي ما نلمسها | inline tokens we don't touch
INLINE_TOKEN = re.compile(r"\{[^{}]*\}|<b>|</b>|<li>|</li>|\[\d+\]|%[A-Za-z_][A-Za-z0-9_]*%")


# ============================================================
# استخراج | Extraction
# ============================================================
def extract_strings(raw, lang_index=1):
    """يستخرج النصوص من LOCR للغة معيّنة.
       Extract strings from LOCR for a given language index.
       يرجع {hashHex: text}.
       Returns {hashHex: text} dict."""
    result = {}
    if len(raw) < 5:
        return result
    try:
        nLang = (rpkg.u32(raw, 1) - 1) // 4
        if nLang <= 0 or nLang > 30:
            return result
        offs = [rpkg.u32(raw, 1 + i * 4) for i in range(nLang)]
    except struct.error:
        return result

    if lang_index >= nLang or offs[lang_index] == 0xFFFFFFFF:
        return result

    o = offs[lang_index]
    try:
        count = rpkg.u32(raw, o); o += 4
        if count > 100000:
            return result
        for _ in range(count):
            kh = rpkg.u32(raw, o); o += 4
            ln = rpkg.u32(raw, o); o += 4
            if ln > 100000 or o + ln + 1 > len(raw):
                break
            blob = raw[o:o + ln]; o += ln + 1   # +1 separator
            if len(blob) == 0 or len(blob) % 8 != 0:
                continue
            try:
                pt = rpkg.xtea_decrypt(blob)
                text = pt.split(b"\x00")[0].decode("utf-8")
                result["%08X" % kh] = text
            except Exception:
                continue
    except struct.error:
        pass
    return result


# ============================================================
# الحقن | Injection
# ============================================================
def rebuild(raw, translations, lang_index=1):
    """يعيد بناء LOCR مع استبدال النصوص للغة المحدّدة.
       Rebuild LOCR replacing strings for the specified language.

       translations = {hashHex: text} (مفاتيح UPPERCASE).
       Translations keys must be UPPERCASE hex strings.

       يرجع (new_raw, injected_count).
       Returns (new_raw, injected_count)."""
    nLang = (rpkg.u32(raw, 1) - 1) // 4
    offs = [rpkg.u32(raw, 1 + i * 4) for i in range(nLang)]
    out = bytearray(raw[0:1])
    body = bytearray()
    new_offs = []
    base = 1 + nLang * 4
    injected = 0

    for li, off in enumerate(offs):
        if off == 0xFFFFFFFF:
            new_offs.append(0xFFFFFFFF)
            continue
        new_offs.append(base + len(body))
        o = off
        count = rpkg.u32(raw, o); o += 4
        block = bytearray(struct.pack("<I", count))
        for _ in range(count):
            kh = rpkg.u32(raw, o); o += 4
            ln = rpkg.u32(raw, o); o += 4
            blob = raw[o:o + ln]; o += ln
            sep = raw[o:o + 1]; o += 1
            khx = "%08X" % kh
            if li == lang_index and khx in translations:
                ct, pt = rpkg.xtea_encrypt(translations[khx].encode("utf-8"))
                # تحقق round-trip | round-trip verify
                if rpkg.xtea_decrypt(ct).split(b"\x00")[0] != pt.split(b"\x00")[0]:
                    block += struct.pack("<I", kh) + struct.pack("<I", ln) + blob + sep
                    continue
                block += struct.pack("<I", kh) + struct.pack("<I", len(ct)) + ct + b"\x00"
                injected += 1
            else:
                block += struct.pack("<I", kh) + struct.pack("<I", ln) + blob + sep
        body += block

    for x in new_offs:
        out += struct.pack("<I", x)
    out += body
    return bytes(out), injected


def list_resource_keys(raw, lang_index=1):
    """قائمة بكل مفاتيح الـ hashes الموجودة في الـ LOCR للغة معيّنة.
       List all key hashes present in LOCR for a given language."""
    out = []
    if len(raw) < 5:
        return out
    try:
        nLang = (rpkg.u32(raw, 1) - 1) // 4
        if nLang <= 0 or lang_index >= nLang:
            return out
        off = rpkg.u32(raw, 1 + lang_index * 4)
        if off == 0xFFFFFFFF:
            return out
        o = off
        count = rpkg.u32(raw, o); o += 4
        for _ in range(count):
            kh = rpkg.u32(raw, o); o += 4
            ln = rpkg.u32(raw, o); o += 4
            o += ln + 1
            out.append("%08X" % kh)
    except struct.error:
        pass
    return out
