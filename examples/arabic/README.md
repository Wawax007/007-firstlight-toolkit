# مثال: تعريب 007 First Light كاملاً
# Example: Full Arabic translation of 007 First Light

## 🇸🇦 بالعربي

هذا مثال جاهز لتعريب اللعبة كاملاً: خط + واجهة + حوار + أسماء المتحدّثين.

### الخطوات

#### 1. حمّل خطوط Noto Kufi Arabic

- افتح: https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic
- اضغط **Download family**
- فك الـ ZIP وحط المجلد `static/` داخل هذا المجلد باسم `fonts/`
- أو عدّل المسارات في `font_config.json` لتشير لمكان خطوطك

التركيب المتوقّع | Expected layout:
```
examples/arabic/
├── font_config.json
├── translation_config.json
├── fonts/
│   ├── NotoKufiArabic-Bold.ttf
│   ├── NotoKufiArabic-Regular.ttf
│   ├── NotoKufiArabic-SemiBold.ttf
│   └── NotoKufiArabic-Medium.ttf
└── translations/
    ├── ui.json
    ├── dialogue.json
    └── speakers.json
```

#### 2. حضّر ملفات الترجمة

استخرج النصوص من اللعبة:

```powershell
python tools/extract_text.py --game-dir "D:/SteamLibrary/steamapps/common/007 First Light" --out examples/arabic/translations/
```

هذا يولّد 3 ملفات بالإنجليزي:
- `ui.json` — نصوص الواجهة
- `dialogue.json` — نصوص الحوار
- `speakers.json` — أسماء المتحدّثين

افتحها وترجم القيم. اترك المفاتيح كما هي.

#### 3. ركّب التعريب

```powershell
python tools/install_translation.py --config examples/arabic/translation_config.json
```

السكربت بيكتشف اللعبة، ياخذ نسخة احتياطية، ويركّب كل شي.

#### 4. شغّل اللعبة

#### للاسترجاع

```powershell
python tools/install_translation.py --restore
```

### ملاحظات تقنية مهمّة

- **Reshaping**: السكربت يطبّق `arabic_reshaper` + `python-bidi` تلقائياً على كل نص عربي لأن Scaleform/GFX ما يدعم RTL أو reshaping.
- **الخط**: يحقن 155 شكل عرض عربي (`U+FE70`–`U+FEFF`) + أرقام `٠–٩` + علامات `،` `؛` `؟` + ligature `ﷲ`.
- **أسماء المتحدّثين**: تنحقن بـ byte-level surgery (استبدال الحقل الأول فقط في DLGE base block، النص المنطوق ما يتأثّر).

---

## 🇬🇧 English

A ready-made example for fully localizing the game into Arabic: font + UI + dialogue + speaker names.

### Steps

#### 1. Download Noto Kufi Arabic

From https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic. Place the `static/` folder here as `fonts/`, or edit the paths in `font_config.json`.

#### 2. Prepare translation files

```powershell
python tools/extract_text.py --game-dir "D:/SteamLibrary/steamapps/common/007 First Light" --out examples/arabic/translations/
```

This generates `ui.json`, `dialogue.json`, and `speakers.json` (in English). Translate the values, keep the keys.

#### 3. Install

```powershell
python tools/install_translation.py --config examples/arabic/translation_config.json
```

#### 4. Restore

```powershell
python tools/install_translation.py --restore
```

### Technical notes

- **Reshaping**: The script automatically applies `arabic_reshaper` + `python-bidi` to every Arabic string because Scaleform/GFX does not support RTL or shaping natively.
- **Font**: Injects 155 Arabic Presentation Forms-B glyphs (`U+FE70`–`U+FEFF`) + Arabic-Indic digits `٠–٩` + punctuation `،` `؛` `؟` + `ﷲ` ligature.
- **Speaker names**: Injected via byte-level surgery (replacing only field 1 of DLGE base block; spoken text is untouched).
