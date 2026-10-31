"""
Export hasil perbandingan ke Excel dan PDF (lengkap).
"""

from __future__ import annotations

import io
import re
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

from src.utils.formatting import fmt_qty

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


def to_excel_bytes(result: Dict[str, Any], product_code: str = "", insights: Optional[Dict] = None) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary = result.get("summary", {})
        rows = [
            {"Metrik": "Saldo Awal (Manual)", "Nilai (Kg)": summary.get("saldo_awal_manual", 0)},
            {"Metrik": "Sistem - Total Masuk", "Nilai (Kg)": summary.get("sistem_masuk", 0)},
            {"Metrik": "Sistem - Total Keluar", "Nilai (Kg)": summary.get("sistem_keluar", 0)},
            {"Metrik": "Sistem - Netto", "Nilai (Kg)": summary.get("sistem_netto", 0)},
            {"Metrik": "Manual - Total Masuk", "Nilai (Kg)": summary.get("manual_masuk", 0)},
            {"Metrik": "Manual - Total Keluar", "Nilai (Kg)": summary.get("manual_keluar", 0)},
            {"Metrik": "Manual - Netto", "Nilai (Kg)": summary.get("manual_netto", 0)},
            {"Metrik": "Selisih Masuk", "Nilai (Kg)": summary.get("selisih_masuk", 0)},
            {"Metrik": "Selisih Keluar", "Nilai (Kg)": summary.get("selisih_keluar", 0)},
            {"Metrik": "Selisih Netto", "Nilai (Kg)": summary.get("selisih_netto", 0)},
            {"Metrik": "Sistem Transfer Masuk", "Nilai (Kg)": summary.get("sistem_transfer_masuk", 0)},
            {"Metrik": "Sistem Transfer Keluar", "Nilai (Kg)": summary.get("sistem_transfer_keluar", 0)},
            {"Metrik": "Manual Transfer Masuk", "Nilai (Kg)": summary.get("manual_transfer_masuk", 0)},
            {"Metrik": "Manual Transfer Keluar", "Nilai (Kg)": summary.get("manual_transfer_keluar", 0)},
        ]
        pd.DataFrame(rows).to_excel(writer, sheet_name="Ringkasan", index=False)

        daily = result.get("daily", pd.DataFrame())
        if not daily.empty:
            daily.to_excel(writer, sheet_name="Perbandingan Harian", index=False)

        if insights and insights.get("issue_dates"):
            pd.DataFrame(insights["issue_dates"]).to_excel(writer, sheet_name="Kesimpulan", index=False)

        by_type = build_daily_by_type(result)
        if not by_type.empty:
            by_type.to_excel(writer, sheet_name="Rekap Jenis Harian", index=False)

        sistem = result.get("sistem", pd.DataFrame())
        if not sistem.empty:
            cols = [c for c in ["tanggal", "jenis", "kategori", "grup", "no_dokumen", "qty", "saldo", "satuan"] if c in sistem.columns]
            sistem[cols].to_excel(writer, sheet_name="Detail Sistem", index=False)

        manual = result.get("manual", pd.DataFrame())
        if not manual.empty:
            cols = [c for c in ["tanggal", "jenis", "kategori", "grup", "nama_produk", "kode_produk", "qty", "catatan"] if c in manual.columns]
            manual[cols].to_excel(writer, sheet_name="Detail Manual", index=False)

    output.seek(0)
    return output.getvalue()


def build_daily_by_type(result: Dict[str, Any]) -> pd.DataFrame:
    frames = []
    for sumber, key in [("sistem", "sistem"), ("manual", "manual")]:
        df = result.get(key, pd.DataFrame())
        if df.empty or "tanggal" not in df.columns:
            continue
        tmp = df.copy()
        tmp["tgl"] = pd.to_datetime(tmp["tanggal"]).dt.date
        col_jenis = "jenis_manual" if "jenis_manual" in tmp.columns else "jenis"
        if col_jenis not in tmp.columns:
            col_jenis = "jenis"
        g = tmp.groupby(["tgl", col_jenis, "kategori"], dropna=False)["qty"].sum().reset_index()
        g = g.rename(columns={"tgl": "tanggal", col_jenis: "jenis", "qty": f"qty_{sumber}"})
        frames.append(g)

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    for f in frames[1:]:
        merged = pd.merge(merged, f, on=["tanggal", "jenis", "kategori"], how="outer")
    if "qty_sistem" not in merged.columns:
        merged["qty_sistem"] = 0.0
    if "qty_manual" not in merged.columns:
        merged["qty_manual"] = 0.0
    merged = merged.fillna(0)
    merged["selisih"] = merged["qty_sistem"] - merged["qty_manual"]
    merged = merged.sort_values(["tanggal", "kategori", "jenis"])
    return merged


