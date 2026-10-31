"""
Parser untuk data Sistem (GUDANG SURABAYA).
Format: dipisah spasi / tab
Contoh:
30/09/2026	Sales Delivery	13133	-19,94	88,579	Kg
"""

import re
from typing import List, Dict, Any, Optional
import pandas as pd

from src.utils.cleaners import clean_date, clean_number, clean_text
from config.settings import (
    TRANSACTION_MAPPING,
    PRODUCT_CONVERSION_POSITIVE,
    PRODUCT_CONVERSION_NEGATIVE,
)


def parse_system_text(
    raw_text: str,
    product_code: str = "",
    product_name: str = "",
) -> pd.DataFrame:
    """
    Parse teks data sistem menjadi DataFrame standar.
    """
    if not raw_text or not raw_text.strip():
        return pd.DataFrame()

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    records: List[Dict[str, Any]] = []

    for line in lines:
        # Skip header yang jelas
        lower = line.lower()
        if any(x in lower for x in ["gudang", "tanggal", "sales delivery", "product conversion"]) and \
           not re.search(r"\d{2}[/-]\d{2}[/-]\d{2,4}", line):
            # kemungkinan header, skip jika tidak ada tanggal
            if not re.search(r"\d{2}[/-]\d{2}[/-]\d{2,4}", line):
                continue

        record = _parse_system_line(line, product_code, product_name)
        if record:
            records.append(record)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    return df


