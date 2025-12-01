# app.py (UPGRADE: upload bukti, preview, barang, bukti penerimaan)
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
import requests
import base64
import io
import mimetypes

# ======================================================
#  KONFIGURASI UTAMA (tetap kompatibel dgn app sebelumnya)
# ======================================================
DATA_FILE = "data/keuangan.csv"
LOG_FILE = "data/log_aktivitas.csv"
BARANG_FILE = "data/barang.csv"  # untuk catatan barang

# Zona waktu GMT+7
TZ = timezone(timedelta(hours=7))

# Multi-password untuk panitia (tetap)
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

# Pastikan folder data ada (untuk fallback lokal)
os.makedirs("data", exist_ok=True)

# ======================================================
#  GITHUB CONFIG (ambil dari st.secrets jika ada)
# ======================================================
GITHUB_TOKEN = None
GITHUB_REPO = None
GITHUB_DATA_PATH = None
GITHUB_LOG_PATH = None
GITHUB_BARANG_PATH = None

if "GITHUB_TOKEN" in st.secrets:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
if "GITHUB_REPO" in st.secrets:
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
if "GITHUB_DATA_PATH" in st.secrets:
    GITHUB_DATA_PATH = st.secrets["GITHUB_DATA_PATH"]
if "GITHUB_LOG_PATH" in st.secrets:
    GITHUB_LOG_PATH = st.secrets["GITHUB_LOG_PATH"]
if "GITHUB_BARANG_PATH" in st.secrets:
    GITHUB_BARANG_PATH = st.secrets["GITHUB_BARANG_PATH"]

# defaults (jika tidak diberikan via secrets)
if not GITHUB_DATA_PATH:
    GITHUB_DATA_PATH = "data/keuangan.csv"
if not GITHUB_LOG_PATH:
    GITHUB_LOG_PATH = "data/log_aktivitas.csv"
if not GITHUB_BARANG_PATH:
    GITHUB_BARANG_PATH = "data/barang.csv"

# Helper: raw URL
def github_raw_url(repo, path, branch="main"):
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