def _latin(text: str) -> str:
    if text is None:
        return ""
    replacements = {
        "✅": "[OK]", "⚠️": "[!]", "📅": "", "📝": "", "🚚": "",
        "💡": "", "📦": "", "—": "-", "–": "-", """: '"', """: '"',
        "'": "'", "'": "'", "≈": "~", "→": "->", "·": "-",
    }
    s = str(text)
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"\*+", "", s)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _safe_text(pdf, text: str, line_h: float = 5.0):
    """Tulis teks multi-baris dengan aman (hindari error horizontal space)."""
    pdf.set_x(pdf.l_margin)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    if usable < 10:
        pdf.add_page()
        pdf.set_x(pdf.l_margin)
        usable = pdf.w - pdf.l_margin - pdf.r_margin
    text = _latin(text)
    # pecah kata sangat panjang agar bisa di-wrap
    text = re.sub(r"(\S{40})", r"\1 ", text)
    try:
        pdf.multi_cell(usable, line_h, text)
    except Exception:
        # fallback: potong manual
        pdf.set_x(pdf.l_margin)
        for i in range(0, len(text), 80):
            chunk = text[i : i + 80]
            try:
                pdf.cell(0, line_h, chunk, new_x="LMARGIN", new_y="NEXT")
            except Exception:
                pdf.cell(0, line_h, chunk[:60], new_x="LMARGIN", new_y="NEXT")


