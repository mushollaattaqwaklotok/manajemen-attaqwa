# ======================================================
#  MENU PANITIA (POSISI BARANG & LOG SUDAH DI-SWITCH)
# ======================================================

menu = st.sidebar.radio(
    "Menu",
    [
        "➡️ Input Keuangan",
        "📦 Input Data Barang",   # <— DIPINDAH KE ATAS
        "🧾 Log Aktivitas",       # <— DIPINDAH KE BAWAH
        "📁 Data Keuangan",
        "📦 Data Barang",
        "⚙️ Setelan"
    ]
)

# ======================
# 1. INPUT KEUANGAN
# ======================
if menu == "➡️ Input Keuangan":
    st.header("✍️ Input Keuangan")
    ...
    ... (tidak diubah)

# ======================
# 2. INPUT DATA BARANG (dipindah ke atas)
# ======================
elif menu == "📦 Input Data Barang":
    st.header("📦 Input Data Barang")

    df_barang = load_barang()

    tanggal = st.date_input("Tanggal", datetime.now(TZ).date())
    jenis = st.selectbox("Jenis", ["Masuk", "Keluar"])
    ket = st.text_input("Keterangan")
    jumlah = st.number_input("Jumlah", min_value=0.0, step=0.1)
    satuan = st.text_input("Satuan", value="unit")

    file_bukti = st.file_uploader("Upload Bukti (opsional)", type=["jpg","jpeg","png","pdf"])

    if st.button("Simpan Barang"):
        bukti_url = ""
        if file_bukti:
            fname = make_safe_filename("barang", file_bukti.name)
            bukti_url = upload_file_to_repo("bukti_barang", fname, file_bukti.read())

        new_row = {
            "Tanggal": tanggal.strftime("%Y-%m-%d"),
            "Jenis": jenis,
            "Keterangan": ket,
            "Jumlah": jumlah,
            "Satuan": satuan,
            "Bukti": bukti_url
        }

        df_barang = pd.concat([df_barang, pd.DataFrame([new_row])], ignore_index=True)
        save_barang(df_barang)
        save_log(username, "Input Barang", ket)

        st.success("Data barang berhasil disimpan!")

# ======================
# 3. LOG AKTIVITAS (dipindah ke bawah)
# ======================
elif menu == "🧾 Log Aktivitas":
    st.header("🧾 Log Aktivitas")

    df_log = load_log()

    if df_log.empty:
        st.info("Belum ada log aktivitas.")
    else:
        st.dataframe(df_log, use_container_width=True)

    if st.button("🧹 Bersihkan Log"):
        clear_log()
        st.warning("Log aktivitas telah dibersihkan!")

# ======================
# 4. DATA KEUANGAN
# ======================
elif menu == "📁 Data Keuangan":
    ...
    ... (tidak diubah)

# ======================
# 5. DATA BARANG
# ======================
elif menu == "📦 Data Barang":
    ...
    ... (tidak diubah)

# ======================
# 6. SETELAN
# ======================
elif menu == "⚙️ Setelan":
    ...
    ... (tidak diubah)
