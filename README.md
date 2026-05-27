# 007 First Light — Font Installer
# مثبّت الخطوط للعبة 007 First Light

> أداة لتركيب **أي خط** على لعبة 007 First Light (Glacier engine, RPKG v2).
> A tool to install **any custom font** into 007 First Light (Glacier engine, RPKG v2).

---

## 🇸🇦 بالعربي

### إيش هذي الأداة؟

سكربت بسيط يستبدل خط اللعبة الأصلي بأي خط `.ttf` تختاره — سواء كنت تبي تعرّب اللعبة، تركّب خط فارسي، تركي، أردو، أو حتى خط مزخرف لسوالف.

تشتغل بطريقة **حياد الحجم بالبايت**: ما تكبّر الـ chunk، ما تحرّك الموارد، ما تكسر شي.

### إيش تحتاج؟

- ويندوز (تنفع على لينكس كمان للي يبي)
- [Python 3.10+](https://www.python.org/downloads/)
- لعبة 007 First Light مثبّتة (Steam)
- ملف `.ttf` للخط اللي تبي تركّبه

### التثبيت

```powershell
git clone https://github.com/7akeem0/007-firstlight-font-installer.git
cd 007-firstlight-font-installer
pip install -r requirements.txt
```

### الاستخدام السريع (مثال عربي جاهز)

نزّل خطوط [Noto Kufi Arabic](https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic) من قوقل، حطّها في مجلد، عدّل المسارات في `examples/arabic/font_config.json`، ثم:

```powershell
python scripts/install_font.py --config examples/arabic/font_config.json
```

السكربت بيكتشف اللعبة تلقائياً، ياخذ نسخة احتياطية، ويركّب الخط.

### للرجوع للخط الأصلي

```powershell
python scripts/install_font.py --restore
```

### إعداد خطّك الخاص

سوّ ملف `my_font.json`:

```json
{
  "scale_em": 1024,
  "scale_size": 20,
  "ttf_upm": 1000,
  "flip_y": true,
  "weights": {
    "1": "C:/path/to/MyFont-Bold.ttf",
    "4": "C:/path/to/MyFont-Regular.ttf",
    "5": "C:/path/to/MyFont-SemiBold.ttf",
    "6": "C:/path/to/MyFont-Medium.ttf"
  },
  "codepoints": {
    "ranges": [[65136, 65280]],
    "extras": [1548, 1567, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641]
  }
}
```

- **`weights`**: المفتاح = `font_id` داخل GFXF، القيمة = مسار TTF. لعائلة Rajdhani في 007: `1=Bold, 4=Regular, 5=SemiBold, 6=Medium`. خطوط العناوين تستخدم `2` و `3` أيضاً.
- **`codepoints`**: قائمة الـ Unicode codepoints اللي تبيها من خطّك. `ranges` نطاقات `[start, end]` (start شامل، end غير شامل)، و `extras` codepoints فردية.
- **`ttf_upm`**: قيمة `unitsPerEm` في خطّك. افتراضي 1000 لمعظم الخطوط الحديثة.
- **`flip_y`**: خلّيها `true` للعبة 007 (Glacier/Scaleform).

شغّل:

```powershell
python scripts/install_font.py --config my_font.json
```

### أدوات إضافية

```powershell
# استعرض كل الموارد في chunk
python scripts/list_resources.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime/chunk0.rpkg"

# تصفية بالنوع
python scripts/list_resources.py chunk0.rpkg --type GFXF

# استخراج الخط الأصلي فقط (بدون حقن)
python scripts/extract_font.py chunk0.rpkg 01DD9580958CDC9B original_font.GFXF
```

### كيف تشتغل؟ (لمن يبي يفهم)

1. **استخراج**: نقرأ مورد الخط `01DD9580958CDC9B` (type=GFXF) من `chunk0.rpkg`. هذا ملف GFX (Scaleform) داخله 9 خطوط `DefineFont3`.
2. **بناء**: نأخذ كل DefineFont3 (للأوزان المستهدفة: 1, 2, 3, 4, 5, 6)، نختار خانات الـ glyphs غير ASCII (codepoint ≥ 0x80)، ونستبدلها بـ glyphs من الـ TTF حقّك.
3. **حياد الحجم**: نُفرّغ كم خانة إضافية لتعويض البايتات الزائدة، ثم نُكمل بـ `\x00` لحد ما يصير طول الـ tag = الأصل بالضبط. هذا مهم — أي تغيير في الحجم يكسر اللعبة.
4. **حقن**: نضغط الـ GFXF الجديد بـ LZ4 hc=12، نشفّره بـ XOR (مفتاح ثابت في الـ engine)، نلصقه في نهاية الـ chunk، ونعدّل الجدولين (table1 الـ offset والـ size، table2 الـ decompressed size).
5. **إعادة التحميل**: نضبط `mtime=2020` على الـ chunk عشان اللعبة تعيد تحميله من القرص.

### الكريدت

تعريب اللعبة وفك تشفير الـ engine: **هشام** ([@7akeem0](https://github.com/7akeem0)). الأداة مفتوحة المصدر، استخدمها كيف ما تبي.

---

## 🇬🇧 English

### What is this?

A script that swaps the game's original font with any `.ttf` you choose — whether you're localizing the game to Arabic, Persian, Turkish, Urdu, or just want a decorative font for fun.

It works in a **byte-size-neutral** way: it does not grow the chunk, move resources, or break anything.

### Requirements

- Windows (also works on Linux)
- [Python 3.10+](https://www.python.org/downloads/)
- 007 First Light installed (Steam)
- A `.ttf` font file

### Install

```powershell
git clone https://github.com/7akeem0/007-firstlight-font-installer.git
cd 007-firstlight-font-installer
pip install -r requirements.txt
```

### Quick start (Arabic preset)

Download [Noto Kufi Arabic](https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic), put it in a folder, edit the paths in `examples/arabic/font_config.json`, then:

```powershell
python scripts/install_font.py --config examples/arabic/font_config.json
```

### Restore the original font

```powershell
python scripts/install_font.py --restore
```

### Your own font

Create `my_font.json` (see the structure under the Arabic section above). The keys in `weights` are `font_id` inside the game's GFXF — for the Rajdhani family in 007: `1=Bold, 4=Regular, 5=SemiBold, 6=Medium`. Title fonts also use `2` and `3`.

```powershell
python scripts/install_font.py --config my_font.json
```

### Extra tools

```powershell
python scripts/list_resources.py chunk0.rpkg --type GFXF
python scripts/extract_font.py chunk0.rpkg 01DD9580958CDC9B original_font.GFXF
```

### How it works (technical)

1. **Extract** the font resource `01DD9580958CDC9B` (type=GFXF) from `chunk0.rpkg` — it's a Scaleform GFX file containing 9 `DefineFont3` tags.
2. **Build**: for each targeted DefineFont3, replace non-ASCII glyph slots with glyphs from your TTF.
3. **Size-neutral**: blank a few extra slots to absorb the size growth, then pad the tag body to the exact original length. Any size drift crashes the game.
4. **Inject**: LZ4-compress (hc=12), XOR-scramble (engine's fixed key), append to chunk EOF, patch table1 (offset + sizeField) and table2 (decompressed size).
5. **Reload**: set `mtime=2020` on the chunk so the engine re-reads it.

### Credit

Engine reverse-engineering & Arabic localization: **Hesham** ([@7akeem0](https://github.com/7akeem0)). Tool is open-source — use it however you want.

---

## License

MIT — see [LICENSE](LICENSE).