def to_pdf_bytes(
    result: Dict[str, Any],
    product_code: str = "",
    product_name: str = "",
    insights: Optional[Dict] = None,
) -> bytes:
    if not HAS_FPDF:
        return b"PDF library (fpdf2) tidak terinstall. Jalankan: pip install fpdf2"

    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=12, top=12, right=12)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, "Laporan Selisih Stok", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5.5, _latin(f"Produk: {product_name} ({product_code})"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 5.5, f"Dibuat: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)

    summary = result.get("summary", {})
    pdf.section_title("1. Ringkasan")
    summary_rows = [
        ("Saldo Awal (Manual)", summary.get("saldo_awal_manual", 0)),
        ("Sistem Masuk", summary.get("sistem_masuk", 0)),
        ("Sistem Keluar", summary.get("sistem_keluar", 0)),
        ("Sistem Netto", summary.get("sistem_netto", 0)),
        ("Manual Masuk", summary.get("manual_masuk", 0)),
        ("Manual Keluar", summary.get("manual_keluar", 0)),
        ("Manual Netto", summary.get("manual_netto", 0)),
        ("Selisih Masuk", summary.get("selisih_masuk", 0)),
        ("Selisih Keluar", summary.get("selisih_keluar", 0)),
        ("Selisih Netto", summary.get("selisih_netto", 0)),
        ("Sistem Pindah Gudang (keluar)", summary.get("sistem_transfer_keluar", 0)),
        ("Manual Pindah Gudang (keluar)", summary.get("manual_transfer_keluar", 0)),
        ("Manual Pindah Gudang (masuk)", summary.get("manual_transfer_masuk", 0)),
    ]
    pdf.set_font("Helvetica", size=9)
    for label, val in summary_rows:
        pdf.set_x(pdf.l_margin)
        pdf.cell(100, 5.2, _latin(label))
        pdf.cell(0, 5.2, f"{fmt_qty(val)} Kg", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Kesimpulan
    pdf.section_title("2. Kesimpulan Otomatis")
    if insights:
        pdf.set_font("Helvetica", size=9)
        _safe_text(pdf, insights.get("headline", ""), 5)
        pdf.ln(1)
        for f in insights.get("findings", []):
            text = str(f).replace("**", "")
            _safe_text(pdf, f"- {text}", 4.8)
        issues = insights.get("issue_dates") or []
        if issues:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_x(pdf.l_margin)
            pdf.cell(0, 5, "Tanggal bermasalah:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=8)
            for it in issues:
                line = (
                    f"{it.get('tanggal', '')} | {it.get('jenis', '')} | "
                    f"{fmt_qty(it.get('selisih', 0))} Kg | {it.get('keterangan', '')}"
                )
                _safe_text(pdf, line, 4.5)
    else:
        pdf.set_font("Helvetica", size=9)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, "Tidak ada kesimpulan.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Rekap per jenis per hari
    pdf.section_title("3. Rekap per Jenis per Hari")
    by_type = build_daily_by_type(result)
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    if by_type.empty:
        pdf.set_font("Helvetica", size=9)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, "Tidak ada data.", new_x="LMARGIN", new_y="NEXT")
    else:
        # Lebar kolom proporsional (total ~186mm untuk A4 margin 12)
        w_tgl, w_jenis, w_kat, w_sys, w_man, w_sel = 20, 42, 20, 28, 28, 28
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_x(pdf.l_margin)
        for w, label in [
            (w_tgl, "Tanggal"), (w_jenis, "Jenis"), (w_kat, "Kategori"),
            (w_sys, "Sistem"), (w_man, "Manual"), (w_sel, "Selisih"),
        ]:
            pdf.cell(w, 5, label, border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", size=7)
        for _, row in by_type.iterrows():
            if pdf.get_y() > 275:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 7.5)
                pdf.set_x(pdf.l_margin)
                for w, label in [
                    (w_tgl, "Tanggal"), (w_jenis, "Jenis"), (w_kat, "Kategori"),
                    (w_sys, "Sistem"), (w_man, "Manual"), (w_sel, "Selisih"),
                ]:
                    pdf.cell(w, 5, label, border=1, align="C")
                pdf.ln()
                pdf.set_font("Helvetica", size=7)

            tgl = pd.to_datetime(row["tanggal"]).strftime("%d/%m/%Y")
            jenis = _latin(str(row.get("jenis", "")))[:24]
            kat = _latin(str(row.get("kategori", "")))[:12]
            pdf.set_x(pdf.l_margin)
            pdf.cell(w_tgl, 4.5, tgl, border=1)
            pdf.cell(w_jenis, 4.5, jenis, border=1)
            pdf.cell(w_kat, 4.5, kat, border=1)
            pdf.cell(w_sys, 4.5, fmt_qty(row.get("qty_sistem", 0)), border=1, align="R")
            pdf.cell(w_man, 4.5, fmt_qty(row.get("qty_manual", 0)), border=1, align="R")
            pdf.cell(w_sel, 4.5, fmt_qty(row.get("selisih", 0)), border=1, align="R")
            pdf.ln()

    pdf.ln(3)
    pdf.section_title("4. Tabel Harian")
    daily = result.get("daily", pd.DataFrame())
    if daily.empty:
        pdf.set_font("Helvetica", size=9)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, "Tidak ada data harian.", new_x="LMARGIN", new_y="NEXT")
    else:
        cols_show = [
            ("tanggal", "Tgl", 16),
            ("sistem_masuk", "S.Masuk", 18),
            ("sistem_keluar", "S.Keluar", 18),
            ("sistem_pindah_gudang", "S.PG", 16),
            ("manual_masuk", "M.Masuk", 18),
            ("manual_keluar", "M.Keluar", 18),
            ("manual_pindah_gudang", "M.PG", 16),
            ("selisih_netto", "Selisih", 16),
        ]
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_x(pdf.l_margin)
        for key, label, w in cols_show:
            pdf.cell(w, 4.5, label, border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", size=6.5)
        for _, row in daily.iterrows():
            if pdf.get_y() > 275:
                pdf.add_page()
                pdf.set_font("Helvetica", "B", 6.5)
                pdf.set_x(pdf.l_margin)
                for key, label, w in cols_show:
                    pdf.cell(w, 4.5, label, border=1, align="C")
                pdf.ln()
                pdf.set_font("Helvetica", size=6.5)
            pdf.set_x(pdf.l_margin)
            for key, label, w in cols_show:
                val = row.get(key, 0)
                if key == "tanggal":
                    txt = pd.to_datetime(val).strftime("%d/%m/%y")
                else:
                    txt = fmt_qty(val)
                pdf.cell(w, 4.2, txt, border=1, align="R" if key != "tanggal" else "C")
            pdf.ln()

    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    _safe_text(
        pdf,
        "Catatan: Qty negatif = keluar. Product Conversion positif = Hasil Produksi, "
        "negatif = Keluar Produksi. Pindah Gudang dipisah dari operasional.",
        4,
    )

    raw = pdf.output()
    return bytes(raw) if isinstance(raw, (bytes, bytearray)) else str(raw).encode("latin-1")


if HAS_FPDF:
    class _ReportPDF(FPDF):
        def section_title(self, title: str):
            self.set_x(self.l_margin)
            self.set_font("Helvetica", "B", 11)
            self.set_fill_color(15, 118, 110)
            self.set_text_color(255, 255, 255)
            usable = self.w - self.l_margin - self.r_margin
            self.cell(usable, 7, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
            self.ln(2)