def _parse_system_line(
    line: str,
    product_code: str,
    product_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Parse satu baris data sistem.
    Pola umum: Tanggal | Jenis Transaksi | No Dokumen | Qty | Saldo | Satuan

    Strategi robust:
    1. Split semua token.
    2. Tanggal = token pertama yang bisa di-parse sebagai tanggal.
    3. Satuan biasanya "Kg" di akhir.
    4. Dua angka terakhir sebelum satuan = Qty dan Saldo.
    5. Sisanya = Jenis + No Dokumen.
    """
    line = line.replace("\t", " ").strip()
    if not line:
        return None

    # Split biasa (spasi)
    parts = line.split()
    if len(parts) < 4:
        return None

    # 1. Tanggal
    tanggal = clean_date(parts[0])
    if tanggal is None:
        return None

    # 2. Cari satuan di akhir (Kg, kg, dll)
    satuan = "Kg"
    end_idx = len(parts)
    if parts[-1].lower() in {"kg", "kgs", "gram", "g"}:
        satuan = parts[-1]
        end_idx -= 1

    # 3. Kumpulkan angka setelah tanggal (sebelum satuan)
    # Aturan ketat:
    #   - No dokumen = bilangan BULAT POSITIF (tidak negatif, tidak desimal)
    #   - Qty        = boleh negatif / desimal / bulat (mutasi stok)
    #   - Saldo      = angka setelah qty (opsional)
    numbers = []  # (index, value, raw)
    for i in range(1, end_idx):
        num = clean_number(parts[i])
        if num is not None:
            numbers.append((i, num, parts[i]))

    if not numbers:
        return None

    def looks_decimal(raw: str) -> bool:
        r = raw.replace("-", "").strip()
        return "," in r or "." in r

    def is_doc_candidate(raw: str, val: float) -> bool:
        """No dokumen: bilangan bulat >= 0, tanpa desimal, biasanya tidak negatif."""
        if val < 0:
            return False
        if looks_decimal(raw):
            return False
        return abs(val - round(val)) < 1e-9

    qty = None
    qty_idx = None
    saldo = None
    no_dok = ""

    if len(numbers) == 1:
        qty_idx, qty, _ = numbers[0]
    elif len(numbers) == 2:
        a_i, a_v, a_r = numbers[-2]
        b_i, b_v, b_r = numbers[-1]
        if is_doc_candidate(a_r, a_v):
            # NoDok + Qty  (qty boleh -10 atau 74,04)
            no_dok = clean_text(a_r)
            qty_idx, qty = b_i, b_v
        else:
            # Qty + Saldo
            qty_idx, qty = a_i, a_v
            saldo = b_v
    else:
        # 3+ angka: utamakan pola NoDok + Qty + Saldo
        a_i, a_v, a_r = numbers[-3]
        b_i, b_v, b_r = numbers[-2]
        c_i, c_v, c_r = numbers[-1]
        if is_doc_candidate(a_r, a_v):
            no_dok = clean_text(a_r)
            qty_idx, qty = b_i, b_v
            saldo = c_v
        elif is_doc_candidate(b_r, b_v):
            # ... Qty-like, NoDok?, last — jarang; anggap b=doc c=qty
            no_dok = clean_text(b_r)
            qty_idx, qty = c_i, c_v
        else:
            # fallback: 2 angka terakhir = qty + saldo
            qty_idx, qty = b_i, b_v
            saldo = c_v
            if is_doc_candidate(a_r, a_v):
                no_dok = clean_text(a_r)

    if qty is None or qty_idx is None:
        return None

    # 4. Jenis = token teks sebelum angka pertama
    first_num_idx = numbers[0][0]
    jenis_tokens = parts[1:first_num_idx]
    jenis = clean_text(" ".join(jenis_tokens)) if jenis_tokens else "Unknown"
    if not jenis:
        jenis = "Unknown"

    # Validasi: no_dokumen tidak boleh terlihat seperti qty (negatif/desimal)
    if no_dok:
        nd = clean_number(no_dok)
        if nd is not None and (nd < 0 or looks_decimal(no_dok)):
            # tukar: yang dianggap dok sebenarnya qty
            # (amankan dari mis-parse)
            pass

        kategori, jenis_manual, grup = _map_transaction(jenis, qty)

    return {
        "tanggal": tanggal,
        "jenis": jenis,
        "kategori": kategori,
        "jenis_manual": jenis_manual,
        "grup": grup,
        "no_dokumen": no_dok,
        "nama_produk": product_name,
        "kode_produk": product_code,
        "qty": qty,
        "saldo": saldo,
        "satuan": satuan or "Kg",
        "sumber": "sistem",
        "catatan": "",
    }


def _map_transaction(jenis: str, qty: float) -> tuple:
    """
    Mapping jenis transaksi sistem ke (kategori, nama_manual, grup).
    grup: "Operasional" | "Pindah Gudang"
    """
    key = jenis.lower().strip()

    # Product Conversion khusus
    if "product conversion" in key or "conversion" in key:
        if qty >= 0:
            return PRODUCT_CONVERSION_POSITIVE
        else:
            return PRODUCT_CONVERSION_NEGATIVE

    # Mapping biasa
    for map_key, value in TRANSACTION_MAPPING.items():
        if map_key in key:
            if value is None:
                continue
            return value

    # Default
    if qty < 0:
        return ("Keluar", jenis, "Operasional")
    return ("Masuk", jenis, "Operasional")



def parse_system_with_diag(
    raw_text: str,
    product_code: str = "",
    product_name: str = "",
) -> tuple:
    """Return (DataFrame, list_skipped)."""
    import re
    import pandas as pd
    if not raw_text or not raw_text.strip():
        return pd.DataFrame(), []

    lines = raw_text.strip().splitlines()
    records = []
    skipped = []

    for i, line in enumerate(lines, start=1):
        raw = line.strip()
        if not raw:
            continue
        lower = raw.lower()
        if any(x in lower for x in ["gudang", "tanggal"]) and not re.search(
            r"\d{2}[/-]\d{2}[/-]\d{2,4}", raw
        ):
            skipped.append({"baris": i, "teks": raw[:80], "alasan": "Header / judul dilewati"})
            continue

        record = _parse_system_line(raw, product_code, product_name)
        if record:
            record["_baris_sumber"] = i
            record["_teks_asli"] = raw
            # Tandai mencurigakan: no_dokumen negatif / desimal (seharusnya tidak)
            nod = str(record.get("no_dokumen") or "")
            warn = ""
            try:
                from src.utils.cleaners import clean_number
                nv = clean_number(nod) if nod else None
                if nv is not None and (nv < 0 or ("," in nod or "." in nod)):
                    warn = "No dokumen mencurigakan (mirip qty) — cek baris ini"
            except Exception:
                pass
            record["_peringatan"] = warn
            records.append(record)
            if warn:
                skipped.append({
                    "baris": i,
                    "teks": raw[:100],
                    "alasan": "DIPARSING tapi " + warn,
                })
        else:
            skipped.append({
                "baris": i,
                "teks": raw[:100],
                "alasan": "Gagal parse (tanggal/qty tidak dikenali)",
            })

    df = pd.DataFrame(records) if records else pd.DataFrame()
    return df, skipped
