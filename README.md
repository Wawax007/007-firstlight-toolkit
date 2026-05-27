# 007 First Light — Toolkit
# مجموعة أدوات لتعريب 007 First Light

> أدوات شاملة لتعديل لعبة 007 First Light (IO Interactive, 2025): استخراج النصوص، تركيب الخطوط، حقن الترجمات.
> A complete toolkit for modding 007 First Light (IO Interactive, 2025): text extraction, font installation, and translation injection.

نشأ هذا المشروع من جهد تعريب اللعبة عام 2026 — أول تعريب كامل للعبة. الأدوات معمّمة بحيث تخدم أي لغة، مو بس العربي.

Born from the 2026 Arabic localization effort — the first complete translation of the game. Tools are generalized to serve any language, not just Arabic.

---

## 🇸🇦 بالعربي

### إيش هذا الـ Toolkit؟

طقم أدوات بـ Python لتعديل لعبة 007 First Light (محرّك Glacier، صيغة RPKG v2). يقدر:

- 📖 **يستخرج كل النصوص** من اللعبة (الواجهة + الحوار + أسماء المتحدّثين) كملفات JSON قابلة للتحرير.
- 🔤 **يركّب أي خط** (TTF) في اللعبة مع الحفاظ على استقرار الـ engine.
- 💉 **يحقن ترجمات كاملة** في اللعبة بأمر واحد (واجهة + حوار + أسماء + خط).
- 🔄 **يرجّع كل شي للأصل** بأمر واحد.

### إيش تحتاج؟

