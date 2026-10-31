"""
Konfigurasi global aplikasi Stock Difference Checker.
Ubah nilai di sini jika ingin menyesuaikan perilaku default.
"""

from pathlib import Path

# === Path ===
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLES_DIR = DATA_DIR / "samples"

# === Aplikasi ===
APP_TITLE = "Stock Difference Checker"
APP_ICON = "📦"
APP_LAYOUT = "wide"

# === Mapping Jenis Transaksi Sistem → (kategori, jenis_manual, grup) ===
# grup: "Operasional" | "Pindah Gudang"
TRANSACTION_MAPPING = {
    "sales delivery": ("Keluar", "Jual", "Operasional"),
    "sales return": ("Masuk", "Return Penjualan", "Operasional"),
    "product conversion": None,  # khusus: tergantung tanda qty
    "stock adjustment": ("Masuk", "Stock Adjustment", "Operasional"),
    "warehouse transfer": ("Keluar", "Pindah Gudang", "Pindah Gudang"),
}

# Product Conversion
PRODUCT_CONVERSION_POSITIVE = ("Masuk", "Hasil Prod.", "Operasional")
PRODUCT_CONVERSION_NEGATIVE = ("Keluar", "Keluar Prod.", "Operasional")

# Keyword di data MANUAL yang menandakan Pindah Gudang
# (case-insensitive, partial match)
TRANSFER_KEYWORDS = [
    "pindah gudang",
    "warehouse transfer",
    "transfer",
    "sby - smr",
    "sby-smr",
    "sby - mlg",
    "sby-mlg",
    "sby - smg",
    "sby-smg",
    "mlg - sby",
    "mlg-sby",
    "smg - sby",
    "smg-sby",
    "smr - sby",
    "smr-sby",
    "sby -",
    "- sby",
]

# === Format Tanggal ===
DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
]

DECIMAL_COMMA = True

DEFAULT_PRODUCT_CODE = "BC.RW19"
DEFAULT_PRODUCT_NAME = "CUT BEEF RW 19"
