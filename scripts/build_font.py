"""
build_font.py — بناء خط GFXF محقون بـ glyphs من أي TTF
build_font.py — Build a GFXF font with glyphs injected from any TTF

الفكرة | The idea:
  ياخذ GFXF أصلي (مستخرج من اللعبة) + ملفات TTF (واحد لكل وزن) + قائمة
  codepoints تبي تحقنها. يولّد GFXF جديد بنفس الحجم بالبايت يحتوي على
  glyphs لغتك بدلاً من الـ glyphs غير ASCII الأصلية.

  Takes an original GFXF (extracted from the game) + TTF files (one per
  weight) + a list of codepoints to inject. Produces a new size-neutral
  GFXF where the original non-ASCII glyphs are replaced with yours.

الاستخدام | Usage:
  python build_font.py --src fonts_en.GFXF --out my_font.GFXF \
      --config font_config.json

font_config.json مثال | example:
{
  "scale_em": 1024,
  "scale_size": 20,
  "ttf_upm": 1000,
  "flip_y": true,
  "weights": {
    "1": "MyFont-Bold.ttf",
    "4": "MyFont-Regular.ttf",
    "5": "MyFont-SemiBold.ttf",
    "6": "MyFont-Medium.ttf"
  },
  "codepoints": {
    "ranges": [[64144, 65279]],
    "extras": [1548, 1563, 1567, 64818, 1632, 1633, 1634, 1635,
               1636, 1637, 1638, 1639, 1640, 1641]
  }
}

  weights : font_id داخل GFXF → ملف TTF.
            خرائط الـ font_id موجودة في extract_font.py لاحقاً.
  codepoints.ranges  : [start, end] شامل-حصري (مثل range()).
  codepoints.extras  : codepoints مفردة.
  flip_y : true إذا الـ engine يستخدم نظام إحداثيات Y معكوس عن TTF
           (Glacier/Scaleform GFX = true).
  scale  : (scale_em * scale_size) / ttf_upm — يطابق scale الـ engine.
           لـ 007 First Light: 1024 * 20 / 1000 = 20.48
"""
import sys, os, json, struct, argparse
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

# ============================================================
# BitWriter — كتابة بت-بايت لـ SHAPE records
# BitWriter — bit-level writer for SWF SHAPE records
# ============================================================
class BitW:
    def __init__(self): self.acc = 0; self.n = 0; self.buf = bytearray()
    def bit(self, x):
        self.acc = (self.acc << 1) | (x & 1); self.n += 1
        if self.n == 8: self.buf.append(self.acc); self.acc = 0; self.n = 0
    def ub(self, v, n):
        for i in range(n - 1, -1, -1): self.bit((v >> i) & 1)
    def sb(self, v, n):
        if n == 0: return
        if v < 0: v = (1 << n) + v
        self.ub(v, n)
    def out(self):
        if self.n: self.buf.append(self.acc << (8 - self.n)); self.acc = 0; self.n = 0
        return bytes(self.buf)

def nb_signed(v):
    """عدد البتات المطلوبة لتمثيل قيمة signed | bits needed for a signed value"""
    return 0 if v == 0 else abs(int(v)).bit_length() + 1

# ============================================================
# Collect — يجمع contours من glyph
# Collect — collects contours from a glyph
# ============================================================
class Collect(BasePen):
    def __init__(self, gs): super().__init__(gs); self.cs = []; self.cur = None
    def _moveTo(self, p):
        if self.cur: self.cs.append(self.cur)
        self.cur = [("m", p)]
    def _lineTo(self, p): self.cur.append(("l", p))
    def _curveToOne(self, a, b, p): self.cur.append(("c", a, b, p))
    def _qCurveToOne(self, a, p): self.cur.append(("q", a, p))
    def _closePath(self):
        if self.cur: self.cs.append(self.cur); self.cur = None
    def done(self):
        if self.cur: self.cs.append(self.cur); self.cur = None
        return self.cs

# ============================================================
# emit edges
# ============================================================
def emit_straight(w, dx, dy):
    nb = max(nb_signed(dx), nb_signed(dy), 2)
    w.bit(1); w.bit(1); w.ub(nb - 2, 4)
    if dx != 0 and dy != 0:
        w.bit(1); w.sb(dx, nb); w.sb(dy, nb)
    elif dx != 0:
        w.bit(0); w.bit(0); w.sb(dx, nb)
    else:
        w.bit(0); w.bit(1); w.sb(dy, nb)

def emit_curve(w, a, b, c, d):
    nb = max(nb_signed(a), nb_signed(b), nb_signed(c), nb_signed(d), 2)
    w.bit(1); w.bit(0); w.ub(nb - 2, 4)
    w.sb(a, nb); w.sb(b, nb); w.sb(c, nb); w.sb(d, nb)