- ويندوز (يشتغل على لينكس كمان)
- [Python 3.10+](https://www.python.org/downloads/)
- لعبة 007 First Light مثبّتة (Steam)

### التثبيت السريع

```powershell
git clone https://github.com/7akeem0/007-firstlight-toolkit.git
cd 007-firstlight-toolkit
pip install -r requirements.txt
```

### الاستخدامات الثلاثة الرئيسية

#### 1. تعريب اللعبة كاملاً (المثال العربي)

```powershell
# استخرج كل النصوص من اللعبة
python tools/extract_text.py --game-dir "D:/SteamLibrary/steamapps/common/007 First Light" --out my_translation/

# ترجم القيم في my_translation/ui.json, dialogue.json, speakers.json

# نزّل خطوط Noto Kufi Arabic من قوقل وحطّها في examples/arabic/fonts/

# ركّب كل شي بأمر واحد
python tools/install_translation.py --config examples/arabic/translation_config.json
```

#### 2. تركيب خط فقط (بدون ترجمة)

لو بس تبي تغيّر شكل الحروف:

```powershell
python tools/install_font.py --config examples/arabic/font_config.json
```

#### 3. استكشاف ملفات اللعبة

```powershell
# قائمة بكل الموارد في chunk0
python tools/list_resources.py "D:/.../Runtime/chunk0.rpkg"

# فقط الخطوط (GFXF)
python tools/list_resources.py chunk0.rpkg --type GFXF

# استخرج خط معيّن
python tools/extract_font.py chunk0.rpkg 01DD9580958CDC9B my_font.GFXF
```

### الاسترجاع

```powershell
python tools/install_translation.py --restore
# أو
python tools/install_font.py --restore
```

### اللغات المدعومة

| اللغة | reshaping/bidi | ملاحظات |
|---|:---:|---|
| العربي | ✅ تلقائي | تستخدم Arabic Presentation Forms-B |
| الفارسي | ✅ تلقائي | يضيف چ پ ژ گ |
| الأردو | ✅ تلقائي | يحتاج Noto Nastaliq Urdu |
| التركي/الفرنسي/الإسباني/إلخ | ❌ مو محتاج | لاتيني مع علامات |
| الروسي/البلغاري/إلخ | ❌ مو محتاج | سيريلي |

### الهيكل

```
007-firstlight-toolkit/
├── glacier/                 # المكتبة الأساسية (modular)
│   ├── rpkg.py              # قراءة/كتابة RPKG + XTEA + XOR
│   ├── locr.py              # نصوص الواجهة
│   ├── dlge.py              # نصوص الحوار + أسماء المتحدّثين
│   ├── gfxf.py              # بناء الخطوط
│   ├── shaping.py           # reshaping للعربي والفارسي
│   └── steam.py             # اكتشاف مسار اللعبة
├── tools/                   # سكربتات CLI
│   ├── list_resources.py    # استعراض الموارد
│   ├── extract_text.py      # استخراج كل النصوص
│   ├── extract_font.py      # استخراج خط
│   ├── install_font.py      # تركيب خط (all-in-one)
│   └── install_translation.py  # تركيب ترجمة كاملة (all-in-one)
├── examples/
│   └── arabic/              # مثال عربي كامل وجاهز
├── docs/
│   ├── RPKG_FORMAT.md       # توثيق صيغة الـ chunks
│   ├── FONT_INJECTION.md    # شرح حقن الخط
│   └── TRANSLATION_WORKFLOW.md  # سير عمل الترجمة
└── README.md
```

### الكريدت

- **تعريب اللعبة + هندسة الـ engine عكسياً (2026):** هشام ([@7akeem0](https://github.com/7akeem0))
- **الأدوات (هذا الريبو):** مفتوحة المصدر (MIT). استخدمها كيف ما تبي.

---

## 🇬🇧 English

### What is this toolkit?

A Python toolkit for modding 007 First Light (Glacier engine, RPKG v2). It can:

- 📖 **Extract all text** from the game (UI + dialogue + speaker names) as editable JSON.
- 🔤 **Install any font** (TTF) into the game while keeping the engine stable.
- 💉 **Inject full translations** in one command (UI + dialogue + names + font).
- 🔄 **Restore everything** in one command.

### Requirements

- Windows (also works on Linux)
- [Python 3.10+](https://www.python.org/downloads/)
- 007 First Light installed (Steam)

### Install

```powershell
git clone https://github.com/7akeem0/007-firstlight-toolkit.git
cd 007-firstlight-toolkit
pip install -r requirements.txt
```

### Main use cases

#### 1. Full game translation (Arabic example)

```powershell
# Extract all text from the game
python tools/extract_text.py --game-dir "D:/.../007 First Light" --out my_translation/

# Translate the values in my_translation/ui.json, dialogue.json, speakers.json

# Download Noto Kufi Arabic from Google Fonts → put it in examples/arabic/fonts/

# Install everything in one command
python tools/install_translation.py --config examples/arabic/translation_config.json
```

#### 2. Font only (no translation)

```powershell
python tools/install_font.py --config examples/arabic/font_config.json
```

#### 3. Explore game files

```powershell
python tools/list_resources.py chunk0.rpkg
python tools/list_resources.py chunk0.rpkg --type GFXF
python tools/extract_font.py chunk0.rpkg 01DD9580958CDC9B my_font.GFXF
```

### Restore

```powershell
python tools/install_translation.py --restore
# or
python tools/install_font.py --restore
```

### Supported languages

| Language | reshaping/bidi | Notes |
|---|:---:|---|
| Arabic | ✅ auto | Uses Arabic Presentation Forms-B |
| Persian | ✅ auto | Adds چ پ ژ گ |
| Urdu | ✅ auto | Needs Noto Nastaliq Urdu |
| Turkish/French/Spanish/etc. | ❌ N/A | Latin with diacritics |
| Russian/Bulgarian/etc. | ❌ N/A | Cyrillic |

### Architecture

`glacier/` is a clean Python package — use it as a library. `tools/` are CLI scripts that wrap it. See `docs/` for the technical deep-dive.

### Credits

- **Game translation + engine reverse engineering (2026):** Hesham ([@7akeem0](https://github.com/7akeem0))
- **Toolkit (this repo):** MIT — use it however you want.

### Disclaimer

This toolkit does not contain or distribute any game assets. You must own a legal copy of 007 First Light. The toolkit does not modify the game executable, only the data archives, and includes a restore command.
