"""
Fungsi pembersihan data umum: tanggal, angka, teks.
"""

import re
from datetime import datetime
from typing import Optional, Union

from config.settings import DATE_FORMATS, DECIMAL_COMMA


def clean_number(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Mengubah string angka (bisa pakai koma atau titik) menjadi float.
    Contoh: "19,94" → 19.94 | "-29.38" → -29.38 | "1.911" → 1.911
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "-"}:
        return None

    # Hapus karakter non-numerik kecuali . , - 
    s = re.sub(r"[^\d.,\-]", "", s)

    if not s or s in {".", ",", "-", "-.", "-,"}:
        return None

    # Deteksi mana yang jadi desimal
    if DECIMAL_COMMA:
        # Jika ada koma, anggap koma = desimal, hapus titik (pemisah ribuan)
        if "," in s:
            s = s.replace(".", "")
            s = s.replace(",", ".")
        # Jika hanya titik, biarkan (sudah desimal)
    else:
        if "." in s and "," in s:
            s = s.replace(",", "")
        elif "," in s:
            s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return None


def clean_date(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse berbagai format tanggal menjadi datetime.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value

    s = str(value).strip()
    if not s:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    # Coba dateutil sebagai fallback
    try:
        from dateutil import parser as date_parser
        return date_parser.parse(s, dayfirst=True)
    except Exception:
        return None


def clean_text(value: Union[str, None]) -> str:
    """Bersihkan spasi berlebih dan karakter aneh."""
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_header(text: str) -> str:
    """Normalisasi nama header untuk matching."""
    return clean_text(text).lower().replace(" ", "_")