# ======================================================
#  GITHUB HELPERS (GET content, PUT update, create file)
# ======================================================
def github_get_file(repo, path):
    """Return tuple (content_text, sha) or (None, None) on error."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None, None
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        j = r.json()
        content_b64 = j.get("content", "")
        sha = j.get("sha", None)
        try:
            content = base64.b64decode(content_b64).decode("utf-8")
        except Exception:
            content = None
        return content, sha
    else:
        return None, None

def github_put_file(repo, path, content_bytes_or_text, commit_message="Update via Streamlit", sha=None, is_binary=False):
    """
    Create or update file in GitHub repo. content_bytes_or_text: bytes or str.
    If is_binary True, content is bytes and will be base64 encoded directly.
    Returns True if success, else False.
    """
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    if is_binary:
        encoded = base64.b64encode(content_bytes_or_text).decode()
    else:
        if isinstance(content_bytes_or_text, bytes):
            encoded = base64.b64encode(content_bytes_or_text).decode()
        else:
            encoded = base64.b64encode(str(content_bytes_or_text).encode()).decode()
    payload = {"message": commit_message, "content": encoded}
    if sha:
        payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code in (200, 201)

# ======================================================
#  HELPER LOCAL FILE ENSURE
# ======================================================
def ensure_local_file(path, columns):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)

# ======================================================
#  FUNGSI DATA & LOG (mendukung GitHub atau fallback lokal)
# ======================================================
def load_data():
    # Try GitHub raw first
    if GITHUB_TOKEN and GITHUB_REPO:
        raw = github_raw_url(GITHUB_REPO, GITHUB_DATA_PATH)
        try:
            df = pd.read_csv(raw)
            return df
        except Exception:
            content, sha = github_get_file(GITHUB_REPO, GITHUB_DATA_PATH)
            if content:
                try:
                    df = pd.read_csv(io.StringIO(content))
                    return df
                except Exception:
                    pass
    # fallback local
    ensure_local_file(DATA_FILE, ["Tanggal", "Keterangan", "Masuk", "Keluar", "Saldo", "Bukti", "Bukti_Penerimaan"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    csv_text = df.to_csv(index=False)
    if GITHUB_TOKEN and GITHUB_REPO:
        _, sha = github_get_file(GITHUB_REPO, GITHUB_DATA_PATH)
        ok = github_put_file(GITHUB_REPO, GITHUB_DATA_PATH, csv_text, commit_message="Update keuangan.csv via Streamlit", sha=sha, is_binary=False)
        if ok:
            return True
        else:
            df.to_csv(DATA_FILE, index=False)
            return False
    else:
        df.to_csv(DATA_FILE, index=False)
        return True

def ensure_remote_log_exists():
    if GITHUB_TOKEN and GITHUB_REPO:
        content, sha = github_get_file(GITHUB_REPO, GITHUB_LOG_PATH)
        if content is None:
            header_df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
            github_put_file(GITHUB_REPO, GITHUB_LOG_PATH, header_df.to_csv(index=False), commit_message="Create log_aktivitas.csv via Streamlit", is_binary=False)

def load_log():
    if GITHUB_TOKEN and GITHUB_REPO:
        raw = github_raw_url(GITHUB_REPO, GITHUB_LOG_PATH)
        try:
            df = pd.read_csv(raw)
            return df
        except Exception:
            content, sha = github_get_file(GITHUB_REPO, GITHUB_LOG_PATH)
            if content:
                try:
                    df = pd.read_csv(io.StringIO(content))
                    return df
                except Exception:
                    pass
    ensure_local_file(LOG_FILE, ["Waktu", "Pengguna", "Aksi", "Detail"])
    return pd.read_csv(LOG_FILE)

def save_log(user, aksi, detail=""):
    waktu = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    new_row = {"Waktu": waktu, "Pengguna": user, "Aksi": aksi, "Detail": detail}
    if GITHUB_TOKEN and GITHUB_REPO:
        content, sha = github_get_file(GITHUB_REPO, GITHUB_LOG_PATH)
        if content:
            try:
                df = pd.read_csv(io.StringIO(content))
            except Exception:
                df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
        else:
            df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        ok = github_put_file(GITHUB_REPO, GITHUB_LOG_PATH, df.to_csv(index=False), commit_message="Update log_aktivitas.csv via Streamlit", sha=sha, is_binary=False)
        if ok:
            return True
        else:
            df.to_csv(LOG_FILE, index=False)
            return False
    else:
        df = load_log()
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(LOG_FILE, index=False)
        return True

def clear_log():
    df = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
    if GITHUB_TOKEN and GITHUB_REPO:
        _, sha = github_get_file(GITHUB_REPO, GITHUB_LOG_PATH)
        github_put_file(GITHUB_REPO, GITHUB_LOG_PATH, df.to_csv(index=False), commit_message="Reset log_aktivitas.csv via Streamlit", sha=sha, is_binary=False)
    df.to_csv(LOG_FILE, index=False)

# ======================================================
#  BARANG: load/save (terpisah dari keuangan)
# ======================================================
def load_barang():
    if GITHUB_TOKEN and GITHUB_REPO:
        raw = github_raw_url(GITHUB_REPO, GITHUB_BARANG_PATH)
        try:
            df = pd.read_csv(raw)
            return df
        except Exception:
            content, sha = github_get_file(GITHUB_REPO, GITHUB_BARANG_PATH)
            if content:
                try:
                    df = pd.read_csv(io.StringIO(content))
                    return df
                except Exception:
                    pass
    ensure_local_file(BARANG_FILE, ["Tanggal", "Jenis", "Keterangan", "Jumlah", "Satuan", "Bukti"])
    return pd.read_csv(BARANG_FILE)

def save_barang(df):
    csv_text = df.to_csv(index=False)
    if GITHUB_TOKEN and GITHUB_REPO:
        _, sha = github_get_file(GITHUB_REPO, GITHUB_BARANG_PATH)
        ok = github_put_file(GITHUB_REPO, GITHUB_BARANG_PATH, csv_text, commit_message="Update barang.csv via Streamlit", sha=sha, is_binary=False)
        if ok:
            return True
        else:
            df.to_csv(BARANG_FILE, index=False)
            return False
    else:
        df.to_csv(BARANG_FILE, index=False)
        return True

# ======================================================
#  FILE UPLOAD HELPERS (upload ke GitHub path atau simpan lokal)
# ======================================================
def upload_file_to_repo(folder_path, filename, file_bytes):
    """
    Upload given bytes to repo path `folder_path/filename`.
    Returns raw URL (https://raw.githubusercontent...) on success, else None.
    """
    # ensure folder path ends without slash
    folder_path = folder_path.strip("/")

    path = f"{folder_path}/{filename}"
    if GITHUB_TOKEN and GITHUB_REPO:
        # check if exists to get sha (not necessary for new files, but harmless)
        _, sha = github_get_file(GITHUB_REPO, path)
        ok = github_put_file(GITHUB_REPO, path, file_bytes, commit_message=f"Upload {filename} via Streamlit", sha=sha, is_binary=True)
        if ok:
            # raw url
            raw = github_raw_url(GITHUB_REPO, path)
            return raw
        else:
            return None
    else:
        # fallback local save
        local_dir = os.path.join("data", folder_path)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        with open(local_path, "wb") as f:
            f.write(file_bytes)
        # return local file URL path (file:// may not be accessible in Streamlit web, so return relative path)
        return local_path

def make_safe_filename(prefix, original_name):
    # timestamp + sanitized original
    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(original_name)[0]
    ext = os.path.splitext(original_name)[1].lower()
    safe_base = "".join(c for c in base if c.isalnum() or c in (" ", "-", "_")).rstrip()
    safe_base = safe_base.replace(" ", "_")
    return f"{prefix}_{ts}_{safe_base}{ext}"

# ======================================================
#  Pastikan remote files minimal ada saat app start
# ======================================================
if GITHUB_TOKEN and GITHUB_REPO:
    # ensure data file exists
    content, sha = github_get_file(GITHUB_REPO, GITHUB_DATA_PATH)
    if content is None:
        df0 = pd.DataFrame([{"Tanggal": datetime.now(TZ).strftime("%Y-%m-%d"),
                             "Keterangan": "Saldo Awal",
                             "Masuk": 0,
                             "Keluar": 0,
                             "Saldo": 0,
                             "Bukti": "",
                             "Bukti_Penerimaan": ""}])
        github_put_file(GITHUB_REPO, GITHUB_DATA_PATH, df0.to_csv(index=False), commit_message="Create keuangan.csv via Streamlit", is_binary=False)
    # ensure log file
    ensure_remote_log_exists()
    # ensure barang file
    content_b, sha_b = github_get_file(GITHUB_REPO, GITHUB_BARANG_PATH)
    if content_b is None:
        df_b = pd.DataFrame(columns=["Tanggal", "Jenis", "Keterangan", "Jumlah", "Satuan", "Bukti"])
        github_put_file(GITHUB_REPO, GITHUB_BARANG_PATH, df_b.to_csv(index=False), commit_message="Create barang.csv via Streamlit", is_binary=False)

# ======================================================
#  TEMA WARNA NU (tidak diubah)
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
#  PILIH MODE (tetap)
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
        # show table but hide raw bukti links; we'll show preview below
        st.dataframe(df.drop(columns=[c for c in ["Bukti","Bukti_Penerimaan"] if c in df.columns]), use_container_width=True)

        # Provide preview expander per row if bukti exists
        st.subheader("🔍 Bukti / Nota")
        for i, row in df.iterrows():
            bukti = row.get("Bukti", "") if "Bukti" in row else ""
            bukti_penerimaan = row.get("Bukti_Penerimaan", "") if "Bukti_Penerimaan" in row else ""
            if pd.notna(bukti) and bukti:
                with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti)"):
                    if bukti.endswith((".jpg", ".jpeg", ".png")) or (bukti.startswith("data/") and any(bukti.lower().endswith(ext) for ext in [".jpg",".jpeg",".png"])):
                        # If remote raw URL or local path
                        try:
                            if bukti.startswith("http"):
                                st.image(bukti, use_column_width=True)
                            else:
                                st.image(open(bukti, "rb").read(), use_column_width=True)
                        except Exception:
                            st.markdown(f"[Lihat Bukti]({bukti})")
                    else:
                        st.markdown(f"[Lihat Bukti (file)]({bukti})")
            if pd.notna(bukti_penerimaan) and bukti_penerimaan:
                with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti Penerimaan)"):
                    if bukti_penerimaan.startswith("http"):
                        # pdf or image link
                        if bukti_penerimaan.lower().endswith((".jpg",".jpeg",".png")):
                            st.image(bukti_penerimaan, use_column_width=True)
                        else:
                            st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")
                    else:
                        st.markdown(f"Lokal: {bukti_penerimaan}")

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
    # FORM TAMBAH DATA (TETAP) + Upload Bukti (baru)
    # -------------------------
    st.subheader("➕ Tambah Data Baru")

    col1, col2 = st.columns(2)
    with col1:
        tanggal = st.date_input("Tanggal", datetime.now(TZ))
        keterangan = st.text_input("Keterangan")
    with col2:
        masuk = st.number_input("Uang Masuk", min_value=0, step=1000)
        keluar = st.number_input("Uang Keluar", min_value=0, step=1000)

    # Upload bukti nota (opsional)
    uploaded_file = st.file_uploader("Upload Nota / Bukti (opsional) — gambar/pdf", type=["jpg","jpeg","png","pdf"])
    # Bukti penerimaan (opsional)
    uploaded_bukti_penerimaan = st.file_uploader("Upload Bukti Penerimaan / Kwitansi (opsional)", type=["jpg","jpeg","png","pdf"])

    if st.button("Simpan Data"):
        # recalc saldo: ambil saldo terakhir dari sumber (remote jika ada)
        df = load_data()
        saldo_akhir = df["Saldo"].iloc[-1] if (not df.empty and "Saldo" in df.columns) else 0
        saldo_baru = saldo_akhir + masuk - keluar

        # handle bukti upload (nota)
        bukti_url = ""
        if uploaded_file is not None:
            safe_name = make_safe_filename("nota", uploaded_file.name)
            file_bytes = uploaded_file.getvalue()
            # upload to repo folder data/bukti or save locally under data/bukti/
            remote = upload_file_to_repo("data/bukti", safe_name, file_bytes)
            if remote:
                bukti_url = remote
            else:
                bukti_url = ""

        # handle bukti penerimaan
        bukti_penerimaan_url = ""
        if uploaded_bukti_penerimaan is not None:
            safe_name2 = make_safe_filename("penerimaan", uploaded_bukti_penerimaan.name)
            file_bytes2 = uploaded_bukti_penerimaan.getvalue()
            remote2 = upload_file_to_repo("data/penerimaan", safe_name2, file_bytes2)
            if remote2:
                bukti_penerimaan_url = remote2
            else:
                bukti_penerimaan_url = ""

        # ensure df has bukti columns
        if "Bukti" not in df.columns:
            df["Bukti"] = ""
        if "Bukti_Penerimaan" not in df.columns:
            df["Bukti_Penerimaan"] = ""

        new_row = {
            "Tanggal": str(tanggal),
            "Keterangan": keterangan,
            "Masuk": masuk,
            "Keluar": keluar,
            "Saldo": saldo_baru,
            "Bukti": bukti_url,
            "Bukti_Penerimaan": bukti_penerimaan_url
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        ok = save_data(df)
        save_log(username, "Tambah Data", f"{keterangan} | +{masuk} / -{keluar} | bukti={bool(bukti_url)} | bukti_penerimaan={bool(bukti_penerimaan_url)}")

        if ok:
            st.success("Data berhasil disimpan!")
        else:
            st.warning("Data disimpan lokal karena gagal menyimpan ke GitHub.")

    # -------------------------
    # TABEL KEUANGAN
    # -------------------------
    st.subheader("📄 Tabel Keuangan")
    df = load_data()
    # show table without raw bukti columns for compactness
    display_cols = [c for c in df.columns if c not in ["Bukti", "Bukti_Penerimaan"]]
    st.dataframe(df[display_cols], use_container_width=True)

    # preview bukti per baris (expander)
    st.subheader("🔍 Preview Bukti per Baris")
    for i, row in df.iterrows():
        bukti = row.get("Bukti", "") if "Bukti" in row else ""
        bukti_penerimaan = row.get("Bukti_Penerimaan", "") if "Bukti_Penerimaan" in row else ""
        if pd.notna(bukti) and bukti:
            with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti)"):
                try:
                    if bukti.startswith("http") and bukti.lower().endswith((".jpg",".jpeg",".png")):
                        st.image(bukti, use_column_width=True)
                    elif bukti.startswith("http"):
                        st.markdown(f"[Lihat Bukti]({bukti})")
                    else:
                        # local path
                        try:
                            st.image(open(bukti, "rb").read(), use_column_width=True)
                        except Exception:
                            st.markdown(f"Lokal: {bukti}")
                except Exception:
                    st.markdown(f"[Lihat Bukti]({bukti})")
        if pd.notna(bukti_penerimaan) and bukti_penerimaan:
            with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti Penerimaan)"):
                try:
                    if bukti_penerimaan.startswith("http") and bukti_penerimaan.lower().endswith((".jpg",".jpeg",".png")):
                        st.image(bukti_penerimaan, use_column_width=True)
                    elif bukti_penerimaan.startswith("http"):
                        st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")
                    else:
                        st.markdown(f"Lokal: {bukti_penerimaan}")
                except Exception:
                    st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")

    # -------------------------
    # TOMBOL HAPUS BARIS (Tetap)
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
            ok = save_data(df)
            save_log(username, "Hapus Data", str(deleted))
            if ok:
                st.success("Baris berhasil dihapus!")
            else:
                st.warning("Perubahan disimpan lokal karena gagal menyimpan ke GitHub.")

    # -------------------------
    # DOWNLOAD CSV (tetap)
    # -------------------------
    st.subheader("⬇️ Download Data")
    csv = df.to_csv(index=False).encode("utf-8")
    if st.download_button("Download CSV", csv, "keuangan_musholla.csv", "text/csv"):
        save_log(username, "Download CSV", "Mengunduh data keuangan")

    # -------------------------
    # LOG AKTIVITAS (tetap)
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

    # -------------------------
    # BAGIAN BARANG (baru)
    # -------------------------
    st.markdown("---")
    st.subheader("📦 Catatan Barang (Masuk/Keluar Non-Uang)")

    tab_input, tab_view = st.tabs(["Input Barang", "Lihat Data Barang"])
    with tab_input:
        tanggal_b = st.date_input("Tanggal Barang", datetime.now(TZ), key="tgl_b")
        jenis_b = st.selectbox("Jenis", ["Masuk", "Keluar"], key="jenis_b")
        ket_b = st.text_input("Keterangan Barang", key="ket_b")
        qty = st.number_input("Jumlah", min_value=1, step=1, key="qty_b")
        satuan = st.text_input("Satuan (pcs/box/karung)", key="satuan_b")
        file_brg = st.file_uploader("Upload Bukti Barang (opsional)", type=["jpg","jpeg","png","pdf"], key="file_brg")

        if st.button("Simpan Barang"):
            dfb = load_barang()
            bukti_barang_url = ""
            if file_brg is not None:
                safe = make_safe_filename("barang", file_brg.name)
                remote_b = upload_file_to_repo("data/bukti_barang", safe, file_brg.getvalue())
                if remote_b:
                    bukti_barang_url = remote_b
            newb = {
                "Tanggal": str(tanggal_b),
                "Jenis": jenis_b,
                "Keterangan": ket_b,
                "Jumlah": qty,
                "Satuan": satuan,
                "Bukti": bukti_barang_url
            }
            dfb = pd.concat([dfb, pd.DataFrame([newb])], ignore_index=True)
            okb = save_barang(dfb)
            save_log(username, "Tambah Barang", f"{jenis_b} | {ket_b} | {qty} {satuan} | bukti={bool(bukti_barang_url)}")
            if okb:
                st.success("Data barang tersimpan.")
            else:
                st.warning("Data barang disimpan lokal karena gagal ke GitHub.")

    with tab_view:
        dfb = load_barang()
        if dfb.empty:
            st.info("Belum ada data barang.")
        else:
            st.dataframe(dfb, use_container_width=True)
            # preview bukti barang
            for i, r in dfb.iterrows():
                b = r.get("Bukti", "")
                if pd.notna(b) and b:
                    with st.expander(f"[{i}] {r.get('Tanggal','')} — {r.get('Keterangan','')} (Bukti Barang)"):
                        if b.startswith("http") and b.lower().endswith((".jpg",".jpeg",".png")):
                            st.image(b, use_column_width=True)
                        else:
                            st.markdown(f"[Lihat Bukti Barang]({b})")

# End of app.py
