# app.py (FINAL) - SAFE FOR STREAMLIT CLOUD
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta, timezone
import requests
import base64
import io

# ======================================================
#  KONFIGURASI UTAMA
# ======================================================
DATA_FILE = "data/keuangan.csv"
LOG_FILE = "data/log_aktivitas.csv"
BARANG_FILE = "data/barang.csv"

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

# ======================================================
# TEMP LOCAL PATH (writeable on Streamlit Cloud)
# Use /mount/data/... if available; otherwise fallback to ./data/...
# ======================================================
DEFAULT_TMP_ROOT = "/mount/data"
if not os.path.exists(DEFAULT_TMP_ROOT):
    DEFAULT_TMP_ROOT = "data"  # fallback local

LOCAL_TMP_BUKTI_UANG = os.path.join(DEFAULT_TMP_ROOT, "bukti_uang")
LOCAL_TMP_BUKTI_PENERIMAAN = os.path.join(DEFAULT_TMP_ROOT, "bukti_penerimaan")
LOCAL_TMP_BUKTI_BARANG = os.path.join(DEFAULT_TMP_ROOT, "bukti_barang")
os.makedirs(LOCAL_TMP_BUKTI_UANG, exist_ok=True)
os.makedirs(LOCAL_TMP_BUKTI_PENERIMAAN, exist_ok=True)
os.makedirs(LOCAL_TMP_BUKTI_BARANG, exist_ok=True)

# also ensure data folder exists for fallback local CSVs
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

# defaults
if not GITHUB_DATA_PATH:
    GITHUB_DATA_PATH = "data/keuangan.csv"
if not GITHUB_LOG_PATH:
    GITHUB_LOG_PATH = "data/log_aktivitas.csv"
if not GITHUB_BARANG_PATH:
    GITHUB_BARANG_PATH = "data/barang.csv"

# Helper raw URL (read-only)
def github_raw_url(repo, path, branch="main"):
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

# ======================================================
#  GITHUB API HELPERS
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
    Create or update file in GitHub repo.
    content_bytes_or_text: bytes or str.
    If is_binary True, content is bytes and will be base64 encoded directly.
    Returns True if success.
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
#  LOCAL FILE ENSURE helpers
# ======================================================
def ensure_local_file(path, columns):
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)

# ======================================================
#  DATA LOAD / SAVE (supports GitHub raw read + API write; fallback local)
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
#  BARANG load/save
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
#  FILE UPLOAD: save temp locally (to /mount/data if available) then upload to GitHub (if configured)
# ======================================================
def make_safe_filename(prefix, original_name):
    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(original_name)[0]
    ext = os.path.splitext(original_name)[1].lower()
    safe_base = "".join(c for c in base if c.isalnum() or c in (" ", "-", "_")).rstrip()
    safe_base = safe_base.replace(" ", "_")
    return f"{prefix}_{ts}_{safe_base}{ext}"

def upload_file_to_repo(folder_path, filename, file_bytes, tmp_kind="uang"):
    """
    1) write temp file to a writeable location (LOCAL_TMP_*)
    2) if GitHub configured: upload bytes to GitHub path: folder_path/filename
    3) return raw URL (if uploaded to GitHub) or local temp path (if not)
    """
    # choose tmp folder
    if tmp_kind == "uang":
        local_tmp_dir = LOCAL_TMP_BUKTI_UANG
    elif tmp_kind == "penerimaan":
        local_tmp_dir = LOCAL_TMP_BUKTI_PENERIMAAN
    elif tmp_kind == "barang":
        local_tmp_dir = LOCAL_TMP_BUKTI_BARANG
    else:
        local_tmp_dir = LOCAL_TMP_BUKTI_UANG

    os.makedirs(local_tmp_dir, exist_ok=True)
    local_path = os.path.join(local_tmp_dir, filename)

    # write temp file
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    # Attempt GitHub upload if configured
    if GITHUB_TOKEN and GITHUB_REPO:
        # read bytes back (we already have file_bytes, but ensure correct)
        try:
            ok = github_put_file(GITHUB_REPO, folder_path + "/" + filename, file_bytes, commit_message=f"Upload {filename} via Streamlit", is_binary=True)
            if ok:
                raw = github_raw_url(GITHUB_REPO, folder_path + "/" + filename)
                # remove temp file to save space (optional)
                try:
                    os.remove(local_path)
                except:
                    pass
                return raw
            else:
                return local_path
        except Exception:
            return local_path
    else:
        return local_path

