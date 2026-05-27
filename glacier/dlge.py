"""
dlge.py — استخراج/حقن نصوص الحوار وأسماء المتحدّثين (DLGE)
dlge.py — Dialogue text & speaker names (DLGE) extraction & injection

تخطيط DLGE | DLGE layout:
  bytes 0..26:    27-byte header (treated as opaque)
  @ offset 27:
    u32 tag3 = 3
    u32 tag3_len
    tag3_len bytes (XTEA-encrypted localized dialogue per language)
    u32 tag4 = 4
    8 bytes  (marker, not a length)
    byte 0x00
    u32 base_len
    base_len bytes (XTEA-encrypted "base block" — what English-locale players see)
    ...

  Base block plaintext format (after XTEA decrypt, null-terminated):
    //[SPEAKER_CODE]\\//{DisplayName}\\//(timing)\\SPOKEN_TEXT
       ^ field 0          ^ field 1     ^ field 2

    Multi-segment: //(timing1)\\seg1//(timing2)\\seg2 ...
"""
import re
import struct
from . import rpkg

HDR = 27   # طول رأس DLGE | DLGE header length

# regexes
FIELD = re.compile(rb"//(.*?)\\\\")
TIM = re.compile(r"//\([^)]*\)\\\\")


# ============================================================
# قراءة base block | Reading the base block
# ============================================================
def _parse_base_offsets(raw):
    """يحدّد إزاحات base block. يرجع dict أو None.
       Locate the base block. Returns dict with offsets or None."""
    o = HDR
    if rpkg.u32(raw, o) != 3:
        return None
    o = o + 8 + rpkg.u32(raw, o + 4)
    if rpkg.u32(raw, o) != 4:
        return None
    o += 8
    if o >= len(raw) or raw[o] != 0:
        return None
    base_off = o
    base_len = rpkg.u32(raw, o + 1)
    base_end = o + 5 + base_len
    if base_len == 0 or base_end > len(raw):
        return None
    return {
        "base_off": base_off,
        "base_payload_off": o + 5,
        "base_len": base_len,
        "base_end": base_end,
    }


def get_base_text(raw):
    """يستخرج base block كنص. | Get the base block as text. Returns str or None."""
    info = _parse_base_offsets(raw)
    if info is None:
        return None
    try:
        pt = rpkg.xtea_decrypt(raw[info["base_payload_off"]:
                                   info["base_payload_off"] + info["base_len"]])
        return pt.split(b"\x00")[0].decode("latin-1")
    except Exception:
        return None


def parse_speaker(text):
    """يستخرج اسم المتحدّث من base block.
       Extract speaker info from base block.
       يرجع dict أو None. | Returns dict or None.
         {speaker_code, speaker_name, has_zero_placeholder}"""
    if text is None:
        return None
    fields = list(FIELD.finditer(text.encode("latin-1")))
    if len(fields) < 2:
        return None
    code = fields[0].group(1).decode("utf-8", errors="replace")
    name_raw = fields[1].group(1).decode("utf-8", errors="replace")
    name = name_raw
    if name.startswith("{") and name.endswith("}"):
        name = name[1:-1]
    has_zero = "{0}" in name
    name_core = name.replace("{0}", "").strip()
    return {
        "speaker_code": code,
        "speaker_name": name_core,
        "has_zero_placeholder": has_zero,
    }


def parse_segments(text):
    """يفصّل النص المنطوق إلى مقاطع زمنية.
       Split spoken text into timed segments.
       يرجع: {'single': '...'} لو مقطع واحد، أو {'seg0': ..., 'seg1': ...}.
       Returns either {'single': '...'} or {'seg0': ..., 'seg1': ...}."""
    if text is None:
        return {}
    tims = list(TIM.finditer(text))
    if not tims:
        return {}
    if len(tims) == 1:
        return {"single": text[tims[0].end():]}
    segs = {}
    for i, m in enumerate(tims):
        end = tims[i + 1].start() if i + 1 < len(tims) else len(text)
        segs["seg%d" % i] = text[m.end():end]
    return segs


