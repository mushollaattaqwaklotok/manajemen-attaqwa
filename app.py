# app.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

# =====================================================
#  KONFIGURASI AWAL
# =====================================================
BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_KEU = UPLOADS_DIR / "keuangan"
UPLOADS_BAR = UPLOADS_DIR / "barang"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(UPLOADS_KEU, exist_ok=True)
os.makedirs(UPLOADS_BAR, exist_ok=True)

FILE_KEUANGAN = DATA_DIR / "keuangan.csv"
FILE_BARANG = DATA_DIR / "barang.csv"
FILE_LOG = DATA_DIR / "log_aktivitas.csv"

# Jika belum ada CSV, buat header minimal
if not FILE_KEUANGAN.exists():
    pd.DataFrame(columns=["Tanggal","Keterangan","Kategori","Masuk","Keluar","Saldo","bukti_url"]).to_csv(FILE_KEUANGAN, index=False)
if not FILE_BARANG.exists():
    pd.DataFrame(columns=["tanggal","jenis","keterangan","jumlah","satuan","bukti","bukti_penerimaan"]).to_csv(FILE_BARANG, index=False)
if not FILE_LOG.exists():
    pd.DataFrame(columns=["Waktu","User","Aktivitas"]).to_csv(FILE_LOG, index=False)

# -----------------------------------------------------
# Konfigurasi akun panitia (bisa diubah sesuai kebutuhan)
# -----------------------------------------------------
PANITIA = {
    "ketua": "kelas3ku",
    "sekretaris": "fatik3762",
    "bendahara 1": "hadi5028",
    "bendahara 2": "riki6522",
    "koor donasi 1": "bayu0255",
    "koor donasi 2": "roni9044"
}

