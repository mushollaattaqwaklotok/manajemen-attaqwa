import streamlit as st
import pandas as pd
import os
from datetime import datetime

# =====================================================
#  KONFIGURASI AWAL
# =====================================================

DATA_DIR = "data"
UPLOADS_DIR = "uploads"
UPLOADS_BUKTI_KEU = f"{UPLOADS_DIR}/keuangan"
UPLOADS_BUKTI_BARANG = f"{UPLOADS_DIR}/barang"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(UPLOADS_BUKTI_KEU, exist_ok=True)
os.makedirs(UPLOADS_BUKTI_BARANG, exist_ok=True)

FILE_KEUANGAN = f"{DATA_DIR}/keuangan.csv"
FILE_BARANG = f"{DATA_DIR}/barang.csv"
FILE_LOG = f"{DATA_DIR}/log.csv"

GITHUB_KEUANGAN = "https://raw.githubusercontent.com/mushollaattaqwaklotok/laporan-keuangan/refs/heads/main/data/keuangan.csv"
GITHUB_BARANG = "https://raw.githubusercontent.com/mushollaattaqwaklotok/laporan-keuangan/refs/heads/main/data/barang.csv"

PANITIA = {
    "ketua": "kelas3ku",
    "sekretaris": "fatik3762",
    "bendahara 1": "hadi5028",
    "bendahara 2": "riki6522",
    "koor donasi 1": "bayu0255",
    "koor donasi 2": "roni9044"
}

# =====================================================
#  UI PREMIUM – Hanya Tampilan
# =====================================================
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

section[data-testid="stSidebar"] {
    background:#0b6e4f; padding:20px;
}
section[data-testid="stSidebar"] * { color:white !important; }

