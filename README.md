# Stock Difference Checker

Aplikasi web untuk membandingkan selisih stok antara **data Sistem** (Gudang) dan **data Manual** (spreadsheet harian).

Dibuat dengan **Streamlit** + struktur multi-file agar mudah di-maintain dan dikembangkan.

---

## Fitur Utama

- Input data via **paste teks** (tidak wajib Excel)
- Parser otomatis
- Mapping otomatis
- Filter produk + rentang tanggal
- Ringkasan selisih (Masuk, Keluar, Netto)
- Tabel perbandingan harian
- Download hasil ke **Excel** dan **PDF**

---

## Cara Menjalankan

### 1. Install dependencies

```bash
cd stock_diff_app
pip install -r requirements.txt
```

### 2. Jalankan aplikasi

```bash
streamlit run app.py / python -m streamlit run app.py
```

Browser akan terbuka di `http://localhost:????`.

---

## Cara Pakai

1. Isi **Kode Produk** dan **Nama Produk** di sidebar.
2. Paste data ke 3 tab:
   - **Data Sistem** (format spasi/tab)
   - **Data Manual Masuk**
   - **Data Manual Keluar**
3. Klik **Preview Data** untuk melihat hasil parsing.
4. Klik **Bandingkan**.
5. Download hasil Excel / PDF.

---

## Catatan 

- **This application is currently under active development. Core features for stock opname reconciliation and inventory tracking are being continuously refined.**
