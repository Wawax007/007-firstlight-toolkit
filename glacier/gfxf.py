"""
gfxf.py — بناء وحقن خطوط GFXF (Scaleform GFX)
gfxf.py — Build & inject GFXF (Scaleform GFX) fonts

تخطيط GFXF | GFXF layout:
  84-byte container header
  GFX size field @ 0x18 (and a duplicate @ 0x50)
  GFX stream @ 84
    SWF tags: ExporterInfo, FileAttr, SetBg, SceneFrame,
              DefineFont3 (×N), DoABC, ExportAssets, ShowFrame, End

تخطيط DefineFont3 body | DefineFont3 body layout:
  u16 fontID
  u8  flags
  u8  langCode
  u8  nameLen
  nameLen bytes name
  u16 numGlyphs (ng)
  (ng+1) × u32 OffsetTable
  shape data (per glyph)
  ng × u16 CodeTable
  s16 ascent
  s16 descent
  s16 leading
  ng × s16 advanceTable
  bounds blob
  u16 kerningCount (always 0 in our targets)

  CRITICAL: tag body length must be byte-for-byte identical to the original,
  otherwise downstream tags (DoABC) layout breaks and the game crashes.
"""
import struct
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen


# ============================================================
# BitWriter
# ============================================================
class BitWriter:
    """كاتب بت-بايت لـ SHAPE records | bit-level writer for SWF SHAPE records."""
    def __init__(self):
        self.acc = 0; self.n = 0; self.buf = bytearray()

    def bit(self, x):
        self.acc = (self.acc << 1) | (x & 1); self.n += 1
        if self.n == 8:
            self.buf.append(self.acc); self.acc = 0; self.n = 0

    def ub(self, v, n):
        for i in range(n - 1, -1, -1):
            self.bit((v >> i) & 1)

    def sb(self, v, n):
        if n == 0:
            return
        if v < 0:
            v = (1 << n) + v
        self.ub(v, n)

    def out(self):
        if self.n:
            self.buf.append(self.acc << (8 - self.n))
            self.acc = 0; self.n = 0
        return bytes(self.buf)


def _nb_signed(v):
    """عدد البتات المطلوبة لقيمة signed | bits needed for signed value."""
    return 0 if v == 0 else abs(int(v)).bit_length() + 1


class _Collect(BasePen):
    """يجمع contours من glyph | collects contours from a TTF glyph."""
    def __init__(self, gs):
        super().__init__(gs); self.cs = []; self.cur = None

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
# Build SHAPE record
# ============================================================
def _emit_straight(w, dx, dy):
    nb = max(_nb_signed(dx), _nb_signed(dy), 2)
    w.bit(1); w.bit(1); w.ub(nb - 2, 4)
    if dx != 0 and dy != 0:
        w.bit(1); w.sb(dx, nb); w.sb(dy, nb)
    elif dx != 0:
        w.bit(0); w.bit(0); w.sb(dx, nb)
    else:
        w.bit(0); w.bit(1); w.sb(dy, nb)


def _emit_curve(w, a, b, c, d):
    nb = max(_nb_signed(a), _nb_signed(b), _nb_signed(c), _nb_signed(d), 2)
    w.bit(1); w.bit(0); w.ub(nb - 2, 4)
    w.sb(a, nb); w.sb(b, nb); w.sb(c, nb); w.sb(d, nb)


def build_shape(contours, scale, flip_y=True):
    """يبني SHAPE record من contours TTF | build SHAPE record from TTF contours."""
    w = BitWriter(); w.ub(1, 4); w.ub(0, 4)  # NFB=1, NLB=0
    SX = lambda v: int(round(v * scale))
    SY = lambda v: int(round((-v if flip_y else v) * scale))
    first = True
    for ct in contours:
        m = ct[0]; x, y = SX(m[1][0]), SY(m[1][1])
        # StyleChange: MoveTo + FillStyle0 on first contour
        w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(1 if first else 0); w.bit(1)
        mb = max(_nb_signed(x), _nb_signed(y), 1)
        w.ub(mb, 5); w.sb(x, mb); w.sb(y, mb)
        if first:
            w.ub(1, 1); first = False
        cx, cy = x, y
        for seg in ct[1:]:
            if seg[0] == "l":
                nx, ny = SX(seg[1][0]), SY(seg[1][1])
                _emit_straight(w, nx - cx, ny - cy)
                cx, cy = nx, ny
            elif seg[0] == "q":
                ctrl, end = seg[1], seg[2]
                ccx, ccy = SX(ctrl[0]), SY(ctrl[1])
                ex, ey = SX(end[0]), SY(end[1])
                _emit_curve(w, ccx - cx, ccy - cy, ex - ccx, ey - ccy)
                cx, cy = ex, ey
    # End record
    w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(0); w.bit(0)
    return w.out()


