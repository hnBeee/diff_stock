"""
Modul perbandingan stok antara data Sistem dan data Manual.
"""

from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime


def prepare_comparison(
    df_sistem: pd.DataFrame,
    df_manual_masuk: pd.DataFrame,
    df_manual_keluar: pd.DataFrame,
    product_code: str,
    product_name: str = "",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Gabungkan semua data, filter produk & tanggal, lalu hitung selisih.
    """
    # Copy agar tidak mengubah session state
    df_sistem = df_sistem.copy() if not df_sistem.empty else pd.DataFrame()
    df_masuk = df_manual_masuk.copy() if not df_manual_masuk.empty else pd.DataFrame()
    df_keluar = df_manual_keluar.copy() if not df_manual_keluar.empty else pd.DataFrame()

    # Gabungkan manual
    frames = [f for f in [df_masuk, df_keluar] if not f.empty]
    df_manual = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Bersihkan kode & nama
    if not df_manual.empty:
        if "kode_produk" in df_manual.columns:
            df_manual["kode_produk"] = df_manual["kode_produk"].astype(str).str.strip()
        if "nama_produk" in df_manual.columns:
            df_manual["nama_produk"] = df_manual["nama_produk"].astype(str).str.strip()

    # Filter HANYA data manual (sistem tidak difilter — biasanya sudah per produk)
    code = (product_code or "").strip().upper()
    name = (product_name or "").strip().upper()
    excluded_manual = pd.DataFrame()

    if (code or name) and not df_manual.empty:
        mask = pd.Series([True] * len(df_manual), index=df_manual.index)
        if code and "kode_produk" in df_manual.columns:
            kode = df_manual["kode_produk"].str.upper()
            code_norm = code.replace(".", "").replace(" ", "").replace("-", "")
            kode_norm = (
                kode.str.replace(".", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.replace("-", "", regex=False)
            )
            mask_code = kode.str.contains(code, na=False) | kode_norm.str.contains(code_norm, na=False)
            mask = mask & mask_code
        if name and "nama_produk" in df_manual.columns:
            mask_name = df_manual["nama_produk"].str.upper().str.contains(name, na=False)
            # jika kode sudah diisi, name bersifat tambahan OR jika code kosong
            if code:
                # keduanya: harus match code (sudah di mask); name optional reinforce
                pass
            else:
                mask = mask & mask_name
        filtered = df_manual[mask]
        excluded_manual = df_manual[~mask].copy()
        df_manual = filtered

    # Simpan info filter untuk UI (attach ke result nanti via return)
    # Kita return excluded di dict

    # Filter tanggal
    def apply_date_filter(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "tanggal" not in df.columns:
            return df
        out = df
        if date_from is not None:
            out = out[out["tanggal"] >= date_from]
        if date_to is not None:
            out = out[out["tanggal"] <= date_to]
        return out

    df_sistem = apply_date_filter(df_sistem)
    df_manual = apply_date_filter(df_manual)

    # Pastikan qty numerik
    for df in (df_sistem, df_manual):
        if not df.empty and "qty" in df.columns:
            df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0)

    summary = _calculate_summary(df_sistem, df_manual)
    daily = _build_daily_table(df_sistem, df_manual)
    mismatches = _find_potential_mismatches(df_sistem, df_manual)

    return {
        "summary": summary,
        "daily": daily,
        "sistem": df_sistem.sort_values("tanggal") if not df_sistem.empty else df_sistem,
        "manual": df_manual.sort_values("tanggal") if not df_manual.empty else df_manual,
        "manual_excluded": excluded_manual.sort_values("tanggal") if not excluded_manual.empty else excluded_manual,
        "mismatches": mismatches,
        "filter_code": code,
        "filter_name": name,
    }


def _calculate_summary(df_sistem: pd.DataFrame, df_manual: pd.DataFrame) -> Dict[str, float]:
    """Hitung total masuk, keluar, selisih, dan breakdown Pindah Gudang."""
    def total_by(df: pd.DataFrame, kategori: str = None, grup: str = None) -> float:
        if df.empty:
            return 0.0
        mask = pd.Series([True] * len(df), index=df.index)
        if kategori and "kategori" in df.columns:
            mask &= df["kategori"] == kategori
        if grup and "grup" in df.columns:
            mask &= df["grup"] == grup
        if "qty" not in df.columns:
            return 0.0
        return float(df.loc[mask, "qty"].sum())

    sistem_masuk = total_by(df_sistem, "Masuk")
    sistem_keluar = total_by(df_sistem, "Keluar")
    manual_masuk = total_by(df_manual, "Masuk")
    manual_keluar = total_by(df_manual, "Keluar")

    # Breakdown pindah gudang
    sistem_transfer_keluar = total_by(df_sistem, "Keluar", "Pindah Gudang")
    sistem_transfer_masuk = total_by(df_sistem, "Masuk", "Pindah Gudang")
    manual_transfer_keluar = total_by(df_manual, "Keluar", "Pindah Gudang")
    manual_transfer_masuk = total_by(df_manual, "Masuk", "Pindah Gudang")

    # Operasional saja (tanpa transfer)
    sistem_ops_masuk = total_by(df_sistem, "Masuk", "Operasional")
    sistem_ops_keluar = total_by(df_sistem, "Keluar", "Operasional")
    manual_ops_masuk = total_by(df_manual, "Masuk", "Operasional")
    manual_ops_keluar = total_by(df_manual, "Keluar", "Operasional")

    saldo_awal = 0.0
    if not df_manual.empty and "jenis" in df_manual.columns:
        mask_awal = df_manual["jenis"].astype(str).str.lower().str.contains("saldo awal", na=False)
        saldo_awal = float(df_manual.loc[mask_awal, "qty"].sum())

    return {
        "saldo_awal_manual": saldo_awal,
        "sistem_masuk": sistem_masuk,
        "sistem_keluar": sistem_keluar,
        "sistem_netto": sistem_masuk + sistem_keluar,
        "manual_masuk": manual_masuk,
        "manual_keluar": manual_keluar,
        "manual_netto": manual_masuk + manual_keluar,
        "selisih_masuk": sistem_masuk - manual_masuk,
        "selisih_keluar": sistem_keluar - manual_keluar,
        "selisih_netto": (sistem_masuk + sistem_keluar) - (manual_masuk + manual_keluar),
        # Breakdown
        "sistem_ops_masuk": sistem_ops_masuk,
        "sistem_ops_keluar": sistem_ops_keluar,
        "manual_ops_masuk": manual_ops_masuk,
        "manual_ops_keluar": manual_ops_keluar,
        "sistem_transfer_masuk": sistem_transfer_masuk,
        "sistem_transfer_keluar": sistem_transfer_keluar,
        "manual_transfer_masuk": manual_transfer_masuk,
        "manual_transfer_keluar": manual_transfer_keluar,
    }


def _build_daily_table(df_sistem: pd.DataFrame, df_manual: pd.DataFrame) -> pd.DataFrame:
    """
    Tabel agregat per hari.
    Masuk/Keluar = Operasional saja.
    Pindah Gudang = kolom terpisah (tidak ikut Masuk/Keluar).
    """
    def daily_agg(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        cols = [
            "tanggal",
            f"{prefix}_masuk",
            f"{prefix}_keluar",
            f"{prefix}_pindah_gudang",
        ]
        if df.empty:
            return pd.DataFrame(columns=cols)

        tmp = df.copy()
        tmp["tgl"] = pd.to_datetime(tmp["tanggal"]).dt.date
        if "grup" not in tmp.columns:
            tmp["grup"] = "Operasional"

        ops = tmp[tmp["grup"] != "Pindah Gudang"]
        transfer = tmp[tmp["grup"] == "Pindah Gudang"]

        masuk = ops[ops["kategori"] == "Masuk"].groupby("tgl")["qty"].sum() if not ops.empty else pd.Series(dtype=float)
        keluar = ops[ops["kategori"] == "Keluar"].groupby("tgl")["qty"].sum() if not ops.empty else pd.Series(dtype=float)
        # Pindah gudang: total qty (negatif=keluar, positif=masuk)
        pindah = transfer.groupby("tgl")["qty"].sum() if not transfer.empty else pd.Series(dtype=float)

        result = pd.DataFrame({
            f"{prefix}_masuk": masuk,
            f"{prefix}_keluar": keluar,
            f"{prefix}_pindah_gudang": pindah,
        }).fillna(0)
        result.index.name = "tanggal"
        return result.reset_index()

    s = daily_agg(df_sistem, "sistem")
    m = daily_agg(df_manual, "manual")

    if s.empty and m.empty:
        return pd.DataFrame()

    daily = pd.merge(s, m, on="tanggal", how="outer").fillna(0)

    # Selisih operasional (tanpa pindah gudang)
    daily["selisih_masuk"] = daily.get("sistem_masuk", 0) - daily.get("manual_masuk", 0)
    daily["selisih_keluar"] = daily.get("sistem_keluar", 0) - daily.get("manual_keluar", 0)
    daily["selisih_pindah_gudang"] = (
        daily.get("sistem_pindah_gudang", 0) - daily.get("manual_pindah_gudang", 0)
    )
    daily["selisih_netto"] = (
        (daily.get("sistem_masuk", 0) + daily.get("sistem_keluar", 0) + daily.get("sistem_pindah_gudang", 0))
        - (daily.get("manual_masuk", 0) + daily.get("manual_keluar", 0) + daily.get("manual_pindah_gudang", 0))
    )
    daily = daily.sort_values("tanggal")

    # Urutan kolom yang rapi
    ordered = [
        "tanggal",
        "sistem_masuk", "sistem_keluar", "sistem_pindah_gudang",
        "manual_masuk", "manual_keluar", "manual_pindah_gudang",
        "selisih_masuk", "selisih_keluar", "selisih_pindah_gudang", "selisih_netto",
    ]
    ordered = [c for c in ordered if c in daily.columns]
    return daily[ordered]


def _find_potential_mismatches(
    df_sistem: pd.DataFrame,
    df_manual: pd.DataFrame,
    tolerance: float = 0.05,
) -> pd.DataFrame:
    """Placeholder untuk deteksi mismatch lebih detail di versi berikutnya."""
    return pd.DataFrame()