# =====================================================
#  UI PREMIUM – Styling
# =====================================================
st.set_page_config(page_title="Manajemen At-Taqwa", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #f4f7f5 !important; }
h1,h2,h3,h4 { color:#0b6e4f !important; font-weight:800; }
.header-box {
    background: linear-gradient(90deg,#0b6e4f,#18a36d);
    padding:22px 26px; border-radius:14px;
    color:white !important; margin-bottom:16px;
}
.header-title { font-size:30px; font-weight:900; }
.header-sub { opacity:.85; margin-top:-6px; }
section[data-testid="stSidebar"] { background:#0b6e4f; padding:20px; }
section[data-testid="stSidebar"] * { color:white !important; }
.stButton>button {
    background: linear-gradient(90deg,#0b6e4f,#18a36d);
    color:white !important; font-weight:700;
    padding:8px 22px; border-radius:10px;
}
.stButton>button:hover { background: linear-gradient(90deg,#18a36d,#0b6e4f); transform:scale(1.03); }
input, textarea, select { border-radius:10px !important; border:1px solid #0b6e4f !important; }
.infocard { background:white; border-radius:14px; padding:18px; text-align:center; border:1px solid #d9e9dd; margin-bottom:15px; }
.infocard h3 { margin:4px 0; font-size:20px; }
.infocard p { margin:0; font-weight:700; font-size:18px; }
.dataframe th { background:#0b6e4f !important; color:white !important; padding:8px !important; }
.dataframe td { padding:6px !important; border:1px solid #c8e6d3 !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================
#  UTIL FUNCTIONS
# =====================================================
def read_csv_safe(path, dtype_cols=None):
    try:
        if path.exists():
            df = pd.read_csv(path)
        else:
            df = pd.DataFrame()
    except Exception:
        df = pd.DataFrame()
    if dtype_cols:
        for col, dtype in dtype_cols.items():
            if col not in df.columns:
                df[col] = pd.Series(dtype=dtype)
    return df

def save_csv(df, path):
    df.to_csv(path, index=False)

def sanitize_amount(x):
    """Aman konversi ke int untuk field numeric; kembalikan 0 jika gagal."""
    try:
        if pd.isna(x) or x == "":
            return 0
        return int(float(x))
    except Exception:
        return 0

def parse_date_safe(s):
    """Kembalikan string tanggal 'YYYY-MM-DD' jika bisa, atau today jika gagal."""
    try:
        d = pd.to_datetime(s, errors='coerce')
        if pd.isna(d):
            return datetime.now().strftime("%Y-%m-%d")
        return d.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

def preview_link(url):
    if pd.isna(url) or url == "" or url is None:
        return "-"
    # gunakan path relatif
    return f"<a href='{url}' target='_blank'>Lihat Bukti</a>"

def log_activity(user, activity):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_log = read_csv_safe(FILE_LOG)
    new = pd.DataFrame([[t, user, activity]], columns=["Waktu","User","Aktivitas"])
    df_log = pd.concat([df_log, new], ignore_index=True)
    save_csv(df_log, FILE_LOG)

def save_uploaded_file(uploaded, dest_folder: Path):
    """Simpan file uploader Streamlit ke dest_folder dan kembalikan path string relatif."""
    if uploaded is None:
        return ""
    safe_name = uploaded.name
    dest = dest_folder / safe_name
    # jika file exists, tambahkan timestamp supaya tidak overwrite
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        dest = dest_folder / f"{stem}_{ts}{suffix}"
    with open(dest, "wb") as f:
        f.write(uploaded.getbuffer())
    # return path as string (relative)
    return str(dest)

# =====================================================
#  LOAD DATA
# =====================================================
df_keu = read_csv_safe(FILE_KEUANGAN, dtype_cols={
    "Tanggal": str, "Keterangan": str, "Kategori": str,
    "Masuk": float, "Keluar": float, "Saldo": float, "bukti_url": str
})
# pastikan kolom ada dan tipe numeric aman
for col in ["Masuk", "Keluar", "Saldo"]:
    if col not in df_keu.columns:
        df_keu[col] = 0
df_keu["Masuk"] = pd.to_numeric(df_keu["Masuk"], errors="coerce").fillna(0).astype(float)
df_keu["Keluar"] = pd.to_numeric(df_keu["Keluar"], errors="coerce").fillna(0).astype(float)
# jika saldo ada, buat ulang untuk konsistensi
if len(df_keu) > 0:
    df_keu["Saldo"] = df_keu["Masuk"].cumsum() - df_keu["Keluar"].cumsum()

df_barang = read_csv_safe(FILE_BARANG, dtype_cols={
    "tanggal": str, "jenis": str, "keterangan": str, "jumlah": float, "satuan": str, "bukti": str, "bukti_penerimaan": str
})
for col in ["jumlah"]:
    if col not in df_barang.columns:
        df_barang[col] = 0
df_barang["jumlah"] = pd.to_numeric(df_barang["jumlah"], errors="coerce").fillna(0).astype(float)

df_log = read_csv_safe(FILE_LOG)

# =====================================================
#  HEADER
# =====================================================
st.markdown("""
<div class="header-box">
    <div class="header-title">Laporan Keuangan Musholla At-Taqwa</div>
    <div class="header-sub">Transparansi • Amanah • Profesional</div>
</div>
""", unsafe_allow_html=True)

# =====================================================
#  LOGIN SIDEBAR
# =====================================================
st.sidebar.header("Login sebagai:")
level = st.sidebar.radio("", [
    "Publik",
    "Ketua",
    "Sekretaris",
    "Bendahara 1",
    "Bendahara 2",
    "Koor Donasi 1",
    "Koor Donasi 2"
])

if level != "Publik":
    password = st.sidebar.text_input("Password:", type="password")
    key = level.lower()
    if key not in PANITIA or password != PANITIA[key]:
        st.warning("🔒 Masukkan password yang benar.")
        st.stop()

menu = st.sidebar.radio("Menu:", ["💰 Keuangan", "📦 Barang Masuk", "📄 Laporan", "🧾 Log"])

# =====================================================
#  SESSION STATE FOR EDITS
# =====================================================
if "edit_keu_idx" not in st.session_state:
    st.session_state.edit_keu_idx = None
if "edit_barang_idx" not in st.session_state:
    st.session_state.edit_barang_idx = None

# =====================================================
#  MENU: KEUANGAN
# =====================================================
if menu == "💰 Keuangan":
    st.header("💰 Keuangan")

    # DASHBOARD CARDS
    if len(df_keu) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='infocard'><h3>Total Masuk</h3><p>Rp {int(df_keu['Masuk'].sum()):,}</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='infocard'><h3>Total Keluar</h3><p>Rp {int(df_keu['Keluar'].sum()):,}</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='infocard'><h3>Saldo Akhir</h3><p>Rp {int(df_keu['Saldo'].iloc[-1]) if len(df_keu)>0 else 0:,}</p></div>", unsafe_allow_html=True)

    # EDIT MODE (Hanya Ketua boleh edit)
    if level == "Ketua" and st.session_state.edit_keu_idx is not None:
        idx = st.session_state.edit_keu_idx
        try:
            row = df_keu.iloc[idx]
        except Exception:
            st.error("Baris tidak tersedia.")
            st.session_state.edit_keu_idx = None
            st.experimental_rerun()

        st.subheader("✏️ Edit Data Keuangan (Ketua)")
        # tanggal safe: jika format buruk, pakai today
        tgl_default = parse_date_safe(row.get("Tanggal", ""))
        tgl_e = st.date_input("Tanggal", value=pd.to_datetime(tgl_default).date())
        ket_e = st.text_input("Keterangan", value=row.get("Keterangan", ""))
        kategori_e = st.selectbox("Kategori", ["Kas Masuk", "Kas Keluar"], index=0 if str(row.get("Kategori",""))=="Kas Masuk" else 1)
        masuk_val = sanitize_amount(row.get("Masuk", 0))
        keluar_val = sanitize_amount(row.get("Keluar", 0))
        masuk_e = st.number_input("Masuk (Rp)", min_value=0, value=masuk_val)
        keluar_e = st.number_input("Keluar (Rp)", min_value=0, value=keluar_val)
        bukti_e = st.file_uploader("Ganti Bukti (opsional)")

        if st.button("💾 Simpan Perubahan"):
            # simpan file bukti jika ada
            bukti_path = row.get("bukti_url", "")
            if bukti_e:
                bukti_path = save_uploaded_file(bukti_e, UPLOADS_KEU)
                log_activity(level, f"Upload bukti keuangan: {bukti_path}")

            # update dataframe
            df_keu.at[idx, "Tanggal"] = str(pd.to_datetime(tgl_e).date())
            df_keu.at[idx, "Keterangan"] = ket_e
            df_keu.at[idx, "Kategori"] = kategori_e
            df_keu.at[idx, "Masuk"] = float(masuk_e)
            df_keu.at[idx, "Keluar"] = float(keluar_e)
            df_keu.at[idx, "bukti_url"] = bukti_path

            # rekalkulasi saldo secara cumulative
            df_keu["Masuk"] = pd.to_numeric(df_keu["Masuk"], errors="coerce").fillna(0)
            df_keu["Keluar"] = pd.to_numeric(df_keu["Keluar"], errors="coerce").fillna(0)
            df_keu["Saldo"] = df_keu["Masuk"].cumsum() - df_keu["Keluar"].cumsum()

            save_csv(df_keu, FILE_KEUANGAN)
            log_activity(level, f"Edit data keuangan index {idx}")
            st.success("Perubahan tersimpan.")
            st.session_state.edit_keu_idx = None
            st.experimental_rerun()

        if st.button("Batal"):
            st.session_state.edit_keu_idx = None
            st.experimental_rerun()

    # INPUT DATA (untuk panitia selain publik)
    st.subheader("Input Keuangan")
    if level == "Publik":
        st.info("🔒 Hanya panitia yang dapat input data.")
        if len(df_keu) > 0:
            st.download_button("⬇️ Download Laporan Keuangan (CSV)", df_keu.to_csv(index=False).encode("utf-8"), "laporan_keuangan.csv", mime="text/csv")
    else:
        tgl = st.date_input("Tanggal")
        ket = st.text_input("Keterangan")
        kategori = st.selectbox("Kategori", ["Kas Masuk", "Kas Keluar"])
        masuk = st.number_input("Masuk (Rp)", min_value=0)
        keluar = st.number_input("Keluar (Rp)", min_value=0)
        bukti = st.file_uploader("Upload Bukti (pdf/jpg/png)")

        if st.button("Simpan Data"):
            bukti_path = ""
            if bukti:
                bukti_path = save_uploaded_file(bukti, UPLOADS_KEU)
                log_activity(level, f"Upload bukti keuangan: {bukti_path}")

            # saldo akhir: jika df kosong -> 0
            last_saldo = float(df_keu["Saldo"].iloc[-1]) if len(df_keu) else 0.0
            saldo_akhir = last_saldo + float(masuk) - float(keluar)

            new_row = {
                "Tanggal": str(pd.to_datetime(tgl).date()),
                "Keterangan": ket,
                "Kategori": kategori,
                "Masuk": float(masuk),
                "Keluar": float(keluar),
                "Saldo": float(saldo_akhir),
                "bukti_url": bukti_path
            }
            df_keu = pd.concat([df_keu, pd.DataFrame([new_row])], ignore_index=True)
            # rekalkulasi ulang untuk konsistensi
            df_keu["Masuk"] = pd.to_numeric(df_keu["Masuk"], errors="coerce").fillna(0)
            df_keu["Keluar"] = pd.to_numeric(df_keu["Keluar"], errors="coerce").fillna(0)
            df_keu["Saldo"] = df_keu["Masuk"].cumsum() - df_keu["Keluar"].cumsum()

            save_csv(df_keu, FILE_KEUANGAN)
            log_activity(level, "Input data keuangan baru")
            st.success("Data berhasil disimpan!")

    # TABEL KEUANGAN + tombol edit utk Ketua
    st.subheader("Tabel Laporan Keuangan")
    if len(df_keu) > 0:
        df_show = df_keu.copy()
        df_show["Bukti"] = df_show["bukti_url"].apply(preview_link)
        # tampilkan baris per baris agar tombol edit terpisah
        for i in range(len(df_show)):
            row_html = df_show.iloc[[i]].to_html(escape=False)
            colA, colB = st.columns([6,1])
            with colA:
                st.markdown(row_html, unsafe_allow_html=True)
            with colB:
                if level == "Ketua":
                    if st.button("✏️ Edit", key=f"keu_edit_{i}"):
                        st.session_state.edit_keu_idx = i
                        st.experimental_rerun()
    else:
        st.info("Belum ada data keuangan.")


# =====================================================
#  MENU: BARANG MASUK
# =====================================================
elif menu == "📦 Barang Masuk":
    st.header("📦 Barang Masuk")

    # MODE EDIT BARANG (Ketua)
    if level == "Ketua" and st.session_state.edit_barang_idx is not None:
        idx = st.session_state.edit_barang_idx
        try:
            row = df_barang.iloc[idx]
        except Exception:
            st.error("Baris barang tidak tersedia.")
            st.session_state.edit_barang_idx = None
            st.experimental_rerun()

        st.subheader("✏️ Edit Data Barang (Ketua)")
        tgl_b_default = parse_date_safe(row.get("tanggal",""))
        tgl_b = st.date_input("Tanggal Barang", value=pd.to_datetime(tgl_b_default).date())
        jenis_b = st.text_input("Jenis Barang", value=row.get("jenis",""))
        ket_b = st.text_input("Keterangan", value=row.get("keterangan",""))
        jumlah_val = sanitize_amount(row.get("jumlah",0))
        jml_b = st.number_input("Jumlah", min_value=0, value=jumlah_val)
        satuan_b = st.text_input("Satuan", value=row.get("satuan",""))
        bukti_b = st.file_uploader("Ganti Bukti Penerimaan (opsional)")

        if st.button("💾 Simpan Perubahan Barang"):
            bukti_path = row.get("bukti", "")
            if bukti_b:
                bukti_path = save_uploaded_file(bukti_b, UPLOADS_BAR)
                log_activity(level, f"Upload bukti barang: {bukti_path}")

            df_barang.at[idx, "tanggal"] = str(pd.to_datetime(tgl_b).date())
            df_barang.at[idx, "jenis"] = jenis_b
            df_barang.at[idx, "keterangan"] = ket_b
            df_barang.at[idx, "jumlah"] = float(jml_b)
            df_barang.at[idx, "satuan"] = satuan_b
            df_barang.at[idx, "bukti"] = bukti_path
            df_barang.at[idx, "bukti_penerimaan"] = bukti_path

            save_csv(df_barang, FILE_BARANG)
            log_activity(level, f"Edit data barang index {idx}")
            st.success("Perubahan barang tersimpan.")
            st.session_state.edit_barang_idx = None
            st.experimental_rerun()

        if st.button("Batal"):
            st.session_state.edit_barang_idx = None
            st.experimental_rerun()

    # INPUT BARANG
    st.subheader("Input Barang Masuk")
    if level == "Publik":
        st.info("🔒 Hanya panitia yang dapat input data.")
        if len(df_barang) > 0:
            st.download_button("⬇️ Download Data Barang (CSV)", df_barang.to_csv(index=False).encode("utf-8"), "barang_masuk.csv", mime="text/csv")
    else:
        tgl_b = st.date_input("Tanggal Barang")
        jenis_b = st.text_input("Jenis Barang")
        ket_b = st.text_input("Keterangan")
        jml_b = st.number_input("Jumlah", min_value=0)
        satuan_b = st.text_input("Satuan")
        bukti_b = st.file_uploader("Upload Bukti Penerimaan (pdf/jpg/png)")

        if st.button("Simpan Barang"):
            bukti_path = ""
            if bukti_b:
                bukti_path = save_uploaded_file(bukti_b, UPLOADS_BAR)
                log_activity(level, f"Upload bukti barang: {bukti_path}")

            new_b = {
                "tanggal": str(pd.to_datetime(tgl_b).date()),
                "jenis": jenis_b,
                "keterangan": ket_b,
                "jumlah": float(jml_b),
                "satuan": satuan_b,
                "bukti": bukti_path,
                "bukti_penerimaan": bukti_path
            }
            df_barang = pd.concat([df_barang, pd.DataFrame([new_b])], ignore_index=True)
            save_csv(df_barang, FILE_BARANG)
            log_activity(level, "Input barang baru")
            st.success("Data barang berhasil disimpan!")

    # TABEL BARANG + tombol edit (Ketua)
    st.subheader("Data Barang Masuk")
    if len(df_barang) > 0:
        for i in range(len(df_barang)):
            colA, colB = st.columns([6,1])
            with colA:
                st.write(df_barang.iloc[[i]])
            with colB:
                if level == "Ketua":
                    if st.button("✏️ Edit", key=f"barang_edit_{i}"):
                        st.session_state.edit_barang_idx = i
                        st.experimental_rerun()
    else:
        st.info("Belum ada data barang.")


# =====================================================
#  MENU: LAPORAN
# =====================================================
elif menu == "📄 Laporan":
    st.header("📄 Laporan Keuangan")
    if len(df_keu) > 0:
        df_show = df_keu.copy()
        df_show["Bukti"] = df_show["bukti_url"].apply(preview_link)
        st.markdown(df_show.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.info("Belum ada data.")


# =====================================================
#  MENU: LOG
# =====================================================
elif menu == "🧾 Log":
    st.header("🧾 Log Aktivitas")
    df_log = read_csv_safe(FILE_LOG)
    if len(df_log) > 0:
        st.dataframe(df_log)
        if st.button("⬇️ Download Log (CSV)"):
            st.download_button("Download", df_log.to_csv(index=False).encode("utf-8"), "log_aktivitas.csv", mime="text/csv")
    else:
        st.info("Belum ada log.")
