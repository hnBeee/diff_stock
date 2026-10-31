"""
Generate kesimpulan otomatis dari tabel perbandingan harian.
Mendeteksi pola: selisih biasa, pindah gudang beda 1 hari, koreksi salah nota.
"""

from typing import Dict, Any, List
import pandas as pd
from datetime import timedelta
from src.utils.formatting import fmt_qty


def generate_insights(result: Dict[str, Any], tolerance: float = 0.05) -> Dict[str, Any]:
    """
    Analisis hasil perbandingan → teks kesimpulan + daftar temuan.
    """
    daily = result.get("daily", pd.DataFrame())
    summary = result.get("summary", {})

    findings: List[str] = []
    issue_dates: List[Dict[str, Any]] = []

    if daily.empty:
        return {
            "headline": "Belum ada data harian untuk dianalisis.",
            "findings": [],
            "issue_dates": [],
            "tips": [],
        }

    df = daily.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"])

    # Pastikan kolom ada
    for c in [
        "sistem_masuk", "sistem_keluar", "sistem_pindah_gudang",
        "manual_masuk", "manual_keluar", "manual_pindah_gudang",
        "selisih_masuk", "selisih_keluar", "selisih_pindah_gudang", "selisih_netto",
    ]:
        if c not in df.columns:
            df[c] = 0.0

    # --- 1. Ringkasan keseluruhan ---
    selisih_netto = float(summary.get("selisih_netto", 0) or 0)
    if abs(selisih_netto) <= tolerance:
        headline = "✅ Secara keseluruhan stok Sistem dan Manual sudah seimbang (selisih netto ≈ 0)."
    elif selisih_netto > 0:
        headline = (
            f"⚠️ Sistem mencatat netto lebih tinggi {fmt_qty(selisih_netto)} Kg dibanding Manual. "
            "Periksa tanggal-tanggal di bawah."
        )
    else:
        headline = (
            f"⚠️ Manual mencatat netto lebih tinggi {fmt_qty(abs(selisih_netto))} Kg dibanding Sistem. "
            "Periksa tanggal-tanggal di bawah."
        )

    # --- 2. Deteksi koreksi salah nota (pasangan keluar + return berurutan di sistem, manual 0) ---
    nota_pairs = _detect_nota_errors(df, tolerance)
    used_dates = set()
    for pair in nota_pairs:
        used_dates.add(pair["tgl1"])
        used_dates.add(pair["tgl2"])
        findings.append(pair["text"])
        issue_dates.append({
            "tanggal": pair["tgl1"].strftime("%d/%m/%Y") + " & " + pair["tgl2"].strftime("%d/%m/%Y"),
            "jenis": "Kemungkinan salah nota",
            "selisih": pair["qty"],
            "keterangan": pair["detail"],
        })

    # --- 3. Deteksi pindah gudang beda 1 hari ---
    transfer_shifts = _detect_transfer_day_shift(df, tolerance)
    for item in transfer_shifts:
        used_dates.add(item["tgl_manual"])
        used_dates.add(item["tgl_sistem"])
        findings.append(item["text"])
        issue_dates.append({
            "tanggal": item["tgl_manual"].strftime("%d/%m/%Y")
            + " → "
            + item["tgl_sistem"].strftime("%d/%m/%Y"),
            "jenis": "Pindah gudang beda hari",
            "selisih": item["qty"],
            "keterangan": item["detail"],
        })

    # --- 4. Tanggal lain yang masih ada selisih signifikan ---
    for _, row in df.iterrows():
        tgl = row["tanggal"]
        if tgl in used_dates:
            continue
        sn = float(row.get("selisih_netto", 0) or 0)
        if abs(sn) <= tolerance:
            continue

        sm = float(row.get("selisih_masuk", 0) or 0)
        sk = float(row.get("selisih_keluar", 0) or 0)
        sp = float(row.get("selisih_pindah_gudang", 0) or 0)

        parts = []
        if abs(sm) > tolerance:
            parts.append(f"masuk {fmt_qty(sm)}")
        if abs(sk) > tolerance:
            parts.append(f"keluar {fmt_qty(sk)}")
        if abs(sp) > tolerance:
            parts.append(f"pindah gudang {fmt_qty(sp)}")

        detail = ", ".join(parts) if parts else f"netto {fmt_qty(sn)}"
        tgl_str = tgl.strftime("%d/%m/%Y")
        findings.append(
            f"📅 {tgl_str}: ada selisih ({detail} Kg). "
            "Perlu dicek apakah ada transaksi yang belum diinput atau qty salah."
        )
        issue_dates.append({
            "tanggal": tgl_str,
            "jenis": "Selisih harian",
            "selisih": sn,
            "keterangan": detail + " Kg",
        })

    if not findings:
        findings.append("Tidak ada selisih harian yang mencolok. Data terlihat konsisten.")

    # --- 5. Tips singkat ---
    tips = [
        "Pindah gudang: manual sering diinput hari pengiriman, sistem hari barang sampai (±1 hari) — itu wajar.",
        "Salah nota sales: biasanya ada keluar di sistem lalu return di hari berikutnya dengan qty sama, sementara manual tidak berubah.",
        "Selisih yang tersisa setelah pola di atas biasanya perlu dicek manual (qty salah / belum diinput).",
    ]

    return {
        "headline": headline,
        "findings": findings,
        "issue_dates": issue_dates,
        "tips": tips,
    }


