import streamlit as st
import pandas as pd

st.set_page_config(page_title="Simulasi Clinker Factor Konsolidasi dan Per Tipe Semen + Emisi CO₂")
st.title("Simulasi Clinker Factor Konsolidasi dan Per Tipe Semen + Emisi CO₂")

# --- Load Data ---
@st.cache_data
def load_data():
    df_raw = pd.read_excel("Clinker_Factor_2025.xlsx", sheet_name="MTD")
    return df_raw

df_raw = load_data()

# --- Sidebar Filter ---
bulan = st.selectbox("Pilih Bulan:", df_raw["Month"].dropna().unique())
periode = st.selectbox("Pilih Periode:", df_raw["Periode"].dropna().unique())
tipe_data = st.selectbox("Pilih Jenis Data:", ["Actual", "Budget"])

# --- Filter Data ---
df_filtered = df_raw[(df_raw["Month"] == bulan) & (df_raw["Periode"] == periode)]

if tipe_data == "Actual":
    df = df_filtered[["Cement Type", "Actual Clinker Consumption", "Actual Cement Production"]].copy()
    df.columns = ["Cement Type", "Clinker Consumption", "Cement Production"]
else:
    df = df_filtered[["Cement Type", "Budget Clinker Consumption", "Budget Cement Production"]].copy()
    df.columns = ["Cement Type", "Clinker Consumption", "Cement Production"]

# Hitung Clinker Factor Awal
df["Clinker Factor"] = df["Clinker Consumption"] / df["Cement Production"] * 100
total_clinker_awal = df["Clinker Consumption"].sum()
total_cement = df["Cement Production"].sum()
cf_awal = total_clinker_awal / total_cement * 100

st.write(f"**Clinker Factor Konsolidasi Awal: {cf_awal:.2f}%**")

# --- Simulasi Mode ---
mode = st.radio("Pilih Mode Simulasi:", ["Ubah CF Konsolidasi", "Ubah CF per Tipe Semen"])

if mode == "Ubah CF Konsolidasi":
    target_cf = st.number_input("Masukkan Target CF Konsolidasi (%)", min_value=0.0, value=cf_awal)
    semen_dipilih = st.multiselect("Pilih tipe semen yang akan disesuaikan Clinker Consumption-nya:", df["Cement Type"].tolist())

    if len(semen_dipilih) < 2:
        st.warning("⚠️ Pilih minimal 2 tipe semen untuk simulasi CF Konsolidasi.")
    else:
        df_new = df.copy()

        # Semen yang tidak dipilih
        df_tetap = df_new[~df_new["Cement Type"].isin(semen_dipilih)]
        clinker_tetap = df_tetap["Clinker Consumption"].sum()

        # Semen yang dipilih
        df_ubah = df_new[df_new["Cement Type"].isin(semen_dipilih)].copy()
        total_prod_ubah = df_ubah["Cement Production"].sum()

        # Hitung clinker total sesuai target CF
        clinker_total_target = (target_cf / 100) * total_cement
        clinker_ubah_total = clinker_total_target - clinker_tetap

        # Update clinker semen yang dipilih secara proporsional
        for idx in df_ubah.index:
            prod = df_ubah.at[idx, "Cement Production"]
            clinker_baru = clinker_ubah_total * (prod / total_prod_ubah)
            df_new.at[idx, "Clinker Consumption"] = clinker_baru
            df_new.at[idx, "Clinker Factor"] = clinker_baru / prod * 100

        cf_konsolidasi_baru = df_new["Clinker Consumption"].sum() / total_cement * 100

        st.subheader("Kondisi Sebelum")
        st.dataframe(df[df["Cement Type"].isin(semen_dipilih)])

        st.subheader("Kondisi Setelah")
        st.dataframe(df_new[df_new["Cement Type"].isin(semen_dipilih)])

        st.success(f"✅ CF Konsolidasi Setelah Simulasi: {cf_konsolidasi_baru:.2f}%")

elif mode == "Ubah CF per Tipe Semen":
    semen_dipilih = st.multiselect("Pilih tipe semen yang ingin diubah nilai CF-nya:", df["Cement Type"].tolist())
    cf_baru_dict = {}

    if semen_dipilih:
        st.subheader("Masukkan Clinker Factor Baru untuk Setiap Tipe Semen:")
        for semen in semen_dipilih:
            default_val = float(df[df["Cement Type"] == semen]["Clinker Factor"])
            cf_input = st.number_input(f"{semen} (CF Baru %):", min_value=0.0, max_value=100.0, value=round(default_val, 2))
            cf_baru_dict[semen] = cf_input

    if cf_baru_dict:
        df_result = df.copy()
        for semen, cf_new in cf_baru_dict.items():
            idx = df_result[df_result["Cement Type"] == semen].index[0]
            prod = df_result.loc[idx, "Cement Production"]
            df_result.at[idx, "Clinker Factor"] = cf_new
            df_result.at[idx, "Clinker Consumption"] = prod * cf_new / 100

        cf_konsolidasi_baru = df_result["Clinker Consumption"].sum() / total_cement * 100

        st.subheader("Kondisi Sebelum")
        st.dataframe(df[df["Cement Type"].isin(semen_dipilih)])

        st.subheader("Kondisi Setelah")
        st.dataframe(df_result[df_result["Cement Type"].isin(semen_dipilih)])

        st.success(f"✅ Clinker Factor Konsolidasi Setelah Simulasi: {cf_konsolidasi_baru:.2f}%")

# --- Simulasi CO2 Emission ---
st.markdown("---")
st.header("🔍 Simulasi Emisi CO₂ Berdasarkan Clinker Factor Konsolidasi")

clinker_factor = st.number_input("Clinker Factor Konsolidasi (%)", min_value=0.0, max_value=100.0, value=cf_awal)
stec = st.number_input("STEC (MJ/ton Clinker)", value=3340.0)
tsr = st.number_input("TSR  (%)", value=13.0)
fuel_ef = st.number_input("fuel_ef  (kg CO2/MJ)", value=0.0958)
calcination_factor = st.number_input("Calcination Factor (kg CO2/kg Clinker)", value=0.531)
factor = st.number_input("factor adj", value=1.01)

co2_process = clinker_factor/100  * calcination_factor * 1000
co2_fuel = stec * fuel_ef * (1 - tsr / 100) * clinker_factor/100
co2_tot = co2_process + co2_fuel
co2_total=co2_tot * factor 

st.metric("CO2 Specific Net (kg CO2/ton cement Eq)", f"{co2_total:.0f}")
