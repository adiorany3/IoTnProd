import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
import io

# Set page title
st.title('Data Produksi Ayam Broiler')

# File uploader untuk data produksi
uploaded_file = st.file_uploader("Upload file Excel Data Produksi", type=['xlsx', 'xls'])
# File uploader untuk data kondisi lingkungan
env_file = st.file_uploader("Upload file Excel Kondisi Lingkungan", type=['xlsx', 'xls'], key='env')

def generate_pdf_report(df_merged, corr_df=None, validasi_summary=None):
    html = "<h1>Report Data Gabungan Produksi & Lingkungan</h1>"
    html += df_merged.head(20).to_html(index=False)
    if corr_df is not None:
        html += "<h2>Korelasi Variabel Lingkungan & Produksi</h2>"
        html += corr_df.to_html()
    if validasi_summary is not None:
        html += "<h2>Ringkasan Validasi Standar</h2>"
        html += "<ul>"
        for item in validasi_summary:
            html += f"<li>{item}</li>"
        html += "</ul>"
    return html

def generate_pdf_report_reportlab(df_merged, corr_df=None, validasi_summary=None, rekomendasi=None, catatan=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    small = styles['Normal'].clone('small')
    small.fontSize = 7

    elements.append(Paragraph("Report Data Gabungan Produksi & Lingkungan", styles['Heading1']))

    # Data Gabungan (pecah per 100 baris jika banyak)
    data = [df_merged.columns.tolist()] + df_merged.values.tolist()
    chunk_size = 100
    for i in range(0, len(data)-1, chunk_size):
        chunk = [data[0]] + data[i+1:i+1+chunk_size]
        t = Table(chunk, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))
        if i + chunk_size < len(data)-1:
            elements.append(PageBreak())

    # Korelasi
    if corr_df is not None:
        elements.append(Paragraph("Korelasi Variabel Lingkungan & Produksi", styles['Heading2']))
        corr_data = [ ["" ] + list(corr_df.columns) ]
        for idx, row in corr_df.iterrows():
            corr_data.append([str(idx)] + [f"{v:.2f}" for v in row.values])
        t2 = Table(corr_data, repeatRows=1)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t2)
        elements.append(Spacer(1, 0.5*cm))

    # Validasi
    if validasi_summary is not None:
        elements.append(Paragraph("Ringkasan Validasi Standar", styles['Heading2']))
        for item in validasi_summary:
            elements.append(Paragraph(item, small))
        elements.append(Spacer(1, 0.5*cm))

    # Rekomendasi
    if rekomendasi:
        elements.append(Paragraph("Rekomendasi Standar Kandang Close House", styles['Heading2']))
        elements.append(Paragraph(rekomendasi, small))
        elements.append(Spacer(1, 0.5*cm))

    # Catatan
    if catatan:
        elements.append(Paragraph("Catatan", styles['Heading2']))
        elements.append(Paragraph(catatan, small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

if uploaded_file is not None and env_file is not None:
    try:
        # Read both Excel files
        df_prod = pd.read_excel(uploaded_file)
        df_env = pd.read_excel(env_file)
        # Pastikan kolom tanggal ada dan bertipe datetime.date (bukan datetime64[ns])
        if 'Date' in df_prod.columns:
            df_prod['Date'] = pd.to_datetime(df_prod['Date'], errors='coerce').dt.date
        else:
            st.error("File data produksi harus memiliki kolom 'Date'.")
            st.stop()
        if 'Date' in df_env.columns:
            df_env['Date'] = pd.to_datetime(df_env['Date'], errors='coerce').dt.date
        elif 'record_datetime' in df_env.columns:
            df_env['Date'] = pd.to_datetime(df_env['record_datetime'], errors='coerce').dt.date
        else:
            st.error("File kondisi lingkungan harus memiliki kolom 'Date' atau 'record_datetime'.")
            st.stop()
        # Jika ada kolom 'cycle', tampilkan pilihan filter cycle
        if 'cycle' in df_prod.columns:
            cycles = df_prod['cycle'].dropna().unique()
            selected_cycle = st.selectbox('Pilih Cycle (atau Semua)', options=['Semua'] + list(map(str, sorted(cycles))))
            if selected_cycle != 'Semua':
                df_prod = df_prod[df_prod['cycle'].astype(str) == selected_cycle]
                if 'cycle' in df_env.columns:
                    df_env = df_env[df_env['cycle'].astype(str) == selected_cycle]
        # Info jumlah data per cycle sebelum merge
        if 'cycle' in df_prod.columns:
            st.write('Jumlah data per cycle (sebelum merge):')
            st.write(df_prod['cycle'].value_counts().sort_index())
        # Gabungkan berdasarkan kolom Date (left join agar semua data produksi tetap muncul)
        df_merged = pd.merge(df_prod, df_env, on='Date', how='left')
        # Info jumlah data per cycle setelah merge
        if 'cycle' in df_merged.columns:
            st.write('Jumlah data per cycle (setelah merge):')
            st.write(df_merged['cycle'].value_counts().sort_index())
        # Tampilkan warning jika ada data produksi yang tidak punya pasangan data lingkungan
        missing_env = df_merged[df_merged[df_env.columns.difference(['Date'])].isnull().all(axis=1)]
        if not missing_env.empty:
            st.warning(f"Ada {len(missing_env)} baris data produksi yang tidak memiliki pasangan data kondisi lingkungan pada tanggal terkait.")
        # Urutkan berdasarkan tanggal
        df_merged = df_merged.sort_values('Date')
        # Tampilkan hasil
        st.subheader('Data Gabungan Produksi & Kondisi Lingkungan (Diurutkan Tanggal)')
        st.dataframe(df_merged)
        # Download hasil gabungan
        import io
        merged_buffer = io.BytesIO()
        df_merged.to_excel(merged_buffer, index=False)
        st.download_button('Download Data Gabungan (XLSX)', merged_buffer.getvalue(), file_name='gabungan_produksi_lingkungan.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        # Korelasi antara variabel lingkungan dan variabel produksi
        st.subheader('Analisis Korelasi Variabel Lingkungan & Produksi')
        # Daftar kolom lingkungan dan produksi
        env_cols = [
            'value_calibration_temp', 'value_calibration_hum', 'THI',
            'value_calibration_wind', 'WCI'
        ]
        prod_cols = [
            'Mortality Adjusted', 'Mortality Rate (%)', 'Live Weight',
            'Harvest Weight', 'Cumulative Feed', 'Feed Intake', 'FCR', 'Index Performance'
        ]
        # Cek kolom yang tersedia di df_merged
        env_cols_present = [col for col in env_cols if col in df_merged.columns]
        prod_cols_present = [col for col in prod_cols if col in df_merged.columns]
        if env_cols_present and prod_cols_present:
            corr_df = df_merged[env_cols_present + prod_cols_present].corr().loc[env_cols_present, prod_cols_present]
            st.dataframe(corr_df.style.background_gradient(cmap='coolwarm', axis=None))
            st.caption('Tabel di atas menunjukkan nilai korelasi Pearson antara variabel lingkungan dan variabel produksi.')
        else:
            st.info('Beberapa kolom yang dibutuhkan untuk analisis korelasi tidak ditemukan di data gabungan.')

        # --- Rekomendasi Standar Close House ---
        st.subheader('Rekomendasi Standar Kandang Close House')
        st.markdown("""
        **Suhu (°C):**
        - 1–7 hari: 32–34
        - 8–14 hari: 30–32
        - 15–21 hari: 28–30
        - 22–28 hari: 26–28
        - >28 hari: 24–26

        **Kelembaban (%):** 60–70  
        **Kadar Amonia (ppm):** Maksimal 20 (ideal <10)  
        **Kekuatan Kipas (ventilasi):**  
        - 1–7 hari: 1–2 m³/jam/ekor  
        - 8–21 hari: 2–4 m³/jam/ekor  
        - >21 hari: 4–6 m³/jam/ekor  
        """)

        # --- Validasi Data Terhadap Standar ---
        st.subheader('Validasi Data Terhadap Standar')
        # Asumsi kolom umur ayam ada, misal 'Day' (hari)
        if 'Day' in df_merged.columns:
            def cek_suhu(row):
                if row['Day'] <= 7:
                    return 32 <= row.get('value_calibration_temp', 0) <= 34
                elif row['Day'] <= 14:
                    return 30 <= row.get('value_calibration_temp', 0) <= 32
                elif row['Day'] <= 21:
                    return 28 <= row.get('value_calibration_temp', 0) <= 30
                elif row['Day'] <= 28:
                    return 26 <= row.get('value_calibration_temp', 0) <= 28
                else:
                    return 24 <= row.get('value_calibration_temp', 0) <= 26

            df_merged['Suhu_Sesuai'] = df_merged.apply(cek_suhu, axis=1)
        else:
            df_merged['Suhu_Sesuai'] = None

        # Kelembaban
        if 'value_calibration_hum' in df_merged.columns:
            df_merged['Kelembaban_Sesuai'] = df_merged['value_calibration_hum'].between(60, 70)
        else:
            df_merged['Kelembaban_Sesuai'] = None

        # Amonia
        if 'amonia' in df_merged.columns:
            df_merged['Amonia_Sesuai'] = df_merged['amonia'] <= 20
        else:
            df_merged['Amonia_Sesuai'] = None

        # Ventilasi/Kipas (asumsi value_calibration_wind dalam m3/jam/ekor, sesuaikan jika satuan berbeda)
        if 'value_calibration_wind' in df_merged.columns and 'Day' in df_merged.columns:
            def cek_ventilasi(row):
                wind = row.get('value_calibration_wind', 0)
                if row['Day'] <= 7:
                    return 1 <= wind <= 2
                elif row['Day'] <= 21:
                    return 2 <= wind <= 4
                else:
                    return 4 <= wind <= 6
            df_merged['Ventilasi_Sesuai'] = df_merged.apply(cek_ventilasi, axis=1)
        else:
            df_merged['Ventilasi_Sesuai'] = None

        # Tampilkan ringkasan validasi (tambahkan ventilasi)
        st.write('**Persentase Data yang Sesuai Standar:**')
        for col, label in [
            ('Suhu_Sesuai', 'Suhu'),
            ('Kelembaban_Sesuai', 'Kelembaban'),
            ('Amonia_Sesuai', 'Amonia'),
            ('Ventilasi_Sesuai', 'Ventilasi/Kipas')
        ]:
            if col in df_merged.columns and df_merged[col].notnull().sum() > 0:
                persen = 100 * df_merged[col].sum(skipna=True) / df_merged[col].notnull().sum()
                st.write(f"- {label}: {persen:.1f}% data sesuai standar (dari {df_merged[col].notnull().sum()} data)")
            else:
                st.write(f"- {label}: Data tidak tersedia")

        # Tampilkan data yang tidak sesuai standar (tambahkan ventilasi)
        st.write('**Contoh Data yang Tidak Sesuai Standar:**')
        cols_check = ['Date', 'Day', 'value_calibration_temp', 'value_calibration_hum', 'amonia', 'value_calibration_wind',
                      'Suhu_Sesuai', 'Kelembaban_Sesuai', 'Amonia_Sesuai', 'Ventilasi_Sesuai']
        cols_check = [c for c in cols_check if c in df_merged.columns]
        st.dataframe(df_merged.loc[
            ~(df_merged['Suhu_Sesuai'].fillna(True) &
              df_merged['Kelembaban_Sesuai'].fillna(True) &
              df_merged['Amonia_Sesuai'].fillna(True) &
              df_merged['Ventilasi_Sesuai'].fillna(True)),
            cols_check
        ].head(10))

        # --- Rekomendasi Jumlah Kipas Menyala ---
        st.subheader('Rekomendasi Jumlah Kipas Menyala')

        # Input tambahan: luas kandang (m2)
        luas_kandang = st.number_input('Masukkan luas kandang (m²):', min_value=1, value=1000)

        # Asumsi: kapasitas satu kipas (m3/jam), jumlah kipas terpasang
        kapasitas_kipas = st.number_input('Masukkan kapasitas satu kipas (m³/jam):', min_value=1, value=10000)
        jumlah_kipas_terpasang = st.number_input('Masukkan jumlah kipas terpasang:', min_value=1, value=6)
        populasi = st.number_input('Masukkan populasi ayam:', min_value=1, value=10000)

        # Hitung kebutuhan ventilasi per ekor sesuai umur
        def kebutuhan_ventilasi_per_ekor(day):
            if day <= 7:
                return 1.5  # rata-rata 1–2 m3/jam/ekor
            elif day <= 21:
                return 3    # rata-rata 2–4 m3/jam/ekor
            else:
                return 5    # rata-rata 4–6 m3/jam/ekor

        # Hitung kebutuhan ventilasi per m2 (opsional, jika ingin membandingkan)
        kebutuhan_ventilasi_per_m2 = 10  # m3/jam/m2 (standar umum, bisa disesuaikan)

        if 'Day' in df_merged.columns:
            # Kebutuhan berdasarkan populasi
            df_merged['Ventilasi_Dibutuhkan_Populasi'] = df_merged['Day'].apply(lambda x: kebutuhan_ventilasi_per_ekor(x) * populasi)
            # Kebutuhan berdasarkan luas kandang
            df_merged['Ventilasi_Dibutuhkan_Luasan'] = luas_kandang * kebutuhan_ventilasi_per_m2
            # Pilih kebutuhan terbesar (safety)
            df_merged['Ventilasi_Dibutuhkan'] = df_merged[['Ventilasi_Dibutuhkan_Populasi', 'Ventilasi_Dibutuhkan_Luasan']].max(axis=1)
            df_merged['Kipas_Menyala'] = (df_merged['Ventilasi_Dibutuhkan'] / kapasitas_kipas).apply(lambda x: min(jumlah_kipas_terpasang, max(1, int(round(x)))))
            st.write('**Contoh Rekomendasi Jumlah Kipas Menyala:**')
            st.dataframe(df_merged[['Date', 'Day', 'Ventilasi_Dibutuhkan', 'Kipas_Menyala']].head(10))
        else:
            st.info('Kolom umur ayam (Day) tidak ditemukan, tidak dapat menghitung kebutuhan kipas.')

        st.markdown("""
        **Catatan:**
        - Perhitungan kebutuhan ventilasi diambil dari kebutuhan terbesar antara populasi dan luasan kandang.
        - Jika kebutuhan ventilasi < total kapasitas semua kipas, gunakan sistem intermitten (on-off) agar suhu dan kelembaban tetap stabil.
        - Contoh intermitten: Jika hanya butuh 2 kipas dari 6, maka 2 kipas menyala, 4 kipas mati, atau semua kipas menyala bergantian sesuai timer (misal 10 menit on, 20 menit off).
        - Atur waktu on-off sesuai kebutuhan ventilasi aktual dan kondisi kandang.
        """)

        # --- Bagian setelah semua analisis selesai, sebelum except ---
        # Siapkan ringkasan validasi
        validasi_summary = []
        for col, label in [
            ('Suhu_Sesuai', 'Suhu'),
            ('Kelembaban_Sesuai', 'Kelembaban'),
            ('Amonia_Sesuai', 'Amonia'),
            ('Ventilasi_Sesuai', 'Ventilasi/Kipas')
        ]:
            if col in df_merged.columns and df_merged[col].notnull().sum() > 0:
                persen = 100 * df_merged[col].sum(skipna=True) / df_merged[col].notnull().sum()
                validasi_summary.append(f"{label}: {persen:.1f}% data sesuai standar (dari {df_merged[col].notnull().sum()} data)")
            else:
                validasi_summary.append(f"{label}: Data tidak tersedia")

        # Tombol download PDF (ganti dengan reportlab)
        rekomendasi = """
        <b>Suhu (°C):</b><br/>
        - 1–7 hari: 32–34<br/>
        - 8–14 hari: 30–32<br/>
        - 15–21 hari: 28–30<br/>
        - 22–28 hari: 26–28<br/>
        - &gt;28 hari: 24–26<br/>
        <b>Kelembaban (%):</b> 60–70<br/>
        <b>Kadar Amonia (ppm):</b> Maksimal 20 (ideal &lt;10)<br/>
        <b>Kekuatan Kipas (ventilasi):</b><br/>
        - 1–7 hari: 1–2 m³/jam/ekor<br/>
        - 8–21 hari: 2–4 m³/jam/ekor<br/>
        - &gt;21 hari: 4–6 m³/jam/ekor<br/>
        """
        catatan = """
        - Perhitungan kebutuhan ventilasi diambil dari kebutuhan terbesar antara populasi dan luasan kandang.<br/>
        - Jika kebutuhan ventilasi &lt; total kapasitas semua kipas, gunakan sistem intermitten (on-off) agar suhu dan kelembaban tetap stabil.<br/>
        - Contoh intermitten: Jika hanya butuh 2 kipas dari 6, maka 2 kipas menyala, 4 kipas mati, atau semua kipas menyala bergantian sesuai timer (misal 10 menit on, 20 menit off).<br/>
        - Atur waktu on-off sesuai kebutuhan ventilasi aktual dan kondisi kandang.
        """
        pdf_bytes = generate_pdf_report_reportlab(
            df_merged,
            corr_df if 'corr_df' in locals() else None,
            validasi_summary,
            rekomendasi,
            catatan
        )
        st.download_button(
            label="Download Report PDF",
            data=pdf_bytes,
            file_name="report_produksi_lingkungan.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.error("Pastikan kedua file memiliki kolom tanggal yang sesuai ('Date' atau 'record_datetime')!")
else:
    st.info('Upload kedua file: data produksi dan data kondisi lingkungan untuk menggabungkan.')

# Add some information
st.sidebar.info('Upload file Excel yang berisi data produksi ayam broiler')