def _detect_nota_errors(df: pd.DataFrame, tolerance: float) -> List[Dict[str, Any]]:
    """
    Pola: sistem keluar -X di hari T, sistem masuk +X di hari T+1 (atau dekat),
    manual masuk/keluar ≈ 0 di kedua hari → kemungkinan salah nota.
    """
    pairs = []
    df = df.sort_values("tanggal").reset_index(drop=True)

    for i in range(len(df) - 1):
        r1 = df.iloc[i]
        # Cari pasangan dalam 1-2 hari berikutnya
        for j in range(i + 1, min(i + 3, len(df))):
            r2 = df.iloc[j]
            gap = (r2["tanggal"] - r1["tanggal"]).days
            if gap < 1 or gap > 2:
                continue

            # Sistem: keluar di hari 1, masuk di hari 2 (qty mirip)
            sys_out = abs(float(r1.get("sistem_keluar", 0) or 0))
            sys_in = float(r2.get("sistem_masuk", 0) or 0)
            man1 = abs(float(r1.get("manual_keluar", 0) or 0)) + abs(float(r1.get("manual_masuk", 0) or 0))
            man2 = abs(float(r2.get("manual_keluar", 0) or 0)) + abs(float(r2.get("manual_masuk", 0) or 0))

            if sys_out > tolerance and abs(sys_out - sys_in) <= max(tolerance, sys_out * 0.05):
                # Manual hampir tidak bergerak di kedua hari
                if man1 <= tolerance and man2 <= tolerance:
                    qty = sys_out
                    pairs.append({
                        "tgl1": r1["tanggal"],
                        "tgl2": r2["tanggal"],
                        "qty": qty,
                        "detail": (
                            f"Sistem keluar {fmt_qty(qty)} lalu masuk/return {fmt_qty(sys_in)}; "
                            "Manual tidak berubah"
                        ),
                        "text": (
                            f"📝 {r1['tanggal'].strftime('%d/%m/%Y')} → "
                            f"{r2['tanggal'].strftime('%d/%m/%Y')}: "
                            f"kemungkinan **salah nota sales** "
                            f"(sistem −{fmt_qty(qty)} lalu +{fmt_qty(sys_in)}, manual tidak ada mutasi). "
                            "Bukan stok fisik yang bergerak."
                        ),
                    })
                    break

            # Atau sebaliknya: sistem masuk dulu lalu keluar (jarang tapi mungkin)
            sys_in1 = float(r1.get("sistem_masuk", 0) or 0)
            sys_out2 = abs(float(r2.get("sistem_keluar", 0) or 0))
            if sys_in1 > tolerance and abs(sys_in1 - sys_out2) <= max(tolerance, sys_in1 * 0.05):
                if man1 <= tolerance and man2 <= tolerance:
                    qty = sys_in1
                    pairs.append({
                        "tgl1": r1["tanggal"],
                        "tgl2": r2["tanggal"],
                        "qty": qty,
                        "detail": f"Sistem masuk {fmt_qty(qty)} lalu keluar {fmt_qty(sys_out2)}; Manual tidak berubah",
                        "text": (
                            f"📝 {r1['tanggal'].strftime('%d/%m/%Y')} → "
                            f"{r2['tanggal'].strftime('%d/%m/%Y')}: "
                            f"kemungkinan koreksi nota "
                            f"(sistem +{fmt_qty(qty)} lalu −{fmt_qty(sys_out2)}, manual tidak berubah)."
                        ),
                    })
                    break

    return pairs


