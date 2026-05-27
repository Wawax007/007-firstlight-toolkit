# مثال: تركيب الخط العربي
# Example: Installing an Arabic font

## 🇸🇦 بالعربي

هذا مثال جاهز لتركيب خط [Noto Kufi Arabic](https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic) من قوقل على لعبة 007 First Light.

### الخطوات

1. **نزّل خطوط Noto Kufi Arabic** من قوقل:
   - افتح: https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic
   - اضغط على **Download family**
   - فك ضغط الـ ZIP
   - راح تلقى مجلد `static/` فيه ملفات `.ttf` (Bold, Regular, SemiBold, Medium, إلخ)

2. **عدّل المسارات في `font_config.json`**:

   افتح الملف وغيّر مسارات الـ TTF لتشير إلى المكان اللي حطّيت فيه الخطوط. مثال:

   ```json
   "weights": {
     "1": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-Bold.ttf",
     "2": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-Regular.ttf",
     "3": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-Bold.ttf",
     "4": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-Regular.ttf",
     "5": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-SemiBold.ttf",
     "6": "C:/Users/YourName/Downloads/Noto_Kufi_Arabic/static/NotoKufiArabic-Medium.ttf"
   }
   ```

3. **شغّل السكربت**:

   من جذر المشروع:

   ```powershell
   python scripts/install_font.py --config examples/arabic/font_config.json
   ```

### إيش يسوّيه هذا الإعداد؟

- يحقن **155 شكل عرض عربي** (Arabic Presentation Forms-B من `U+FE70` إلى `U+FEFF`).
- يضيف **الأرقام العربية-الهندية** (`٠–٩`).
- يضيف **علامات الترقيم العربية**: `،` `؛` `؟` و ligature `ﷲ`.
- يضيف الخط في كل أوزان عائلة Rajdhani (1, 4, 5, 6) وخطوط العناوين (2, 3).

### ملاحظة مهمة عن العربي

اللعبة تستخدم Scaleform/GFX، اللي ما يدعم RTL أو reshaping تلقائياً. عشان يطلع العربي صح في اللعبة، لازم النص نفسه يتم:

1. **إعادة تشكيله** بـ `arabic_reshaper` (يحوّل الحروف لشكل العرض المناسب: مفصول، أول، وسط، نهاية).
2. **عكسه** بـ `python-bidi`'s `get_display` (للترتيب البصري RTL).

الأداة هذي تركّب **الخط فقط** — مو الترجمة. لو تبي تترجم اللعبة كاملة، هذا مشروع منفصل.

---

## 🇬🇧 English

A ready-made example for installing [Noto Kufi Arabic](https://fonts.google.com/noto/specimen/Noto+Kufi+Arabic) into 007 First Light.

### Steps

1. **Download Noto Kufi Arabic** from Google Fonts → unzip → find the `static/` folder with the `.ttf` files.

2. **Edit `font_config.json`** to point to your TTF paths.

3. **Run** from the project root:

   ```powershell
   python scripts/install_font.py --config examples/arabic/font_config.json
   ```

### What this preset does

- Injects **155 Arabic Presentation Forms-B glyphs** (`U+FE70`–`U+FEFF`).
- Adds **Arabic-Indic digits** (`٠–٩`).
- Adds **Arabic punctuation**: `،` `؛` `؟` and the `ﷲ` ligature.
- Covers all four Rajdhani weights (1, 4, 5, 6) plus the title fonts (2, 3).

### Important note about Arabic

The game uses Scaleform/GFX which does **not** auto-shape or auto-RTL. For Arabic to render correctly in-game, the *text itself* must be:

1. **Reshaped** with `arabic_reshaper` (maps base letters to their presentation forms).
2. **Bidi-reversed** with `python-bidi`'s `get_display` (to visual RTL order).

This tool only installs the **font** — not the translation. Full game localization is a separate project.
