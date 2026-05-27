# سير عمل الترجمة | Translation Workflow

## 🇸🇦 بالعربي

### المراحل الثلاث

```
1. الاستخراج          2. الترجمة           3. الحقن
   ──────────             ────────             ──────
   chunks → JSON   →   trans JSON     →   chunks (معدّل)
```

### 1. الاستخراج

```powershell
python tools/extract_text.py --game-dir "D:/Games/007 First Light" --out my_translation/
```

هذا يولّد 3 ملفات:

| الملف | المحتوى |
|---|---|
| `ui.json` | كل نصوص الواجهة (LOCR) — منظّمة حسب الـ resource |
| `dialogue.json` | كل نصوص الحوار (DLGE) — مع segments الزمنية ومعلومات المتحدّث |
| `speakers.json` | قائمة بكل أسماء المتحدّثين الفريدة (للترجمة) |

### 2. الترجمة

افتح ملفات JSON وترجم **القيم فقط، اترك المفاتيح**:

`ui.json` مثلاً:
```json
{
  "01179467BC0E9F2F": {
    "5E5123EA": "السلام عليكم",
    "...": "..."
  }
}
```

`speakers.json`:
```json
{
  "Bond": "بوند",
  "Pilot": "الطيار",
  "M": "إم"
}
```

`dialogue.json` (هيكل أعقد):
```json
{
  "01002E3BD8CE1EE8": {
    "speaker_name": "Bond",
    "speaker_code": "[BOND]",
    "has_zero_placeholder": false,
    "segments": {
      "single": "أنا في الموقع"
    }
  }
}
```

> **لا تغيّر** الحقول الإدارية (`speaker_code`, `has_zero_placeholder`). غيّر فقط `segments` و `speaker_name`.

### 3. الحقن

أنشئ ملف `my_config.json`:

```json
{
  "language": "arabic",
  "font": "./font_config.json",
  "ui": "./my_translation/ui.json",
  "dialogue": "./my_translation/dialogue.json",
  "speakers": "./my_translation/speakers.json"
}
```

شغّل:

```powershell
python tools/install_translation.py --config my_config.json
```

### اختبار قبل التطبيق

```powershell
python tools/install_translation.py --config my_config.json --dry
```

يعالج كل شي بالذاكرة بدون ما يكتب.

### الاسترجاع

```powershell
python tools/install_translation.py --restore
```

---

## 🇬🇧 English

### Three stages

```
1. Extract              2. Translate         3. Inject
   ───────                  ─────────            ──────
   chunks → JSON   →   translated JSON   →   chunks (modified)
```

### 1. Extract

```powershell
python tools/extract_text.py --game-dir "D:/Games/007 First Light" --out my_translation/
```

Produces:

| File | Contents |
|------|----------|
| `ui.json` | All UI strings (LOCR), organized by resource |
| `dialogue.json` | All dialogue (DLGE) with timing segments + speaker info |
| `speakers.json` | Unique speaker names to translate |

### 2. Translate

Open the JSON files. **Translate values, keep keys.**

> **Don't change** `speaker_code` or `has_zero_placeholder`. Only translate `segments` content and the `speaker_name` map.

### 3. Inject

Create `my_config.json`:

```json
{
  "language": "your_language",
  "font": "./font_config.json",
  "ui": "./my_translation/ui.json",
  "dialogue": "./my_translation/dialogue.json",
  "speakers": "./my_translation/speakers.json"
}
```

Run:

```powershell
python tools/install_translation.py --config my_config.json
```

### Language values

The `language` field selects the text processor:

| Value | Behavior |
|-------|----------|
| `arabic`, `persian`, `urdu`, `pashto`, `kashmiri`, `sindhi` | Applies arabic_reshaper + bidi (RTL handling) |
| anything else | Identity passthrough (raw text) |

### Dry run

```powershell
python tools/install_translation.py --config my_config.json --dry
```

### Restore

```powershell
python tools/install_translation.py --restore
```