.stButton>button {
    background: linear-gradient(90deg,#0b6e4f,#18a36d);
    color:white !important; font-weight:700;
    padding:8px 22px; border-radius:10px;
}
.stButton>button:hover {
    background: linear-gradient(90deg,#18a36d,#0b6e4f);
    transform:scale(1.03);
}

input, textarea, select {
    border-radius:10px !important;
    border:1px solid #0b6e4f !important;
}

.infocard {
    background:white; border-radius:14px;
    padding:18px; text-align:center;
    border:1px solid #d9e9dd;
    margin-bottom:15px;
}
.infocard h3 { margin:4px 0; font-size:20px; }
.infocard p { margin:0; font-weight:700; font-size:18px; }

.dataframe th {
    background:#0b6e4f !important;
    color:white !important;
    padding:8px !important;
}
.dataframe td {
    padding:6px !important;
    border:1px solid #c8e6d3 !important;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
#  FUNGSI UTILITAS
# =====================================================
def load_csv_safe(local_file, github_url, columns):
    """Jika lokal ada pakai lokal. Jika tidak pakai GitHub."""
    if os.path.exists(local_file):
        try:
            return pd.read_csv(local_file)
        except:
            pass
    try:
        return pd.read_csv(github_url)
    except:
        return pd.DataFrame(columns=columns)


def save_csv(df, file):
    df.to_csv(file, index=False)


def preview_link(url):
    if pd.isna(url) or url == "":
        return "-"
    return f"<a href='{url}' target='_blank'>Lihat Bukti</a>"


def log(activity, user):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_log = pd.DataFrame([[now, user, activity]],
                columns=["Waktu","User","Aktivitas"])
    if os.path.exists(FILE_LOG):
        old = pd.read_csv(FILE_LOG)
        df_log = pd.concat([old, df_log], ignore_index=True)
    df_log.to_csv(FILE_LOG, index=False)


# =====================================================
#  LOAD DATA
# =====================================================
df_keu = load_csv_safe(
    FILE_KEUANGAN,
    GITHUB_KEUANGAN,
    ["Tanggal","Keterangan","Kategori","Masuk","Keluar","Saldo","bukti_url"]
)

df_barang = load_csv_safe(
    FILE_BARANG,
    GITHUB_BARANG,
    ["tanggal","jenis","keterangan","jumlah","satuan","bukti","bukti_penerimaan"]
)

df_log = load_csv_safe(
    FILE_LOG,
    "",
    ["Waktu","User","Aktivitas"]
)


# =====================================================
#  HEADER UI
# =====================================================
st.markdown("""
<div class="header-box">
    <div class="header-title">Laporan Keuangan Musholla At-Taqwa</div>
    <div class="header-sub">Transparansi • Amanah • Profesional</div>
</div>
""", unsafe_allow_html=True)


# =====================================================
#  LOGIN
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

# =====================================================
#  MENU UTAMA
# =====================================================
menu = st.sidebar.radio("Menu:", ["💰 Keuangan", "📦 Barang Masuk", "📄 Laporan", "🧾 Log"])


# =====================================================
#  MODE EDIT
# =====================================================
if "edit_keu" not in st.session_state:
    st.session_state.edit_keu = None

if "edit_barang" not in st.session_state:
    st.session_state.edit_barang = None


# =====================================================
#  DASHBOARD KEUANGAN
# =====================================================
if menu == "💰 Keuangan":

    st.header("💰 Keuangan")

    # Dashboard Card
    if len(df_keu) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class='infocard'>
                <h3>Total Masuk</h3>
                <p>Rp {df_keu['Masuk'].sum():,}</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='infocard'>
                <h3>Total Keluar</h3>
                <p>Rp {df_keu['Keluar'].sum():,}</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class='infocard'>
                <h3>Saldo Akhir</h3>
                <p>Rp {df_keu['Saldo'].iloc[-1]:,}</p>
            </div>
            """, unsafe_allow_html=True)


    # ===========================
    #  EDIT MODE KEUANGAN
    # ===========================
    if level == "Ketua" and st.session_state.edit_keu is not None:
        idx = st.session_state.edit_keu
        row = df_keu.iloc[idx]

        st.subheader("✏️ Edit Data Keuangan")

        tgl_e = st.date_input("Tanggal", datetime.strptime(row["Tanggal"], "%Y-%m-%d"))
        ket_e = st.text_input("Keterangan", row["Keterangan"])
        kategori_e = st.selectbox("Kategori", ["Kas Masuk", "Kas Keluar"], 
                                  index=0 if row["Kategori"]=="Kas Masuk" else 1)
        masuk_e = st.number_input("Masuk", min_value=0, value=int(row["Masuk"]))
        keluar_e = st.number_input("Keluar", min_value=0, value=int(row["Keluar"]))
        bukti_e = st.file_uploader("Ganti Bukti (opsional)")

        if st.button("💾 Simpan Perubahan"):
            bukti_path = row["bukti_url"]
            if bukti_e:
                bukti_path = f"{UPLOADS_BUKTI_KEU}/{bukti_e.name}"
                with open(bukti_path, "wb") as f:
                    f.write(bukti_e.read())

            df_keu.loc[idx, "Tanggal"] = str(tgl_e)
            df_keu.loc[idx, "Keterangan"] = ket_e
            df_keu.loc[idx, "Kategori"] = kategori_e
            df_keu.loc[idx, "Masuk"] = masuk_e
            df_keu.loc[idx, "Keluar"] = keluar_e
            df_keu.loc[idx, "bukti_url"] = bukti_path

            df_keu["Saldo"] = df_keu["Masuk"].cumsum() - df_keu["Keluar"].cumsum()

            save_csv(df_keu, FILE_KEUANGAN)
            log(f"Edit data keuangan index {idx}", level)

            st.success("Data berhasil diperbarui!")
            st.session_state.edit_keu = None
            st.rerun()

        if st.button("Batal"):
            st.session_state.edit_keu = None
            st.rerun()

        st.divider()


    # ===========================
    #  INPUT DATA BARU
    # ===========================
    st.subheader("Input Keuangan")

    if level == "Publik":
        st.info("🔒 Hanya panitia yang dapat input data.")
        if len(df_keu) > 0:
            st.download_button(
                "⬇️ Download Laporan (CSV)",
                df_keu.to_csv(index=False),
                "laporan_keuangan.csv"
            )

    else:
        tgl = st.date_input("Tanggal")
        ket = st.text_input("Keterangan")
        kategori = st.selectbox("Kategori", ["Kas Masuk", "Kas Keluar"])
        masuk = st.number_input("Masuk", min_value=0)
        keluar = st.number_input("Keluar", min_value=0)
        bukti = st.file_uploader("Upload Bukti")

        if st.button("Simpan Data"):
            bukti_path = ""
            if bukti:
                bukti_path = f"{UPLOADS_BUKTI_KEU}/{bukti.name}"
                with open(bukti_path, "wb") as f:
                    f.write(bukti.read())

            saldo_akhir = (df_keu["Saldo"].iloc[-1] if len(df_keu) else 0) + masuk - keluar

            new_row = {
                "Tanggal": str(tgl),
                "Keterangan": ket,
                "Kategori": kategori,
                "Masuk": masuk,
                "Keluar": keluar,
                "Saldo": saldo_akhir,
                "bukti_url": bukti_path
            }

            df_keu = pd.concat([df_keu, pd.DataFrame([new_row])], ignore_index=True)
            save_csv(df_keu, FILE_KEUANGAN)

            log("Input data keuangan baru", level)

            st.success("Data berhasil disimpan!")

    # ===========================
    #  TABEL DATA + TOMBOL EDIT
    # ===========================
    st.subheader("Tabel Laporan Keuangan")

    df_show = df_keu.copy()
    df_show["Bukti"] = df_show["bukti_url"].apply(preview_link)

    for i in range(len(df_show)):
        colA, colB = st.columns([5,1])
        with colA:
            st.markdown(df_show.iloc[[i]].to_html(escape=False), unsafe_allow_html=True)
        if level == "Ketua":
            with colB:
                if st.button("✏️ Edit", key=f"edit_{i}"):
                    st.session_state.edit_keu = i
                    st.rerun()


# =====================================================
#  BARANG MASUK (ADA FITUR EDIT)
# =====================================================
elif menu == "📦 Barang Masuk":

    st.header("📦 Barang Masuk")

    # ============= MODE EDIT BARANG ==================
    if level == "Ketua" and st.session_state.edit_barang is not None:
        idx = st.session_state.edit_barang
        row = df_barang.iloc[idx]

        st.subheader("✏️ Edit Data Barang")

        tgl_b = st.date_input("Tanggal Barang", datetime.strptime(row["tanggal"], "%Y-%m-%d"))
        jenis_b = st.text_input("Jenis Barang", row["jenis"])
        ket_b = st.text_input("Keterangan", row["keterangan"])
        jml_b = st.number_input("Jumlah", min_value=0, value=int(row["jumlah"]))
        satuan_b = st.text_input("Satuan", row["satuan"])
        bukti_b = st.file_uploader("Ganti Bukti Penerimaan (opsional)")

        if st.button("💾 Simpan Perubahan Barang"):
            bukti_path = row["bukti"]

            if bukti_b:
                bukti_path = f"{UPLOADS_BUKTI_BARANG}/{bukti_b.name}"
                with open(bukti_path, "wb") as f:
                    f.write(bukti_b.read())

            df_barang.loc[idx] = [
                str(tgl_b), jenis_b, ket_b, jml_b, satuan_b, bukti_path, bukti_path
            ]

            save_csv(df_barang, FILE_BARANG)
            log(f"Edit data barang index {idx}", level)

            st.success("Data barang berhasil diupdate!")
            st.session_state.edit_barang = None
            st.rerun()

        if st.button("Batal"):
            st.session_state.edit_barang = None
            st.rerun()

        st.divider()

    # ===== INPUT BARANG BARU =====
    if level == "Publik":
        st.info("🔒 Hanya panitia yang dapat input data.")
        if len(df_barang) > 0:
            st.download_button(
                "⬇️ Download Data Barang",
                df_barang.to_csv(index=False),
                "barang.csv"
            )

    else:
        tgl_b = st.date_input("Tanggal Barang")
        jenis_b = st.text_input("Jenis Barang")
        ket_b = st.text_input("Keterangan")
        jml_b = st.number_input("Jumlah", min_value=0)
        satuan_b = st.text_input("Satuan")
        bukti_b = st.file_uploader("Upload Bukti Penerimaan")

        if st.button("Simpan Barang"):
            bukti_path = ""
            if bukti_b:
                bukti_path = f"{UPLOADS_BUKTI_BARANG}/{bukti_b.name}"
                with open(bukti_path, "wb") as f:
                    f.write(bukti_b.read())

            new_b = {
                "tanggal": str(tgl_b),
                "jenis": jenis_b,
                "keterangan": ket_b,
                "jumlah": jml_b,
                "satuan": satuan_b,
                "bukti": bukti_path,
                "bukti_penerimaan": bukti_path
            }

            df_barang = pd.concat([df_barang, pd.DataFrame([new_b])], ignore_index=True)
            save_csv(df_barang, FILE_BARANG)

            log("Input barang baru", level)

            st.success("Data barang berhasil disimpan!")

    # ===== TABEL BARANG + TOMBOL EDIT =====
    st.subheader("Data Barang Masuk")

    for i in range(len(df_barang)):
        colA, colB = st.columns([5,1])
        with colA:
            st.write(df_barang.iloc[[i]])
        if level == "Ketua":
            with colB:
                if st.button("✏️ Edit Barang", key=f"edit_barang_{i}"):
                    st.session_state.edit_barang = i
                    st.rerun()


# =====================================================
#  LAPORAN
# =====================================================
elif menu == "📄 Laporan":

    st.header("📄 Laporan Keuangan")

    if len(df_keu) > 0:
        df_show = df_keu.copy()
        df_show["Bukti"] = df_show["bukti_url"].apply(preview_link)
        st.write(df_show.to_html(escape=False), unsafe_allow_html=True)
    else:
        st.info("Belum ada data.")


# =====================================================
#  LOG
# =====================================================
elif menu == "🧾 Log":
    st.header("🧾 Log Aktivitas")
    st.dataframe(df_log)