# ======================================================
#  Ensure minimal files exist on remote or local
# ======================================================
if GITHUB_TOKEN and GITHUB_REPO:
    # ensure keuangan exists
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
    # ensure log exists
    content_log, sha_log = github_get_file(GITHUB_REPO, GITHUB_LOG_PATH)
    if content_log is None:
        df_log = pd.DataFrame(columns=["Waktu", "Pengguna", "Aksi", "Detail"])
        github_put_file(GITHUB_REPO, GITHUB_LOG_PATH, df_log.to_csv(index=False), commit_message="Create log_aktivitas.csv via Streamlit", is_binary=False)
    # ensure barang exists
    content_b, sha_b = github_get_file(GITHUB_REPO, GITHUB_BARANG_PATH)
    if content_b is None:
        df_b = pd.DataFrame(columns=["Tanggal", "Jenis", "Keterangan", "Jumlah", "Satuan", "Bukti"])
        github_put_file(GITHUB_REPO, GITHUB_BARANG_PATH, df_b.to_csv(index=False), commit_message="Create barang.csv via Streamlit", is_binary=False)

# ======================================================
#  THEME (tidak diubah)
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
#  MODE PICKER (PUBLIK / PANITIA)
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
        st.dataframe(df.drop(columns=[c for c in ["Bukti","Bukti_Penerimaan"] if c in df.columns]), use_container_width=True)

        # Provide preview expander per row if bukti exists
        st.subheader("🔍 Bukti / Nota")
        for i, row in df.iterrows():
            bukti = row.get("Bukti", "") if "Bukti" in row else ""
            bukti_penerimaan = row.get("Bukti_Penerimaan", "") if "Bukti_Penerimaan" in row else ""
            if pd.notna(bukti) and bukti:
                with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti)"):
                    if isinstance(bukti, str) and (bukti.endswith((".jpg", ".jpeg", ".png")) or (bukti.startswith("data/") and any(bukti.lower().endswith(ext) for ext in [".jpg",".jpeg",".png"]))):
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
                    if isinstance(bukti_penerimaan, str) and bukti_penerimaan.startswith("http"):
                        if bukti_penerimaan.lower().endswith((".jpg",".jpeg",".png")):
                            st.image(bukti_penerimaan, use_column_width=True)
                        else:
                            st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")
                    else:
                        st.markdown(f"Lokal: {bukti_penerimaan}")

    # ======================================================
    #  TAMPILAN BARANG DI PUBLIK
    # ======================================================
    st.subheader("📦 Laporan Barang Masuk / Keluar")

    dfb = load_barang()

    if dfb.empty:
        st.info("Belum ada data barang yang dicatat.")
    else:
        cols_to_show = [c for c in dfb.columns if c != "Bukti"]
        st.dataframe(dfb[cols_to_show], use_container_width=True)

        st.subheader("🔍 Bukti Barang")
        for i, row in dfb.iterrows():
            bukti = row.get("Bukti", "")
            if pd.notna(bukti) and bukti:
                with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Jenis','')} — {row.get('Keterangan','')}"):
                    try:
                        if isinstance(bukti, str) and bukti.startswith("http") and bukti.lower().endswith((".jpg",".jpeg",".png")):
                            st.image(bukti, use_column_width=True)
                        elif isinstance(bukti, str) and bukti.startswith("http"):
                            st.markdown(f"[Lihat Bukti Barang]({bukti})")
                        else:
                            st.image(open(bukti, "rb").read(), use_column_width=True)
                    except Exception:
                        st.markdown(f"[Lihat Bukti Barang]({bukti})")

    # -------------------------
    # DOWNLOAD CSV (PUBLIK)
    # -------------------------
    st.subheader("⬇️ Download Data CSV")
    csv_keu = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Keuangan (CSV)", csv_keu, "keuangan_musholla.csv", "text/csv")

    csv_barang = dfb.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Barang (CSV)", csv_barang, "barang_musholla.csv", "text/csv")

    st.stop()

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
    # FORM TAMBAH DATA + Upload Bukti
    # -------------------------
    st.subheader("➕ Tambah Data Baru")

    col1, col2 = st.columns(2)
    with col1:
        tanggal = st.date_input("Tanggal", datetime.now(TZ))
        keterangan = st.text_input("Keterangan")
    with col2:
        masuk = st.number_input("Uang Masuk", min_value=0, step=1000)
        keluar = st.number_input("Uang Keluar", min_value=0, step=1000)

    uploaded_file = st.file_uploader("Upload Nota / Bukti (opsional) — gambar/pdf", type=["jpg","jpeg","png","pdf"])
    uploaded_bukti_penerimaan = st.file_uploader("Upload Bukti Penerimaan / Kwitansi (opsional)", type=["jpg","jpeg","png","pdf"])

    if st.button("Simpan Data"):
        df = load_data()
        saldo_akhir = df["Saldo"].iloc[-1] if (not df.empty and "Saldo" in df.columns) else 0
        saldo_baru = saldo_akhir + masuk - keluar

        bukti_url = ""
        if uploaded_file is not None:
            safe_name = make_safe_filename("nota", uploaded_file.name)
            file_bytes = uploaded_file.getvalue()
            # write temp to /mount then upload to GitHub data/bukti
            remote = upload_file_to_repo("data/bukti", safe_name, file_bytes, tmp_kind="uang")
            if remote:
                bukti_url = remote

        bukti_penerimaan_url = ""
        if uploaded_bukti_penerimaan is not None:
            safe_name2 = make_safe_filename("penerimaan", uploaded_bukti_penerimaan.name)
            file_bytes2 = uploaded_bukti_penerimaan.getvalue()
            remote2 = upload_file_to_repo("data/penerimaan", safe_name2, file_bytes2, tmp_kind="penerimaan")
            if remote2:
                bukti_penerimaan_url = remote2

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
    display_cols = [c for c in df.columns if c not in ["Bukti", "Bukti_Penerimaan"]]
    st.dataframe(df[display_cols], use_container_width=True)

    # preview bukti per baris
    st.subheader("🔍 Preview Bukti per Baris")
    for i, row in df.iterrows():
        bukti = row.get("Bukti", "") if "Bukti" in row else ""
        bukti_penerimaan = row.get("Bukti_Penerimaan", "") if "Bukti_Penerimaan" in row else ""
        if pd.notna(bukti) and bukti:
            with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti)"):
                try:
                    if isinstance(bukti, str) and bukti.startswith("http") and bukti.lower().endswith((".jpg",".jpeg",".png")):
                        st.image(bukti, use_column_width=True)
                    elif isinstance(bukti, str) and bukti.startswith("http"):
                        st.markdown(f"[Lihat Bukti]({bukti})")
                    else:
                        st.image(open(bukti, "rb").read(), use_column_width=True)
                except Exception:
                    st.markdown(f"[Lihat Bukti]({bukti})")
        if pd.notna(bukti_penerimaan) and bukti_penerimaan:
            with st.expander(f"[{i}] {row.get('Tanggal','')} — {row.get('Keterangan','')} (Bukti Penerimaan)"):
                try:
                    if isinstance(bukti_penerimaan, str) and bukti_penerimaan.startswith("http") and bukti_penerimaan.lower().endswith((".jpg",".jpeg",".png")):
                        st.image(bukti_penerimaan, use_column_width=True)
                    elif isinstance(bukti_penerimaan, str) and bukti_penerimaan.startswith("http"):
                        st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")
                    else:
                        st.markdown(f"Lokal: {bukti_penerimaan}")
                except Exception:
                    st.markdown(f"[Lihat Bukti Penerimaan]({bukti_penerimaan})")

    # -------------------------
    # HAPUS BARIS
    # -------------------------
    st.subheader("🗑 Hapus Baris Data")
    if not df.empty:
        idx = st.number_input(f"Pilih nomor baris (0 - {len(df)-1})", min_value=0, max_value=len(df)-1, step=1)
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
    # DOWNLOAD CSV (PANITIA)
    # -------------------------
    st.subheader("⬇️ Download Data")
    csv_keu = df.to_csv(index=False).encode("utf-8")
    if st.download_button("Download Keuangan (CSV)", csv_keu, "keuangan_musholla.csv", "text/csv"):
        save_log(username, "Download CSV", "Mengunduh data keuangan")

    dfb = load_barang()
    csv_brg = dfb.to_csv(index=False).encode("utf-8")
    if st.download_button("Download Barang (CSV)", csv_brg, "barang_musholla.csv", "text/csv"):
        save_log(username, "Download CSV Barang", "Mengunduh data barang")

    # -------------------------
    # LOG AKTIVITAS (PALING BAWAH)
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
    # BAGIAN BARANG (PANITIA)
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
                remote_b = upload_file_to_repo("data/bukti_barang", safe, file_brg.getvalue(), tmp_kind="barang")
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
                        try:
                            if isinstance(b, str) and b.startswith("http") and b.lower().endswith((".jpg",".jpeg",".png")):
                                st.image(b, use_column_width=True)
                            elif isinstance(b, str) and b.startswith("http"):
                                st.markdown(f"[Lihat Bukti Barang]({b})")
                            else:
                                st.image(open(b, "rb").read(), use_column_width=True)
                        except Exception:
                            st.markdown(f"[Lihat Bukti Barang]({b})")

# End of app.py
