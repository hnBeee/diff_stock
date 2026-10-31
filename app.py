"""
Stock Difference Checker — main entry.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from config.settings import (
    APP_TITLE,
    APP_ICON,
    APP_LAYOUT,
    DEFAULT_PRODUCT_CODE,
    DEFAULT_PRODUCT_NAME,
    SAMPLES_DIR,
)
from src.parsers.system_parser import parse_system_text, parse_system_with_diag
from src.parsers.manual_parser import parse_manual_text, parse_manual_with_diag
from src.processors.comparator import prepare_comparison
from src.processors.insights import generate_insights
from src.utils.exporters import to_excel_bytes, to_pdf_bytes
from src.utils.session_store import (
    save_session,
    load_session,
    list_sessions,
    delete_session,
)
from src.utils.formatting import fmt_qty
from src.ui.components import (
    show_header,
    show_summary_cards,
    show_daily_table,
    show_detail_tabs,
    show_insights,
    section_title,
)
from src.ui.styles import CUSTOM_CSS

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=APP_LAYOUT,
    initial_sidebar_state="auto",
)



def load_sample(filename: str) -> str:
    path = SAMPLES_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _extract_product_options(df_masuk, df_keluar):
    import pandas as pd
    frames = [f for f in [df_masuk, df_keluar] if f is not None and not f.empty]
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True)
    if "kode_produk" not in df.columns:
        df["kode_produk"] = ""
    if "nama_produk" not in df.columns:
        df["nama_produk"] = ""
    df["kode_produk"] = df["kode_produk"].fillna("").astype(str).str.strip()
    df["nama_produk"] = df["nama_produk"].fillna("").astype(str).str.strip()
    grouped = (
        df.groupby(["kode_produk", "nama_produk"], dropna=False)
        .size()
        .reset_index(name="n")
        .sort_values(["kode_produk", "nama_produk"])
    )
    return [
        {"kode": r.kode_produk, "nama": r.nama_produk, "n": int(r.n)}
        for r in grouped.itertuples()
    ]


def _show_parsed_preview(df, sistem=False):
    if df is None or df.empty:
        st.caption("Kosong")
        return
    cols = ["tanggal", "jenis", "kategori", "qty"]
    if sistem:
        for c in ["no_dokumen", "saldo", "_peringatan"]:
            if c in df.columns:
                cols.append(c)
    else:
        for c in ["kode_produk", "nama_produk"]:
            if c in df.columns:
                cols.append(c)
    if "_baris_sumber" in df.columns:
        cols = ["_baris_sumber"] + cols
    show = df[[c for c in cols if c in df.columns]].head(15).copy()
    if "tanggal" in show.columns:
        show["tanggal"] = show["tanggal"].dt.strftime("%d/%m/%Y")
    if "qty" in show.columns:
        show["qty"] = show["qty"].apply(fmt_qty)
    if "saldo" in show.columns:
        show["saldo"] = show["saldo"].apply(lambda x: fmt_qty(x) if x is not None and str(x) not in ("", "nan", "None") else "")
    if "_baris_sumber" in show.columns:
        show = show.rename(columns={"_baris_sumber": "baris"})
    if "_peringatan" in show.columns:
        show = show.rename(columns={"_peringatan": "peringatan"})
    st.dataframe(show, use_container_width=True, height=260)
    # Ringkas peringatan
    if sistem and "_peringatan" in df.columns:
        n_warn = int((df["_peringatan"].astype(str).str.len() > 0).sum())
        if n_warn:
            st.error(f"{n_warn} baris sistem punya peringatan — jangan Bandingkan sebelum dicek.")


def main():
    # --- Muat sesi tertunda (sebelum widget dibuat) ---
    pending = st.session_state.pop("pending_session_path", None)
    if pending:
        try:
            data = load_session(Path(pending))
            st.session_state["input_sistem"] = data.get("raw_sistem", "")
            st.session_state["input_masuk"] = data.get("raw_masuk", "")
            st.session_state["input_keluar"] = data.get("raw_keluar", "")
            st.session_state["raw_sistem"] = data.get("raw_sistem", "")
            st.session_state["raw_masuk"] = data.get("raw_masuk", "")
            st.session_state["raw_keluar"] = data.get("raw_keluar", "")
            st.session_state["product_code_manual"] = data.get("product_code", "")
            st.session_state["product_name_manual"] = data.get("product_name", "")
            st.session_state["product_code"] = data.get("product_code", "")
            st.session_state["product_name"] = data.get("product_name", "")
            for k in ("last_result", "last_insights", "filter_tanggal",
                      "df_sistem", "df_masuk", "df_keluar", "product_options"):
                st.session_state.pop(k, None)
            st.session_state["_toast_load"] = f"Sesi dimuat: {Path(pending).name}"
        except Exception as e:
            st.session_state["_toast_load_err"] = str(e)

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    show_header()
    _msg = st.session_state.pop("_toast_load", None)
    if _msg:
        st.success(_msg)
    _err = st.session_state.pop("_toast_load_err", None)
    if _err:
        st.error(f"Gagal muat sesi: {_err}")

    # ---------- SIDEBAR ----------
    with st.sidebar:
        st.markdown("### Filter Produk (Manual)")
        st.caption(
            "Pilih dari data Manual yang sudah di-paste. "
            "Data Sistem tidak difilter (biasanya sudah per produk)."
        )
        # Opsi produk diisi setelah parse; pakai session
        product_options = st.session_state.get("product_options", [])
        if product_options:
            labels = ["(Semua produk manual)"] + [
                f"{o['kode']} — {o['nama']}" if o.get("kode") or o.get("nama") else "(tanpa kode)"
                for o in product_options
            ]
            pick = st.selectbox("Produk dari data Manual", options=range(len(labels)), format_func=lambda i: labels[i])
            if pick == 0:
                product_code = ""
                product_name = ""
                st.session_state["filter_mode"] = "all"
            else:
                sel = product_options[pick - 1]
                product_code = sel.get("kode") or ""
                product_name = sel.get("nama") or ""
                st.session_state["filter_mode"] = "one"
        else:
            st.info("Paste data Manual lalu Preview/Bandingkan agar daftar produk muncul.")
            product_code = st.session_state.get("product_code", "")
            product_name = st.session_state.get("product_name", "")

        product_code = st.text_input(
            "Atau ketik kode produk",
            value=product_code,
            key="product_code_manual",
            help="Filter ketat ke kode ini pada data Manual",
        )
        product_name = st.text_input(
            "Atau ketik nama produk",
            value=product_name,
            key="product_name_manual",
            help="Filter jika mengandung teks nama ini",
        )
        st.session_state["product_code"] = product_code
        st.session_state["product_name"] = product_name

        st.divider()
        st.markdown("### Filter Tanggal")
        use_date_filter = st.checkbox("Aktifkan filter tanggal", value=False)
        date_from = date_to = None
        if use_date_filter:
            date_from = st.date_input("Dari", value=datetime(2026, 9, 30))
            date_to = st.date_input("Sampai", value=datetime(2026, 10, 21))
            date_from = datetime.combine(date_from, datetime.min.time())
            date_to = datetime.combine(date_to, datetime.max.time())

        st.divider()
        st.markdown("### Sesi")
        session_label = st.text_input("Nama sesi (opsional)", placeholder="mis. BC.TR Oktober")
        if st.button("Simpan sesi sekarang", use_container_width=True):
            path = save_session(
                product_code=product_code,
                product_name=product_name,
                raw_sistem=st.session_state.get("input_sistem") or st.session_state.get("raw_sistem", ""),
                raw_masuk=st.session_state.get("input_masuk") or st.session_state.get("raw_masuk", ""),
                raw_keluar=st.session_state.get("input_keluar") or st.session_state.get("raw_keluar", ""),
                label=session_label or None,
                summary=(st.session_state.get("last_result") or {}).get("summary"),
            )
            st.success(f"Tersimpan: {path.name}")

        sessions = list_sessions(20)
        if not sessions:
            st.caption("Belum ada sesi. Klik Simpan sesi setelah paste data.")
        if sessions:
            labels = {
                s["path"]: f"{s['label']} · {s.get('product_code','')} · {str(s.get('saved_at',''))[:16]}"
                for s in sessions
            }
            choice = st.selectbox(
                "Muat sesi",
                options=[""] + list(labels.keys()),
                format_func=lambda p: labels.get(p, "— pilih —") if p else "— pilih —",
            )
            c_load, c_del = st.columns(2)
            with c_load:
                if st.button("Muat", use_container_width=True, disabled=not choice):
                    # Jangan set key widget di sini — tunda ke awal main (sebelum text_area)
                    st.session_state["pending_session_path"] = choice
                    st.rerun()
            with c_del:
                if st.button("Hapus", use_container_width=True, disabled=not choice):
                    delete_session(Path(choice))
                    st.rerun()

        st.divider()
        st.markdown("### Sample")
        if st.button("Load Sample Data", use_container_width=True):
            st.session_state["input_sistem"] = load_sample("sistem_sample.txt")
            st.session_state["input_masuk"] = load_sample("manual_masuk_sample.txt")
            st.session_state["input_keluar"] = load_sample("manual_keluar_sample.txt")
            st.session_state["raw_sistem"] = st.session_state["input_sistem"]
            st.session_state["raw_masuk"] = st.session_state["input_masuk"]
            st.session_state["raw_keluar"] = st.session_state["input_keluar"]
            st.rerun()

        st.divider()
        st.caption("Tema: menu ⋮ kanan atas → Settings → Theme")
        st.caption("Sidebar tertutup? Klik tombol hijau di tepi kiri.")

    # ---------- INPUT ----------
    section_title("1. Input Data")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Load Sample", use_container_width=True):
            st.session_state["input_sistem"] = load_sample("sistem_sample.txt")
            st.session_state["input_masuk"] = load_sample("manual_masuk_sample.txt")
            st.session_state["input_keluar"] = load_sample("manual_keluar_sample.txt")
            st.session_state["raw_sistem"] = st.session_state["input_sistem"]
            st.session_state["raw_masuk"] = st.session_state["input_masuk"]
            st.session_state["raw_keluar"] = st.session_state["input_keluar"]
            st.rerun()
    with b2:
        if st.button("Hapus Semua", use_container_width=True):
            for k in list(st.session_state.keys()):
                if (
                    k.startswith("raw_")
                    or k.startswith("df_")
                    or k.startswith("input_")
                    or k.startswith("skip_")
                    or k in (
                        "last_result", "last_insights", "filter_tanggal",
                        "product_options",
                    )
                ):
                    del st.session_state[k]
            st.session_state["input_sistem"] = ""
            st.session_state["input_masuk"] = ""
            st.session_state["input_keluar"] = ""
            st.rerun()
    with b3:
        if st.button("Simpan Sesi", use_container_width=True, type="secondary"):
            path = save_session(
                product_code=product_code,
                product_name=product_name,
                raw_sistem=st.session_state.get("input_sistem") or st.session_state.get("raw_sistem", ""),
                raw_masuk=st.session_state.get("input_masuk") or st.session_state.get("raw_masuk", ""),
                raw_keluar=st.session_state.get("input_keluar") or st.session_state.get("raw_keluar", ""),
                label=session_label or None,
                summary=(st.session_state.get("last_result") or {}).get("summary"),
            )
            st.toast(f"Sesi disimpan: {path.name}")

    # Inisialisasi key widget jika belum ada
    for _k in ("input_sistem", "input_masuk", "input_keluar"):
        if _k not in st.session_state:
            st.session_state[_k] = st.session_state.get(_k.replace("input_", "raw_"), "")

    tab_s, tab_m, tab_k = st.tabs(["Data Sistem", "Manual Masuk", "Manual Keluar"])
    with tab_s:
        st.caption("Format: Tanggal · Jenis · NoDok · Qty  (spasi/tab, saldo opsional)")
        raw_sistem = st.text_area(
            "sistem", height=200,
            key="input_sistem", label_visibility="collapsed",
        )
        st.session_state["raw_sistem"] = raw_sistem
    with tab_m:
        st.caption("Format bebas: spasi / tab / |  → Tanggal Jenis Nama Kode Qty")
        raw_masuk = st.text_area(
            "masuk", height=200,
            key="input_masuk", label_visibility="collapsed",
        )
        st.session_state["raw_masuk"] = raw_masuk
    with tab_k:
        st.caption("Format bebas: spasi / tab / |  → Tanggal Jenis Nama Kode Qty")
        raw_keluar = st.text_area(
            "keluar", height=200,
            key="input_keluar", label_visibility="collapsed",
        )
        st.session_state["raw_keluar"] = raw_keluar

    st.write("")
    col_a, col_b = st.columns(2)
    with col_a:
        preview_clicked = st.button("Preview Data", use_container_width=True)
    with col_b:
        compare_clicked = st.button("Bandingkan", type="primary", use_container_width=True)

    # ---------- PREVIEW ----------
    if preview_clicked or compare_clicked:
        with st.spinner("Membaca data..."):
            df_sistem, skip_sys = parse_system_with_diag(raw_sistem, product_code, product_name)
            df_masuk, skip_masuk = parse_manual_with_diag(raw_masuk, default_kategori="Masuk")
            df_keluar, skip_keluar = parse_manual_with_diag(raw_keluar, default_kategori="Keluar")

        # Daftar produk unik dari manual (untuk filter sidebar)
        product_options = _extract_product_options(df_masuk, df_keluar)
        st.session_state["product_options"] = product_options

        section_title("2. Audit Parsing (akurasi data)")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Sistem OK", len(df_sistem))
        m2.metric("Manual Masuk OK", len(df_masuk))
        m3.metric("Manual Keluar OK", len(df_keluar))
        total_skip = len(skip_sys) + len(skip_masuk) + len(skip_keluar)
        m4.metric("Baris dilewati", total_skip)

        if total_skip > 0:
            st.warning(
                f"{total_skip} baris tidak diambil program. Buka expander di bawah untuk detail — "
                "penting dicek agar tidak ada data yang terlewat."
            )

        with st.expander("Baris yang BERHASIL dibaca", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.caption("Sistem")
                _show_parsed_preview(df_sistem, sistem=True)
            with c2:
                st.caption("Manual Masuk")
                _show_parsed_preview(df_masuk)
            with c3:
                st.caption("Manual Keluar")
                _show_parsed_preview(df_keluar)

        with st.expander("Baris yang DILEWATI / gagal dibaca", expanded=total_skip > 0):
            if total_skip == 0:
                st.success("Semua baris berhasil dibaca.")
            else:
                import pandas as pd
                rows = []
                for src, skips in [("Sistem", skip_sys), ("Manual Masuk", skip_masuk), ("Manual Keluar", skip_keluar)]:
                    for s in skips:
                        rows.append({"Sumber": src, "Baris": s["baris"], "Teks": s["teks"], "Alasan": s["alasan"]})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, height=min(280, 40 + total_skip * 28))

        if df_sistem.empty and df_masuk.empty and df_keluar.empty:
            st.error("Tidak ada data yang terbaca. Periksa format paste.")
            return

        st.session_state["df_sistem"] = df_sistem
        st.session_state["df_masuk"] = df_masuk
        st.session_state["df_keluar"] = df_keluar
        st.session_state["skip_sys"] = skip_sys
        st.session_state["skip_masuk"] = skip_masuk
        st.session_state["skip_keluar"] = skip_keluar

    # ---------- COMPARE ----------
    if compare_clicked:
        with st.spinner("Menghitung selisih..."):
            df_sistem, skip_sys = parse_system_with_diag(raw_sistem, product_code, product_name)
            df_masuk, skip_masuk = parse_manual_with_diag(raw_masuk, default_kategori="Masuk")
            df_keluar, skip_keluar = parse_manual_with_diag(raw_keluar, default_kategori="Keluar")
            st.session_state["product_options"] = _extract_product_options(df_masuk, df_keluar)
            st.session_state["skip_sys"] = skip_sys
            st.session_state["skip_masuk"] = skip_masuk
            st.session_state["skip_keluar"] = skip_keluar

        if df_sistem.empty and df_masuk.empty and df_keluar.empty:
            st.error("Tidak ada data yang terbaca.")
            return

        result = prepare_comparison(
            df_sistem=df_sistem,
            df_manual_masuk=df_masuk,
            df_manual_keluar=df_keluar,
            product_code=product_code,
            product_name=product_name,
            date_from=date_from,
            date_to=date_to,
        )
        insights = generate_insights(result)
        st.session_state["last_result"] = result
        st.session_state["last_insights"] = insights

        # Auto-simpan sesi ringan (tanpa mengganggu)
        try:
            save_session(
                product_code=product_code,
                product_name=product_name,
                raw_sistem=raw_sistem,
                raw_masuk=raw_masuk,
                raw_keluar=raw_keluar,
                label=session_label or f"auto_{product_code}_{datetime.now().strftime('%H%M')}",
                summary=result.get("summary"),
            )
        except Exception:
            pass

    # Tampilkan hasil jika ada di session
    if "last_result" in st.session_state:
        result = st.session_state["last_result"]
        insights = st.session_state.get("last_insights") or generate_insights(result)

        section_title("3. Hasil Perbandingan")
        show_summary_cards(result["summary"])

        st.markdown("#### Tabel Perbandingan Harian")
        show_daily_table(result["daily"])

        show_insights(insights)

        # Produk manual yang tidak masuk filter
        excl = result.get("manual_excluded")
        if excl is not None and not excl.empty:
            st.warning(
                f"{len(excl)} baris Manual **tidak ikut dihitung** karena di luar filter produk "
                f"(kode/nama). Buka daftar di bawah agar tidak ada yang terlewat tanpa sengaja."
            )
            with st.expander("Manual di luar filter produk (tidak dihitung)"):
                show = excl.copy()
                if "tanggal" in show.columns:
                    show["tanggal"] = show["tanggal"].dt.strftime("%d/%m/%Y")
                cols = [c for c in ["tanggal", "jenis", "kode_produk", "nama_produk", "qty"] if c in show.columns]
                if "qty" in show.columns:
                    show["qty"] = show["qty"].apply(fmt_qty)
                st.dataframe(show[cols], use_container_width=True, height=220)

        st.markdown("#### Detail Transaksi")
        filter_tgl = st.session_state.get("filter_tanggal")
        show_detail_tabs(result, filter_tanggal=filter_tgl)

        section_title("4. Download")
        d1, d2 = st.columns(2)
        with d1:
            try:
                excel_bytes = to_excel_bytes(result, product_code, insights)
                st.download_button(
                    "Download Excel",
                    data=excel_bytes,
                    file_name=f"selisih_{product_code}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Gagal buat Excel: {e}")
        with d2:
            try:
                pdf_bytes = to_pdf_bytes(result, product_code, product_name, insights)
                st.download_button(
                    "Download PDF",
                    data=pdf_bytes,
                    file_name=f"selisih_{product_code}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Gagal buat PDF: {e}")
                st.caption("Excel tetap bisa diunduh. Coba Bandingkan ulang setelah update.")


if __name__ == "__main__":
    main()
