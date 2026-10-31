"""
Parser untuk data Manual (Barang Masuk & Barang Keluar).

Mendukung: pipe |, tab, atau spasi.
Menandai grup: Operasional vs Pindah Gudang.
"""

import re
from typing import List, Dict, Any, Optional
import pandas as pd

from src.utils.cleaners import clean_date, clean_number, clean_text
from config.settings import TRANSFER_KEYWORDS


def parse_manual_text(
    raw_text: str,
    default_kategori: str = "Keluar",
) -> pd.DataFrame:
    if not raw_text or not raw_text.strip():
        return pd.DataFrame()

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    records: List[Dict[str, Any]] = []

    for line in lines:
        if re.match(r"^[\|\s\-_]+$", line):
            continue
        lower = line.lower()
        if ("tanggal" in lower or "date" in lower) and (
            "jual" in lower or "produk" in lower or "qty" in lower or "hasil" in lower
        ):
            continue

        record = _parse_manual_line(line, default_kategori)
        if record:
            records.append(record)

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def _parse_manual_line(line: str, default_kategori: str) -> Optional[Dict[str, Any]]:
    parts = _smart_split(line)
    if len(parts) < 3:
        return None

    tanggal = clean_date(parts[0])
    if tanggal is None:
        return None

    qty = None
    qty_idx = None
    catatan = ""

    for i in range(len(parts) - 1, 0, -1):
        num = clean_number(parts[i])
        if num is not None:
            qty = num
            qty_idx = i
            if i + 1 < len(parts):
                catatan = clean_text(" ".join(parts[i + 1:]))
            break

    if qty is None or qty_idx is None:
        return None

    middle = parts[1:qty_idx]
    jenis = ""
    nama_produk = ""
    kode_produk = ""

    if len(middle) == 0:
        jenis = "Unknown"
    elif len(middle) == 1:
        jenis = clean_text(middle[0])
    elif len(middle) == 2:
        jenis = clean_text(middle[0])
        if _looks_like_code(middle[1]):
            kode_produk = clean_text(middle[1])
        else:
            nama_produk = clean_text(middle[1])
    else:
        jenis = clean_text(middle[0])
        if _looks_like_code(middle[-1]):
            kode_produk = clean_text(middle[-1])
            nama_produk = clean_text(" ".join(middle[1:-1]))
        else:
            nama_produk = clean_text(" ".join(middle[1:]))

    kategori = _detect_kategori(jenis, default_kategori)
    grup = _detect_grup(jenis, catatan)

    if kategori == "Keluar" and qty > 0:
        qty = -abs(qty)
    elif kategori == "Masuk" and qty < 0:
        qty = abs(qty)

    return {
        "tanggal": tanggal,
        "jenis": jenis,
        "kategori": kategori,
        "jenis_manual": jenis,
        "grup": grup,
        "no_dokumen": "",
        "nama_produk": nama_produk,
        "kode_produk": kode_produk,
        "qty": qty,
        "saldo": None,
        "satuan": "Kg",
        "sumber": "manual",
        "catatan": catatan,
    }


def _smart_split(line: str) -> List[str]:
    line = line.strip()
    if "|" in line:
        parts = [p.strip() for p in line.strip("|").split("|")]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            return parts
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            return parts
    parts = re.split(r"\s{2,}", line)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 3:
        return parts
    return line.split()


def _looks_like_code(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", t) and ("." in t or "-" in t or "_" in t or len(t) <= 12):
        return True
    if re.match(r"^[A-Z0-9.\-_]{2,15}$", t) and any(c.isalpha() for c in t):
        return True
    return False


def _detect_kategori(jenis: str, default: str) -> str:
    j = jenis.lower()
    masuk_keywords = [
        "hasil prod", "hasil produksi", "beli", "pembelian",
        "return penjualan", "retur penjualan", "saldo awal",
        "stock adjustment", "masuk", "produksi",
        "mlg - sby", "mlg-sby", "smg - sby", "smg-sby", "smr - sby", "smr-sby",
    ]
    keluar_keywords = [
        "jual", "penjualan", "keluar prod", "keluar produksi",
        "pindah gudang", "transfer", "return pembelian", "retur pembelian",
        "sby - smr", "sby-smr", "sby - mlg", "sby-mlg", "sby - smg", "sby-smg",
        "sample", "keluar",
    ]
    for kw in masuk_keywords:
        if kw in j:
            return "Masuk"
    for kw in keluar_keywords:
        if kw in j:
            return "Keluar"
    return default


def _detect_grup(jenis: str, catatan: str = "") -> str:
    """Operasional vs Pindah Gudang."""
    text = f"{jenis} {catatan}".lower()
    for kw in TRANSFER_KEYWORDS:
        if kw in text:
            return "Pindah Gudang"
    return "Operasional"



def parse_manual_with_diag(
    raw_text: str,
    default_kategori: str = "Keluar",
) -> tuple:
    """
    Return (DataFrame, list_skipped).
    list_skipped: [{"baris": int, "teks": str, "alasan": str}, ...]
    """
    if not raw_text or not raw_text.strip():
        return __import__("pandas").DataFrame(), []

    import re
    lines = raw_text.strip().splitlines()
    records = []
    skipped = []

    for i, line in enumerate(lines, start=1):
        raw = line.strip()
        if not raw:
            continue
        if re.match(r"^[\|\s\-_]+$", raw):
            skipped.append({"baris": i, "teks": raw[:80], "alasan": "Baris pemisah / kosong"})
            continue
        lower = raw.lower()
        if ("tanggal" in lower or "date" in lower) and (
            "jual" in lower or "produk" in lower or "qty" in lower or "hasil" in lower
        ):
            skipped.append({"baris": i, "teks": raw[:80], "alasan": "Header dilewati"})
            continue

        record = _parse_manual_line(raw, default_kategori)
        if record:
            record["_baris_sumber"] = i
            records.append(record)
        else:
            skipped.append({
                "baris": i,
                "teks": raw[:100],
                "alasan": "Gagal parse (tanggal/qty tidak valid atau kolom kurang)",
            })

    import pandas as pd
    df = pd.DataFrame(records) if records else pd.DataFrame()
    return df, skipped
