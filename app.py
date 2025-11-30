import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, timezone

# ======================================================
#  KONFIGURASI UTAMA
# ======================================================
DATA_FILE = "data/keuangan.csv"
LOG_FILE = "data/log_aktivitas.csv"

# Zona waktu GMT+7
TZ = timezone(timedelta(hours=7))

# Multi-password untuk panitia
PANITIA_USERS = {
    "Ketua": "kelas3ku",
    "Sekretaris": "fatik3762",
    "Bendahara 1": "hadi5028",
    "Bendahara 2": "riki6522",
    "Koor Donasi 1": "bayu0255",
    "Koor Donasi 2": "roni9044"
}

PUBLIK_MODE = "PUBLIK"
PANITIA_MODE = "PANITIA"

# Pastikan folder data ada
os.makedirs("data", exist_ok=True)

# ======================================================
#  FUNGSI DATA
# ======================================================
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Tanggal", "Keterangan", "Masuk", "Keluar", "Saldo"])
        df.to_csv(DATA_FILE, index=False)
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def load_log():
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
        df.to_csv(LOG_FILE, index=False)
    return pd.read_csv(LOG_FILE)

def save_log(user, aksi, detail=""):
    df = load_log()
    new_row = {
        "Waktu": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "Pengguna": user,
        "Aksi": aksi,
        "Detail": detail
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)

def clear_log():
    df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
    df.to_csv(LOG_FILE, index=False)

# ======================================================
#  TEMA WARNA NU
# ======================================================
st.markdown("""
    <style>
        body { background-color: #ffffff; }
        .main { background-color: #ffffff; }
        .stApp { background-color: #ffffff; }
        h1, h2, h3 { color: #0b6e4f; font-weight: 800; }

        .stButton>button {
            background-color: #0b6e4f;
            color: white;
            font-weight: bold;
            border-radius: 6px;
            padding: 6px 16px;
        }
        .stButton>button:hover {
            background-color: #0d8a64;
            color: white;
        }

        .stTextInput input, .stNumberInput input {
            border: 1px solid #0b6e4f !important;
        }
    </style>
""", unsafe_allow_html=True)

# ======================================================
#  PILIH MODE
# ======================================================
st.sidebar.header("📌 Pilih Mode")
mode = st.sidebar.radio("Mode", [PUBLIK_MODE, PANITIA_MODE])

# ======================================================
#  MODE PUBLIK
# ======================================================
if mode == PUBLIK_MODE:
    st.title("💒 Musholla At-Taqwa RT.1 Dusun Klotok– PUBLIK")

    df = load_data()

    if df.empty:
        st.info("Belum ada data keuangan.")
    else:
        st.subheader("📄 Laporan Keuangan")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Data CSV",
            csv,
            "keuangan_musholla.csv",
            "text/csv",
        )

# ======================================================
#  MODE PANITIA
# ======================================================
else:
    st.title("🕌 Panel PANITIA – Kelola Keuangan Musholla")

    username = st.sidebar.selectbox("Pilih Nama Panitia", ["-"] + list(PANITIA_USERS.keys()))
    password = st.sidebar.text_input("Password", type="password")

    if username == "-" or password != PANITIA_USERS.get(username):
        st.warning("Masukkan username & password panitia.")
        st.stop()

    st.success(f"Login berhasil ✔️ (Panitia: {username})")

    # Log login
    save_log(username, "Login", "Masuk ke panel panitia")

    df = load_data()

    # -------------------------
    # FORM TAMBAH DATA
    # -------------------------
    st.subheader("➕ Tambah Data Baru")

    col1, col2 = st.columns(2)
    with col1:
        tanggal = st.date_input("Tanggal", datetime.now(TZ))
        keterangan = st.text_input("Keterangan")
    with col2:
        masuk = st.number_input("Uang Masuk", min_value=0, step=1000)
        keluar = st.number_input("Uang Keluar", min_value=0, step=1000)

    if st.button("Simpan Data"):
        saldo_akhir = df["Saldo"].iloc[-1] if not df.empty else 0
        saldo_baru = saldo_akhir + masuk - keluar

        new_row = {
            "Tanggal": str(tanggal),
            "Keterangan": keterangan,
            "Masuk": masuk,
            "Keluar": keluar,
            "Saldo": saldo_baru
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)

        save_log(username, "Tambah Data", f"{keterangan} | +{masuk} / -{keluar}")

        st.success("Data berhasil disimpan!")

    # -------------------------
    # TABEL KEUANGAN
    # -------------------------
    st.subheader("📄 Tabel Keuangan")
    st.dataframe(df, use_container_width=True)

    # -------------------------
    # HAPUS DATA
    # -------------------------
    st.subheader("🗑 Hapus Baris Data")

    if not df.empty:
        idx = st.number_input(
            f"Pilih nomor baris (0 - {len(df)-1})",
            min_value=0, max_value=len(df)-1, step=1
        )

        if st.button("Hapus Baris"):
            deleted = df.iloc[idx].to_dict()
            df = df.drop(idx).reset_index(drop=True)
            save_data(df)

            save_log(username, "Hapus Data", str(deleted))

            st.success("Baris berhasil dihapus!")

    # -------------------------
    # DOWNLOAD CSV
    # -------------------------
    st.subheader("⬇️ Download Data")

    csv = df.to_csv(index=False).encode("utf-8")
    if st.download_button("Download CSV", csv, "keuangan_musholla.csv", "text/csv"):
        save_log(username, "Download CSV", "Mengunduh data keuangan")

    # -------------------------
    # LOG AKTIVITAS
    # -------------------------
    st.subheader("📘 Log Aktivitas Panitia")

    log_df = load_log()
    st.dataframe(log_df, use_container_width=True)

    # -------------------------
    # HAPUS LOG (KHUSUS KETUA)
    # -------------------------
    if username == "Ketua":
        st.warning("⚠️ Fitur Khusus Ketua")
        if st.button("Hapus Semua Log"):
            clear_log()
            save_log("Ketua", "Hapus Semua Log", "Log aktivitas direset ketua")
            st.success("Semua log aktivitas berhasil dihapus!")
