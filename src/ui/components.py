"""
Komponen UI — clean, responsif, highlight kesimpulan → detail.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional

from src.utils.formatting import fmt_qty


def show_header():
    st.markdown(
        """
        <div class="main-header">
            <div class="header-badge">STOCK TOOL</div>
            <h1>Stock Difference Checker</h1>
            <p>Bandingkan sistem vs manual · deteksi selisih · simpan sesi</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_summary_cards(summary: Dict[str, float]):
    s = summary

    def card(label: str, value: float, color_class: str = "neutral"):
        return f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value {color_class}">{fmt_qty(value)} Kg</div>
        </div>
        """

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(card("Saldo Awal (Manual)", s.get("saldo_awal_manual", 0)), unsafe_allow_html=True)
    with c2:
        st.markdown(card("Sistem Netto", s.get("sistem_netto", 0)), unsafe_allow_html=True)
    with c3:
        st.markdown(card("Manual Netto", s.get("manual_netto", 0)), unsafe_allow_html=True)
    with c4:
        selisih = s.get("selisih_netto", 0)
        color = "negative" if abs(selisih) > 0.001 else "positive"
        st.markdown(card("Selisih Netto", selisih, color), unsafe_allow_html=True)

    st.write("")
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown(card("Sistem Masuk", s.get("sistem_masuk", 0), "positive"), unsafe_allow_html=True)
    with c6:
        st.markdown(card("Sistem Keluar", s.get("sistem_keluar", 0), "negative"), unsafe_allow_html=True)
    with c7:
        st.markdown(card("Manual Masuk", s.get("manual_masuk", 0), "positive"), unsafe_allow_html=True)
    with c8:
        st.markdown(card("Manual Keluar", s.get("manual_keluar", 0), "negative"), unsafe_allow_html=True)

    st.write("")
    st.caption("Pindah Gudang (sudah dihitung di total, ditampilkan terpisah)")
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        st.markdown(card("Sys Transfer Masuk", s.get("sistem_transfer_masuk", 0)), unsafe_allow_html=True)
    with t2:
        st.markdown(card("Sys Transfer Keluar", s.get("sistem_transfer_keluar", 0)), unsafe_allow_html=True)
    with t3:
        st.markdown(card("Man Transfer Masuk", s.get("manual_transfer_masuk", 0)), unsafe_allow_html=True)
    with t4:
        st.markdown(card("Man Transfer Keluar", s.get("manual_transfer_keluar", 0)), unsafe_allow_html=True)


def show_daily_table(daily: pd.DataFrame):
    if daily.empty:
        st.info("Tidak ada data harian.")
        return

    df = daily.copy()
    if "tanggal" in df.columns:
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.strftime("%d/%m/%Y")

    rename_map = {
        "sistem_masuk": "Sistem Masuk",
        "sistem_keluar": "Sistem Keluar",
        "sistem_pindah_gudang": "Sistem Pindah Gudang",
        "manual_masuk": "Manual Masuk",
        "manual_keluar": "Manual Keluar",
        "manual_pindah_gudang": "Manual Pindah Gudang",
        "selisih_masuk": "Selisih Masuk",
        "selisih_keluar": "Selisih Keluar",
        "selisih_pindah_gudang": "Selisih Pindah Gudang",
        "selisih_netto": "Selisih Netto",
        "tanggal": "Tanggal",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    for col in df.select_dtypes(include="number").columns:
        df[col] = df[col].apply(fmt_qty)

    st.dataframe(df, use_container_width=True, height=min(420, 48 + len(df) * 36))


def show_insights(insights: dict):
    if not insights:
        return

    st.markdown("#### Kesimpulan Otomatis")
    st.info(insights.get("headline", ""))

    findings = insights.get("findings", [])
    if findings:
        st.markdown("**Temuan:**")
        for f in findings:
            st.markdown(f"- {f}")

    issues = insights.get("issue_dates") or []
    if issues:
        st.markdown("**Ringkasan tanggal bermasalah** — klik tanggal untuk filter detail:")
        cols = st.columns([2, 2, 1.2, 3, 1.2])
        cols[0].caption("Tanggal")
        cols[1].caption("Jenis")
        cols[2].caption("Qty")
        cols[3].caption("Keterangan")
        cols[4].caption("")

        for i, it in enumerate(issues):
            c0, c1, c2, c3, c4 = st.columns([2, 2, 1.2, 3, 1.2])
            c0.write(it.get("tanggal", ""))
            c1.write(it.get("jenis", ""))
            c2.write(fmt_qty(it.get("selisih", 0)))
            c3.write(it.get("keterangan", ""))
            # Ambil tanggal pertama untuk filter (bisa "01/10/2026 & 02/10/2026")
            raw_tgl = str(it.get("tanggal", "")).split("&")[0].strip().split("→")[0].strip()
            if c4.button("Lihat", key=f"see_issue_{i}", use_container_width=True):
                st.session_state["filter_tanggal"] = raw_tgl
                st.session_state["detail_tab"] = "manual"
                st.rerun()

    tips = insights.get("tips") or []
    if tips:
        with st.expander("Tips membaca selisih"):
            for tip in tips:
                st.markdown(f"- {tip}")


def show_detail_tabs(result: Dict[str, Any], filter_tanggal: Optional[str] = None):
    """Detail sistem & manual, opsional filter tanggal (dd/mm/yyyy)."""
    if filter_tanggal:
        st.success(f"Filter detail: **{filter_tanggal}**")
        if st.button("Hapus filter tanggal", key="clear_date_filter"):
            st.session_state["filter_tanggal"] = None
            st.rerun()

    tab1, tab2 = st.tabs(["Detail Sistem", "Detail Manual"])

    with tab1:
        df = result.get("sistem", pd.DataFrame())
        df = _apply_date_filter(df, filter_tanggal)
        if df.empty:
            st.warning("Tidak ada data sistem" + (f" untuk {filter_tanggal}" if filter_tanggal else "") + ".")
        else:
            show = df.copy()
            if "tanggal" in show.columns:
                show["tanggal"] = show["tanggal"].dt.strftime("%d/%m/%Y")
            cols = [c for c in ["tanggal", "jenis", "kategori", "grup", "no_dokumen", "qty", "saldo", "satuan"] if c in show.columns]
            show = show[cols]
            if "qty" in show.columns:
                show["qty"] = show["qty"].apply(fmt_qty)
            if "saldo" in show.columns:
                show["saldo"] = show["saldo"].apply(lambda x: fmt_qty(x) if pd.notna(x) else "")
            st.dataframe(show, use_container_width=True, height=360)

    with tab2:
        df = result.get("manual", pd.DataFrame())
        df = _apply_date_filter(df, filter_tanggal)
        if df.empty:
            st.warning("Tidak ada data manual" + (f" untuk {filter_tanggal}" if filter_tanggal else "") + ".")
        else:
            show = df.copy()
            if "tanggal" in show.columns:
                show["tanggal"] = show["tanggal"].dt.strftime("%d/%m/%Y")
            cols = [c for c in ["tanggal", "jenis", "kategori", "grup", "nama_produk", "kode_produk", "qty", "catatan"] if c in show.columns]
            show = show[cols]
            if "qty" in show.columns:
                show["qty"] = show["qty"].apply(fmt_qty)
            st.dataframe(show, use_container_width=True, height=360)


def _apply_date_filter(df: pd.DataFrame, filter_tanggal: Optional[str]) -> pd.DataFrame:
    if df.empty or not filter_tanggal or "tanggal" not in df.columns:
        return df
    try:
        # filter_tanggal: dd/mm/yyyy
        parts = filter_tanggal.replace("-", "/").split("/")
        if len(parts) == 3:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            mask = (
                (df["tanggal"].dt.day == d)
                & (df["tanggal"].dt.month == m)
                & (df["tanggal"].dt.year == y)
            )
            return df.loc[mask]
    except Exception:
        pass
    return df


def section_title(text: str, icon: str = ""):
    st.markdown(f'<div class="section-title">{icon} {text}</div>'.strip(), unsafe_allow_html=True)