def build_shape(contours, scale, flip_y):
    """يبني SHAPE record من contours | builds SHAPE record from contours"""
    w = BitW(); w.ub(1, 4); w.ub(0, 4)        # NFB=1, NLB=0
    SX = lambda v: int(round(v * scale))
    SY = lambda v: int(round((-v if flip_y else v) * scale))
    first = True
    for ct in contours:
        m = ct[0]; x, y = SX(m[1][0]), SY(m[1][1])
        # StyleChange: MoveTo + (FillStyle0 on first contour)
        w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(1 if first else 0); w.bit(1)
        mb = max(nb_signed(x), nb_signed(y), 1)
        w.ub(mb, 5); w.sb(x, mb); w.sb(y, mb)
        if first: w.ub(1, 1); first = False
        cx, cy = x, y
        for seg in ct[1:]:
            if seg[0] == "l":
                nx, ny = SX(seg[1][0]), SY(seg[1][1])
                emit_straight(w, nx - cx, ny - cy); cx, cy = nx, ny
            elif seg[0] == "q":
                ctrl, end = seg[1], seg[2]
                ccx, ccy = SX(ctrl[0]), SY(ctrl[1])
                ex, ey = SX(end[0]), SY(end[1])
                emit_curve(w, ccx - cx, ccy - cy, ex - ccx, ey - ccy)
                cx, cy = ex, ey
    # End record
    w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(0)
    return w.out()

def empty_shape():
    """شكل فارغ (لإفراغ glyphs غير مستخدمة) | empty shape for blanking unused glyphs"""
    w = BitW(); w.ub(1, 4); w.ub(0, 4)
    for _ in range(6): w.bit(0)
    return w.out()

# ============================================================
# قراءة tag من GFX stream | read a SWF tag
# ============================================================
def read_tag(buf, p):
    rec = struct.unpack_from("<H", buf, p)[0]
    code = rec >> 6; ln = rec & 0x3F; q = p + 2
    if ln == 0x3F:
        ln = struct.unpack_from("<I", buf, q)[0]; q += 4
    return code, ln, q

# ============================================================
# إعادة بناء DefineFont3 | rebuild a DefineFont3 tag body
# ============================================================
def rebuild_font(b, fid, ar_codepoints, ar_shapes, ar_advances, ES):
    """يستبدل خانات Latin غير ASCII بـ glyphs الجديدة. حياد الحجم بالبايت.
       Replaces non-ASCII Latin slots with new glyphs. Byte-size neutral."""
    LN = len(b)
    flags = b[2]; lang = b[3]; nlen = b[4]; name = b[5:5 + nlen]; p = 5 + nlen
    ng = struct.unpack_from("<H", b, p)[0]; p += 2; ot = p
    offs = [struct.unpack_from("<I", b, ot + i * 4)[0] for i in range(ng + 1)]
    shapes = [b[ot + offs[i]:ot + offs[i + 1]] for i in range(ng)]
    cs = ot + offs[ng]
    codes = [struct.unpack_from("<H", b, cs + i * 2)[0] for i in range(ng)]
    ls = cs + ng * 2
    asc, desc, lead = struct.unpack_from("<hhh", b, ls); ads = ls + 6
    advs = [struct.unpack_from("<h", b, ads + i * 2)[0] for i in range(ng)]
    bnds = ads + ng * 2
    bounds_blob = b[bnds:LN - 2]
    kern = struct.unpack_from("<H", b, LN - 2)[0]

    codes2 = list(codes); shapes2 = list(shapes); advs2 = list(advs)
    # خانات الـ glyphs غير ASCII (codepoint >= 0x80)
    victims = sorted([i for i in range(ng) if codes[i] >= 0x80],
                     key=lambda i: codes[i], reverse=True)
    if len(victims) < len(ar_codepoints):
        raise SystemExit(f"font {fid}: not enough victim slots "
                         f"({len(victims)} < {len(ar_codepoints)})")
    used = set()
    for k, cp in enumerate(ar_codepoints):
        idx = victims[k]; used.add(idx)
        codes2[idx] = cp; shapes2[idx] = ar_shapes[cp]; advs2[idx] = ar_advances[cp]

    def core_len(sh):
        return ((5 + nlen + 2) + (ng + 1) * 4 + sum(len(x) for x in sh) +
                ng * 2 + 6 + ng * 2 + len(bounds_blob) + 2)

    need = core_len(shapes2) - LN
    blanked = 0
    if need > 0:
        spare = sorted([(len(shapes2[i]), i) for i in range(ng)
                        if i not in used and codes2[i] >= 0x80 and shapes2[i] != ES],
                       reverse=True)
        rec = 0
        for sz, i in spare:
            if rec >= need: break
            rec += sz - len(ES); shapes2[i] = ES; blanked += 1
        need = core_len(shapes2) - LN
        if need > 0:
            raise SystemExit(f"font {fid}: cannot fit even after blanking "
                             f"{blanked} glyphs (still need {need} B)")

    # رتّب تصاعدياً حسب codepoint | sort ascending by codepoint
    trip = sorted(zip(codes2, shapes2, advs2), key=lambda x: x[0])
    c3 = [t[0] for t in trip]; s3 = [t[1] for t in trip]; a3 = [t[2] for t in trip]

    head = bytearray()
    head += struct.pack("<H", fid); head.append(flags); head.append(lang)
    head.append(nlen); head += name; head += struct.pack("<H", ng)
    o2 = [(ng + 1) * 4]
    for s in s3: o2.append(o2[-1] + len(s))

    body = (bytes(head)
            + b"".join(struct.pack("<I", o) for o in o2)
            + b"".join(s3)
            + b"".join(struct.pack("<H", c) for c in c3)
            + struct.pack("<hhh", asc, desc, lead)
            + b"".join(struct.pack("<h", x) for x in a3)
            + bounds_blob
            + struct.pack("<H", kern))

    pad = LN - len(body)
    body += b"\x00" * pad
    assert len(body) == LN, f"font {fid}: size mismatch {len(body)} != {LN}"
    print(f"  font {fid}: +{len(ar_codepoints)} glyphs, blanked {blanked}, "
          f"pad {pad}, len {LN} ✅")
    return body