def empty_shape():
    """شكل فارغ لإفراغ glyphs غير مستخدمة. | Empty shape for blanking unused glyphs."""
    w = BitWriter(); w.ub(1, 4); w.ub(0, 4)
    for _ in range(6):
        w.bit(0)
    return w.out()


# ============================================================
# قراءة tag من GFX stream | Read a SWF tag
# ============================================================
def read_tag(buf, p):
    rec = struct.unpack_from("<H", buf, p)[0]
    code = rec >> 6; ln = rec & 0x3F; q = p + 2
    if ln == 0x3F:
        ln = struct.unpack_from("<I", buf, q)[0]; q += 4
    return code, ln, q


# ============================================================
# إعادة بناء DefineFont3 | Rebuild a DefineFont3 tag body
# ============================================================
def rebuild_font_body(body, font_id, codepoints, shapes_by_cp, advs_by_cp, ES):
    """يستبدل خانات Latin غير ASCII بـ glyphs جديدة (حياد الحجم).
       Replace non-ASCII slots with new glyphs, byte-size-neutral.

       body         = bytes of one DefineFont3 tag body
       font_id      = font id (for error messages)
       codepoints   = list of new codepoints to inject (sorted)
       shapes_by_cp = {cp: shape_bytes} per codepoint
       advs_by_cp   = {cp: s16 advance} per codepoint
       ES           = empty_shape() for blanking
       يرجع body جديد بنفس الطول. | Returns new body of identical length."""
    LN = len(body)
    flags = body[2]; lang = body[3]; nlen = body[4]; name = body[5:5 + nlen]
    p = 5 + nlen
    ng = struct.unpack_from("<H", body, p)[0]; p += 2
    ot = p
    offs = [struct.unpack_from("<I", body, ot + i * 4)[0] for i in range(ng + 1)]
    shapes = [body[ot + offs[i]:ot + offs[i + 1]] for i in range(ng)]
    cs = ot + offs[ng]
    codes = [struct.unpack_from("<H", body, cs + i * 2)[0] for i in range(ng)]
    ls = cs + ng * 2
    asc, desc, lead = struct.unpack_from("<hhh", body, ls)
    ads = ls + 6
    advs = [struct.unpack_from("<h", body, ads + i * 2)[0] for i in range(ng)]
    bnds = ads + ng * 2
    bounds_blob = body[bnds:LN - 2]
    kern = struct.unpack_from("<H", body, LN - 2)[0]

    codes2 = list(codes); shapes2 = list(shapes); advs2 = list(advs)
    # خانات الـ glyphs غير ASCII (codepoint >= 0x80)
    victims = sorted([i for i in range(ng) if codes[i] >= 0x80],
                     key=lambda i: codes[i], reverse=True)
    if len(victims) < len(codepoints):
        raise RuntimeError(
            f"font {font_id}: not enough victim slots "
            f"({len(victims)} < {len(codepoints)}). "
            f"Reduce the number of requested codepoints."
        )
    used = set()
    for k, cp in enumerate(codepoints):
        idx = victims[k]
        used.add(idx)
        codes2[idx] = cp
        shapes2[idx] = shapes_by_cp[cp]
        advs2[idx] = advs_by_cp[cp]

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
            if rec >= need:
                break
            rec += sz - len(ES)
            shapes2[i] = ES
            blanked += 1
        need = core_len(shapes2) - LN
        if need > 0:
            raise RuntimeError(
                f"font {font_id}: cannot fit even after blanking {blanked} glyphs "
                f"(still need {need} B)"
            )

    # رتّب تصاعدياً | sort ascending by codepoint
    trip = sorted(zip(codes2, shapes2, advs2), key=lambda x: x[0])
    c3 = [t[0] for t in trip]
    s3 = [t[1] for t in trip]
    a3 = [t[2] for t in trip]

    head = bytearray()
    head += struct.pack("<H", font_id)
    head.append(flags); head.append(lang); head.append(nlen); head += name
    head += struct.pack("<H", ng)
    o2 = [(ng + 1) * 4]
    for s in s3:
        o2.append(o2[-1] + len(s))

    new_body = (bytes(head)
                + b"".join(struct.pack("<I", o) for o in o2)
                + b"".join(s3)
                + b"".join(struct.pack("<H", c) for c in c3)
                + struct.pack("<hhh", asc, desc, lead)
                + b"".join(struct.pack("<h", x) for x in a3)
                + bounds_blob
                + struct.pack("<H", kern))

    pad = LN - len(new_body)
    new_body += b"\x00" * pad
    if len(new_body) != LN:
        raise RuntimeError(f"font {font_id}: size mismatch {len(new_body)} != {LN}")
    return new_body, blanked, pad


