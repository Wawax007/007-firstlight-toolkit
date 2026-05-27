"""
glacier — مكتبة قراءة/كتابة ملفات Glacier engine
glacier — Glacier engine file I/O library

تركّز على 007 First Light (RPKG v2)، لكن أغلب المنطق ينطبق على Hitman أيضاً.
Focused on 007 First Light (RPKG v2), but most logic applies to Hitman too.
"""
__version__ = "1.0.0"

from . import rpkg
from . import locr
from . import dlge
from . import gfxf
from . import shaping
from . import steam

__all__ = ["rpkg", "locr", "dlge", "gfxf", "shaping", "steam"]