def _detect_transfer_day_shift(df: pd.DataFrame, tolerance: float) -> List[Dict[str, Any]]:
    """
    Pola: manual pindah gudang di hari T, sistem pindah gudang di T+1 (qty mirip).
    """
    items = []
    df = df.sort_values("tanggal").reset_index(drop=True)

    for i in range(len(df)):
        r1 = df.iloc[i]
        man_pg = float(r1.get("manual_pindah_gudang", 0) or 0)
        if abs(man_pg) <= tolerance:
            continue

        for j in range(len(df)):
            if i == j:
                continue
            r2 = df.iloc[j]
            gap = (r2["tanggal"] - r1["tanggal"]).days
            # Manual lebih dulu (gap 1-2 hari) atau sistem lebih dulu
            if abs(gap) < 1 or abs(gap) > 2:
                continue

            sys_pg = float(r2.get("sistem_pindah_gudang", 0) or 0)
            if abs(sys_pg) <= tolerance:
                continue

            # Qty mirip (arah sama atau mirror)
            if abs(abs(man_pg) - abs(sys_pg)) <= max(tolerance, abs(man_pg) * 0.1):
                if gap > 0:
                    # Manual lebih dulu
                    items.append({
                        "tgl_manual": r1["tanggal"],
                        "tgl_sistem": r2["tanggal"],
                        "qty": abs(man_pg),
                        "detail": (
                            f"Manual {fmt_qty(man_pg)} Kg, Sistem {fmt_qty(sys_pg)} Kg "
                            f"(selisih hari: {gap})"
                        ),
                        "text": (
                            f"🚚 Pindah gudang: Manual "
                            f"{r1['tanggal'].strftime('%d/%m/%Y')} ({fmt_qty(man_pg)} Kg), "
                            f"Sistem {r2['tanggal'].strftime('%d/%m/%Y')} ({fmt_qty(sys_pg)} Kg). "
                            "Wajar jika input sistem menunggu barang sampai di tujuan."
                        ),
                    })
                else:
                    items.append({
                        "tgl_manual": r2["tanggal"],
                        "tgl_sistem": r1["tanggal"],
                        "qty": abs(sys_pg),
                        "detail": (
                            f"Sistem {fmt_qty(sys_pg)} Kg dulu, Manual {fmt_qty(man_pg)} Kg "
                            f"(selisih hari: {abs(gap)})"
                        ),
                        "text": (
                            f"🚚 Pindah gudang: Sistem "
                            f"{r1['tanggal'].strftime('%d/%m/%Y')} ({fmt_qty(sys_pg)} Kg), "
                            f"Manual {r2['tanggal'].strftime('%d/%m/%Y')} ({fmt_qty(man_pg)} Kg). "
                            "Cek apakah input manual terlambat."
                        ),
                    })
                break

    # Dedup kasar
    seen = set()
    unique = []
    for it in items:
        key = (it["tgl_manual"], it["tgl_sistem"], round(it["qty"], 3))
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique
