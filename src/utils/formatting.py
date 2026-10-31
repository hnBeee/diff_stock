"""
Format angka gaya Indonesia: 1.234,56 (titik ribuan, koma desimal).
Default 2 digit di belakang koma agar tidak terbaca seperti ton.
"""


def fmt_qty(value, decimals: int = 2) -> str:
    """
    Format qty untuk tampilan.
    2 -> "2,00"
    1234.5 -> "1.234,50"
    -9.3 -> "-9,30"
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    # Format dengan titik desimal dulu, lalu tukar
    sign = "-" if v < 0 else ""
    v = abs(v)
    formatted = f"{v:,.{decimals}f}"  # 1,234.56 (US)
    # Tukar: , ribuan sementara → X, . desimal → ,, X → .
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + formatted


def fmt_qty_plain(value, decimals: int = 2) -> str:
    """Tanpa pemisah ribuan: 1234,50 — cocok untuk sel kecil."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{v:.{decimals}f}".replace(".", ",")
