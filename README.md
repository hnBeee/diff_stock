# Stock Difference Checker

Aplikasi web untuk membandingkan selisih stok antara **data Sistem** (Gudang) dan **data Manual** (spreadsheet harian).

Dibuat dengan **Streamlit** + struktur multi-file agar mudah di-maintain dan dikembangkan.

---

## Fitur Utama

- Input data via **paste teks** (tidak wajib Excel)
- Parser otomatis untuk:
  - Data Sistem (spasi / tab)
  - Data Manual (dipisah `|`)
- Mapping otomatis **Product Conversion**:
  - Qty positif → Hasil Produksi (Masuk)
  - Qty negatif → Keluar Produksi (Keluar)
- Filter produk + rentang tanggal
- Ringkasan selisih (Masuk, Keluar, Netto)
- Tabel perbandingan harian
- Download hasil ke **Excel** dan **PDF**

---

## Struktur Folder

```
stock_diff_app/
├── app.py                  # Entry point Streamlit
├── requirements.txt
├── README.md
├── config/
│   └── settings.py         # Konfigurasi & mapping transaksi
├── src/
│   ├── parsers/
│   │   ├── system_parser.py
│   │   └── manual_parser.py
│   ├── processors/
│   │   └── comparator.py
│   ├── utils/
│   │   ├── cleaners.py
│   │   └── exporters.py
│   └── ui/
│       └── components.py
├── data/
│   └── samples/            # Contoh data
└── tests/
```

---

## Cara Menjalankan

### 1. Install dependencies

```bash
cd stock_diff_app
pip install -r requirements.txt
```

### 2. Jalankan aplikasi

```bash
streamlit run app.py
```

Browser akan terbuka di `http://localhost:8501`.

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

## Format Data yang Didukung

### Data Sistem
```
30/09/2026	Sales Delivery	13133	-19,94	88,579	Kg
30/09/2026	Product Conversion	21216	19,58	108,159	Kg
```

### Data Manual
```
| 01/10/2026 | Hasil Prod. | CUT BEEF RW 19 | BC.RW19 | 74,04 |
| 01/10/2026 | Jual        | CUT BEEF RW 19 | BC.RW19 | 61,42 |
```

---

## Pengembangan Selanjutnya

- [ ] Mapping transaksi yang bisa diedit lewat UI
- [ ] Multi-produk sekaligus
- [ ] Simpan histori perbandingan (database)
- [ ] OCR untuk foto tabel
- [ ] Login sederhana
- [ ] Deploy ke Streamlit Cloud

---

## Catatan Teknis

- Qty **Keluar** disimpan sebagai **negatif** untuk memudahkan perhitungan netto.
- Saldo Awal hanya diambil dari data Manual.
- Parser cukup toleran terhadap spasi berlebih dan format desimal koma/titik.