# ============================================================
# حقن النص المنطوق | Inject spoken text
# ============================================================
def _segkey(k):
    if k == "single":
        return -1
    m = re.match(r"seg(\d+)", k)
    return int(m.group(1)) if m else 999


def inject_spoken(raw, segments, shape_fn=None):
    """يستبدل النص المنطوق في base block بترجمة جديدة.
       Replace spoken text in the base block with translated segments.

       segments = {'single': '...'} أو {'seg0': ..., 'seg1': ..., ...}
       shape_fn(text) = دالة معالجة نصية اختيارية (مثل reshaping للعربي).
                       Optional text-processing function (e.g. Arabic reshaping).

       يرجع raw_bytes الجديد أو None. | Returns new raw bytes or None."""
    info = _parse_base_offsets(raw)
    if info is None:
        return None
    try:
        pt = rpkg.xtea_decrypt(raw[info["base_payload_off"]:
                                   info["base_payload_off"] + info["base_len"]])
        s = pt.split(b"\x00")[0].decode("latin-1")
    except Exception:
        return None

    tims = list(TIM.finditer(s))
    if not tims:
        return None

    process = shape_fn if shape_fn is not None else (lambda x: x)
    keys = sorted(segments.keys(), key=_segkey)

    if len(tims) == 1:
        if "single" in segments:
            joined = segments["single"]
        else:
            joined = " ".join(segments[k] for k in keys)
        new = s[:tims[0].end()] + process(joined)
    else:
        new = s[:tims[0].end()]
        for k in range(len(tims)):
            tr = segments.get("seg%d" % k)
            if tr is None and k < len(keys):
                tr = segments[keys[k]]
            new += process(tr if tr else "")
            if k + 1 < len(tims):
                new += s[tims[k + 1].start():tims[k + 1].end()]

    ct, _ = rpkg.xtea_encrypt(new.encode("utf-8"))
    return (raw[:info["base_off"]] + b"\x00" + struct.pack("<I", len(ct)) +
            ct + raw[info["base_end"]:])


# ============================================================
# حقن اسم المتحدّث | Inject speaker name (byte-level surgery)
# ============================================================
def inject_speaker(raw, name_map, shape_fn=None):
    """يستبدل اسم المتحدّث (الحقل 1) ببايتات جديدة.
       Replace speaker name (field 1) at byte level.

       name_map = {"English Name": "Translated Name"}.
       shape_fn(text) = دالة معالجة اختيارية.
                       Optional text-processing function.

       يرجع raw_bytes الجديد أو None لو ما كان فيه ترجمة للاسم.
       Returns new raw bytes, or None if name not in map."""
    info = _parse_base_offsets(raw)
    if info is None:
        return None
    try:
        pt = rpkg.xtea_decrypt(raw[info["base_payload_off"]:
                                   info["base_payload_off"] + info["base_len"]])
        sraw = pt.split(b"\x00")[0]
    except Exception:
        return None

    fields = list(FIELD.finditer(sraw))
    if len(fields) < 2:
        return None
    name_blob = fields[1].group(1).decode("utf-8", errors="replace")
    has_zero = "{0}" in name_blob
    if name_blob.startswith("{") and name_blob.endswith("}"):
        name_blob = name_blob[1:-1]
    core = name_blob.replace("{0}", "").strip()
    translated = name_map.get(core)
    if translated is None:
        return None

    process = shape_fn if shape_fn is not None else (lambda x: x)
    shaped = process(translated + ("{0}" if has_zero else ""))
    nn = b"{" + shaped.encode("utf-8") + b"}"
    new_sraw = (sraw[:fields[1].start()] + b"//" + nn + b"\\\\" +
                sraw[fields[1].end():])

    ct, pt2 = rpkg.xtea_encrypt(new_sraw)
    if rpkg.xtea_decrypt(ct).split(b"\x00")[0] != pt2.split(b"\x00")[0]:
        return None
    return (raw[:info["base_off"]] + b"\x00" + struct.pack("<I", len(ct)) +
            ct + raw[info["base_end"]:])