# ============================================================
# الواجهة عالية المستوى | High-level builder
# ============================================================
def build(src_gfxf_bytes, config, verbose=False):
    """يبني GFXF جديد من إعداد JSON.
       Build a new GFXF from JSON config.

       config dict keys:
         scale_em, scale_size, ttf_upm  -> scale = (scale_em*scale_size)/ttf_upm
         flip_y      bool
         weights     {font_id: ttf_path}
         codepoints  {ranges: [[start,end],...], extras: [...]}

       يرجع GFXF bytes جديد بنفس حجم المصدر.
       Returns new GFXF bytes, same size as source."""
    scale = (config["scale_em"] * config["scale_size"]) / config["ttf_upm"]
    flip_y = config.get("flip_y", True)
    weights = {int(k): v for k, v in config["weights"].items()}

    # codepoints المطلوبة
    cps = set()
    for rng in config["codepoints"].get("ranges", []):
        for c in range(rng[0], rng[1]):
            cps.add(c)
    for c in config["codepoints"].get("extras", []):
        cps.add(c)

    if verbose:
        print(f"📐 scale = {scale}  flip_y = {flip_y}")
        print(f"🎯 requested codepoints: {len(cps)}")

    # حضّر shapes + advances لكل وزن | per-weight prep
    ES = empty_shape()
    shapes_by_fid = {}
    advs_by_fid = {}
    available_cps = None

    for fid, ttf_path in weights.items():
        tt = TTFont(ttf_path)
        gs = tt.getGlyphSet()
        cmap = tt.getBestCmap()
        hm = tt["hmtx"]
        avail = sorted(cp for cp in cps if cp in cmap)
        if available_cps is None:
            available_cps = set(avail)
        else:
            available_cps &= set(avail)
        sh = {}
        ad = {}
        for cp in avail:
            gn = cmap[cp]
            pen = _Collect(gs)
            gs[gn].draw(pen)
            sh[cp] = build_shape(pen.done(), scale, flip_y)
            ad[cp] = max(-32768, min(32767, int(round(hm[gn][0] * scale))))
        shapes_by_fid[fid] = sh
        advs_by_fid[fid] = ad
        if verbose:
            import os
            print(f"   font {fid} ({os.path.basename(ttf_path)}): "
                  f"{len(avail)} glyphs prepared")

    final_cps = sorted(available_cps) if available_cps else []
    if verbose:
        print(f"✅ intersection across all weights: {len(final_cps)} codepoints")

    # اقرأ GFXF المصدر | read source GFXF
    d = src_gfxf_bytes
    gfxsz = struct.unpack_from("<I", d, 0x18)[0]
    gfx = d[84:84 + gfxsz]

    # امش على tags | walk SWF tags
    out = bytearray(gfx[:21])
    p = 21
    while p < len(gfx):
        code, ln, q = read_tag(gfx, p)
        body = gfx[q:q + ln]
        if code == 75:  # DefineFont3
            fid = struct.unpack_from("<H", body, 0)[0]
            if fid in weights:
                body, blanked, pad = rebuild_font_body(
                    body, fid, final_cps,
                    shapes_by_fid[fid], advs_by_fid[fid], ES
                )
                if verbose:
                    print(f"  font {fid}: +{len(final_cps)} glyphs, "
                          f"blanked {blanked}, pad {pad}, len {ln} ✅")
        out += gfx[p:q] + body
        if code == 0 and ln == 0:
            break
        p = q + ln

    new_gfx = bytes(out)
    if len(new_gfx) != len(gfx):
        raise RuntimeError(f"GFX not size-neutral: {len(new_gfx)} != {len(gfx)}")

    # حدّث طول GFX داخلياً | update internal GFX length
    new_gfx = new_gfx[:4] + struct.pack("<I", len(new_gfx)) + new_gfx[8:]
    full = bytearray(d[:84])
    struct.pack_into("<I", full, 0x18, len(new_gfx))
    struct.pack_into("<I", full, 0x50, len(new_gfx))
    full += new_gfx + d[84 + gfxsz:]
    if len(full) != len(d):
        raise RuntimeError(f"GFXF not size-neutral: {len(full)} != {len(d)}")
    return bytes(full)