# ============================================================
# main
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description="Build a size-neutral GFXF font with custom glyphs injected from TTF.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="original GFXF (extracted from game)")
    ap.add_argument("--out", required=True, help="output GFXF path")
    ap.add_argument("--config", required=True, help="JSON config file")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f: cfg = json.load(f)

    scale = (cfg["scale_em"] * cfg["scale_size"]) / cfg["ttf_upm"]
    flip_y = cfg.get("flip_y", True)
    weights = {int(k): v for k, v in cfg["weights"].items()}

    # ابني قائمة الـ codepoints | build codepoint list
    cps = set()
    for rng in cfg["codepoints"].get("ranges", []):
        for c in range(rng[0], rng[1]): cps.add(c)
    for c in cfg["codepoints"].get("extras", []): cps.add(c)

    # تحقق إيش متوفر فعلاً في كل TTF | filter by font cmap
    print(f"📐 scale = {scale}  flip_y = {flip_y}")
    print(f"🎯 requested codepoints: {len(cps)}")

    # حضّر shapes + advances لكل وزن | prepare per-weight shapes + advances
    ES = empty_shape()
    ar_shapes_by_fid = {}; ar_advances_by_fid = {}
    ar_codepoints = None
    for fid, ttf_path in weights.items():
        tt = TTFont(ttf_path)
        gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); hm = tt["hmtx"]
        avail = sorted(cp for cp in cps if cp in cmap)
        if ar_codepoints is None: ar_codepoints = avail
        else:
            ar_codepoints = sorted(set(ar_codepoints) & set(avail))
        sh = {}; ad = {}
        for cp in avail:
            gn = cmap[cp]; pen = Collect(gs); gs[gn].draw(pen)
            sh[cp] = build_shape(pen.done(), scale, flip_y)
            ad[cp] = max(-32768, min(32767, int(round(hm[gn][0] * scale))))
        ar_shapes_by_fid[fid] = sh; ar_advances_by_fid[fid] = ad
        print(f"   font {fid} ({os.path.basename(ttf_path)}): {len(avail)} glyphs prepared")

    print(f"✅ intersection across all weights: {len(ar_codepoints)} codepoints")

    # اقرأ الـ GFXF الأصلي | read the original GFXF
    d = open(args.src, "rb").read()
    gfxsz = struct.unpack_from("<I", d, 0x18)[0]
    gfx = d[84:84 + gfxsz]

    # امش على tags | walk tags
    out = bytearray(gfx[:21]); p = 21
    while p < len(gfx):
        code, ln, q = read_tag(gfx, p)
        body = gfx[q:q + ln]
        if code == 75:        # DefineFont3
            fid = struct.unpack_from("<H", body, 0)[0]
            if fid in weights:
                body = rebuild_font(body, fid, ar_codepoints,
                                    ar_shapes_by_fid[fid],
                                    ar_advances_by_fid[fid], ES)
        out += gfx[p:q] + body
        if code == 0 and ln == 0: break
        p = q + ln

    newgfx = bytes(out)
    if len(newgfx) != len(gfx):
        raise SystemExit(f"❌ output GFX not size-neutral: {len(newgfx)} != {len(gfx)}")

    # حدّث طول الـ GFX داخلياً | update internal GFX length
    newgfx = newgfx[:4] + struct.pack("<I", len(newgfx)) + newgfx[8:]
    full = bytearray(d[:84])
    struct.pack_into("<I", full, 0x18, len(newgfx))
    struct.pack_into("<I", full, 0x50, len(newgfx))
    full += newgfx + d[84 + gfxsz:]
    if len(full) != len(d):
        raise SystemExit(f"❌ output GFXF not size-neutral: {len(full)} != {len(d)}")
    open(args.out, "wb").write(full)
    print(f"\n✅ wrote {args.out} ({len(full):,} B) — size-neutral")

if __name__ == "__main__":
    main()