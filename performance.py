import streamlit as st
import pandas as pd

# Set page title
st.title('Data Produksi Ayam Broiler')

# File uploader untuk data produksi
uploaded_file = st.file_uploader("Upload file Excel Data Produksi", type=['xlsx', 'xls'])
# File uploader untuk data kondisi lingkungan
env_file = st.file_uploader("Upload file Excel Kondisi Lingkungan", type=['xlsx', 'xls'], key='env')

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
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.error("Pastikan kedua file memiliki kolom tanggal yang sesuai ('Date' atau 'record_datetime')!")
else:
    st.info('Upload kedua file: data produksi dan data kondisi lingkungan untuk menggabungkan.')

# Add some information
st.sidebar.info('Upload file Excel yang berisi data produksi ayam broiler')