# حقن الخط | Font Injection

## 🇸🇦 بالعربي

### الفكرة

اللعبة تستخدم محرّك Scaleform/GFX للواجهة، والخطوط مخزّنة كـ `DefineFont3` tags داخل GFX containers. هذي الـ containers مغلّفة بـ GFXF resource داخل chunk0.

### المسار

```
TTF file ──[fonttools]──▶ contours
   │
   ▼
contours ──[bit-writer]──▶ SHAPE record (SWF format)
   │
   ▼
استبدال خانات Latin غير ASCII في DefineFont3 بـ glyphs الجديدة
   │
   ▼
حشو الـ body بـ \x00 ليصير = الطول الأصلي بالضبط
   │
   ▼
LZ4 hc=12 ──▶ XOR scramble ──▶ EOF-append + table patch
```

### حياد الحجم: لماذا؟

اللعبة بتقرأ tags بعد الـ DefineFont3 (مثل DoABC اللي فيه ActionScript)، وعناوينها مبنية على إزاحات ثابتة من بداية الملف. أي زيادة أو نقصان في حجم body الـ DefineFont3 يحرّك كل شي بعده ويكسر الـ engine.

الحل: نستبدل خانات الـ glyphs **بنفس العدد**، نزبّط الفروقات بإفراغ خانات إضافية أو حشو بـ `\x00`.

### Y-axis flip

- TTF: محور Y يصعد (Y-up)
- SWF/Scaleform: محور Y ينزل (Y-down)
- بدون عكس Y تطلع الحروف مقلوبة

### السكيل

```
scale = (scale_em × scale_size) / ttf_upm
```

لـ 007 First Light: `(1024 × 20) / 1000 = 20.48`.

### اختيار الـ font_id

الخط الإنجليزي في 007 (`fonts_en`) يحوي 9 خطوط:

| ID | الاسم الأصلي | الاستخدام |
|----|-------------|-----------|
| 1 | Rajdhani Bold | عناوين عريضة (`$bold` في SWF) |
| 2 | Noto Sans KNT Global | خط عناوين كبير |
| 3 | Arya Regular | عناوين |
| 4 | Rajdhani Regular | نص عادي (`$normal`) |
| 5 | Rajdhani SemiBold | شبه عريض |
| 6 | Rajdhani Medium | متوسط (`$medium`) |
| 7-9 | Kimono | أيقونات (تخطّاها — 43 glyph فقط) |

لـ تغطية كاملة: اطلب 1, 2, 3, 4, 5, 6.

### اختيار الـ codepoints

عدد الـ glyphs اللي تقدر تحقنها محدود بعدد خانات الـ Latin غير ASCII في الخط (~247 خانة لكل Rajdhani).

**نطاق العربي الموصى به:**
- `U+FE70`–`U+FEFF` = Arabic Presentation Forms-B (~144 codepoint)
- + `U+0660`–`U+0669` (الأرقام `٠–٩`)
- + علامات الترقيم `U+060C ، U+061B ; U+061F ?`
- + `U+FDF2 ﷲ`

المجموع ≈ 158، مناسب جداً.

**ليش Presentation Forms مو الحروف العادية؟** لأن `arabic_reshaper` يحوّل النص لأشكال FE70–FEFF (الأشكال الموصولة). لو حقنت U+0628 (ب) بدل U+FE91 (ﺑ — ب في وضع البداية)، الـ engine ما يلقى الـ glyph الصحيح.

---

## 🇬🇧 English

### Concept

The game uses Scaleform/GFX for its UI, with fonts stored as `DefineFont3` tags inside GFX containers, which are wrapped in GFXF resources inside chunk0.

### Pipeline

```
TTF ──[fonttools]──▶ contours
  │
  ▼
contours ──[bit-writer]──▶ SHAPE record (SWF format)
  │
  ▼
Replace non-ASCII Latin slots in DefineFont3 with new glyphs
  │
  ▼
Pad body with \x00 to exact original length
  │
  ▼
LZ4 hc=12 → XOR scramble → EOF-append + table patch
```

### Why size-neutral?

The engine reads subsequent tags (like DoABC containing ActionScript) by fixed file offsets. Any size drift in the DefineFont3 body shifts everything after it and crashes the engine.

Solution: replace glyph slots **in-place**, absorb size growth by blanking extra slots, pad to original length with `\x00`.

### Y-axis flip

- TTF: Y-up
- SWF/Scaleform: Y-down

Without flipping, glyphs render upside down.

### Scale

```
scale = (scale_em × scale_size) / ttf_upm
```

For 007 First Light: `(1024 × 20) / 1000 = 20.48`.

### Choosing font_id

The English font resource (`fonts_en`) in 007 contains 9 DefineFont3 tags:

| ID | Original | Used for |
|----|----------|----------|
| 1 | Rajdhani Bold | Headings (`$bold` SWF alias) |
| 2 | Noto Sans KNT Global | Large title font |
| 3 | Arya Regular | Titles |
| 4 | Rajdhani Regular | Body (`$normal`) |
| 5 | Rajdhani SemiBold | Semi-bold |
| 6 | Rajdhani Medium | Medium (`$medium`) |
| 7-9 | Kimono | Icon glyphs (skip — only 43 glyphs) |

For full coverage, target 1, 2, 3, 4, 5, 6.

### Choosing codepoints

The number of glyphs you can inject is limited by the non-ASCII Latin slots available (~247 in each Rajdhani font).

**For Arabic**, the recommended set:
- `U+FE70`–`U+FEFF` = Arabic Presentation Forms-B (~144 codepoints)
- + `U+0660`–`U+0669` (digits)
- + punctuation `U+060C ، U+061B ; U+061F ?`
- + `U+FDF2 ﷲ`

Total ≈ 158, well within budget.

**Why presentation forms instead of base letters?** Because `arabic_reshaper` outputs FE70–FEFF (the connected/positional forms). If you inject U+0628 (ب base) instead of U+FE91 (ﺑ initial), the engine won't find the right glyph.

### For other scripts

- **Persian/Urdu**: same as Arabic, plus extras (`U+0686 چ`, `U+0698 ژ`, `U+06AF گ`, `U+067E پ` and their presentation forms `U+FB57`–`U+FB6B`, `U+FB7A`–`U+FB94`, ...).
- **Turkish**: extended Latin — just add `ç ş ğ İ ı Ö ö Ü ü` (no shaping needed).
- **Cyrillic**: `U+0400`–`U+04FF`.

Check each codepoint exists in your chosen TTF before injection — `build_font.py` will warn if not.
