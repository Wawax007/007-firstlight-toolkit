"""
shaping.py — معالجة نصوص اللغات اللي تحتاج reshaping/bidi
shaping.py — Text processing for languages requiring reshaping/bidi

ينفع لـ | Useful for: العربية، الفارسية، الأردية، الباشتو، الكشميرية...
                     Arabic, Persian, Urdu, Pashto, Kashmiri...

تتطلّب: pip install arabic_reshaper python-bidi
Requires: pip install arabic_reshaper python-bidi
"""
import re

# نحاول استيراد المكتبات | try to import the libraries
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# tokens داخلية لا نلمسها | inline tokens we preserve unchanged
INLINE_TOKEN = re.compile(r"\{[^{}]*\}|<b>|</b>|<li>|</li>|\[\d+\]|%[A-Za-z_][A-Za-z0-9_]*%")


def _require():
    if not AVAILABLE:
        raise ImportError(
            "shaping requires: pip install arabic_reshaper python-bidi"
        )


def shape_line(text):
    """يعيد تشكيل سطر واحد وعكسه للترتيب البصري (RTL).
       Reshape a single line and reverse for visual order (RTL).

       يحمي الـ tokens (مثل {0}, <b>, %DX_%) من المعالجة.
       Preserves tokens (e.g. {0}, <b>, %DX_%) from being processed."""
    _require()
    tokens = []

    def replace(m):
        tokens.append(m.group(0))
        return chr(0xE000 + len(tokens) - 1)   # Private Use Area

    masked = INLINE_TOKEN.sub(replace, text)
    visual = get_display(arabic_reshaper.reshape(masked))
    for i, tok in enumerate(tokens):
        visual = visual.replace(chr(0xE000 + i), tok)
    return visual


def wrap_words(text, width):
    """يقسّم النص لأسطر بعرض معيّن (بالكلمات).
       Wrap text into lines of given width by words."""
    out = []
    cur = ""
    for w in text.split(" "):
        if w == "":
            continue
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out or [""]


def shape_block(text, width_tight=18, width_loose=40):
    """يشكّل نص متعدّد الأسطر (مع <br>).
       Shape multi-line text (with <br>).

       يستخدم العرض الضيّق للنصوص القصيرة بلا <br>،
       والعرض الواسع للنصوص الطويلة أو فيها <br>.
       Uses tight width for short/single-line text, loose for long/multi-line."""
    _require()
    w = width_tight if (("<br" not in text) and (len(text) <= 40)) else width_loose
    lines = []
    for s in re.split(r"<br\s*/?>", text):
        s = s.strip()
        if s == "":
            lines.append("")
        else:
            lines.extend(wrap_words(s, w))
    return "<br>".join(shape_line(x) if x else "" for x in lines)


def shape_subtitle(text, width=40):
    """يشكّل سطر ترجمة (شرح فيلم) بعرض ثابت.
       Shape a subtitle (dialogue line) at fixed width."""
    _require()
    lines = []
    for s in re.split(r"<br\s*/?>", text):
        s = s.strip()
        if s == "":
            lines.append("")
        else:
            lines.extend(wrap_words(s, width))
    return "<br>".join(shape_line(x) if x else "" for x in lines)


# ============================================================
# Identity fallback (للغات اللي ما تحتاج reshaping)
# ============================================================
def identity(text):
    """مرّر النص كما هو (للغات بدون reshaping).
       Pass text through unchanged (for non-RTL languages)."""
    return text


def get_processor(name):
    """يرجع دالة المعالجة المناسبة حسب اسم اللغة.
       Get the appropriate processor function by name.

       arabic, persian, urdu, pashto → shape_line
       any other / 'none'            → identity"""
    rtl_languages = {"arabic", "persian", "urdu", "pashto", "kashmiri", "sindhi"}
    if name.lower() in rtl_languages:
        return shape_line
    return identity
