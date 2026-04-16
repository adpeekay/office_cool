# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 14:30:14 2026

@author: Martyn
"""
#office_app


import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path 

EPW_DIR = Path("data")

# -------------------------------------------------------
# Page config
# -------------------------------------------------------

st.set_page_config(
    page_title="Cambridge Office Cooling Model",
    layout="centered"
)

st.title("🏢 Cooling‑Only Energy Model – Cambridge Office")
st.markdown(
    """
    **Cooling demand comparison for different glazing types**  
    Location: Cambridge, UK  
    Model includes internal gains, solar gains, and optional PV offset.
    """
)

# -------------------------------------------------------
# Sidebar inputs
# -------------------------------------------------------

st.sidebar.header("Building Parameters")

N_OCC = st.sidebar.slider("Number of occupants", 1, 50, 10)
FLOOR_AREA = N_OCC * 15
GLASS_AREA = st.sidebar.slider("Glazing area (m²)", 5, 50, 20)
T_COOL = st.sidebar.slider("Cooling setpoint (°C)", 20, 28, 24)
COP_COOL = st.sidebar.slider("Cooling COP", 2.0, 6.0, 3.0)

st.sidebar.header("Weather Data")

epw_files = sorted(EPW_DIR.glob("*.epw"))

if not epw_files:
    st.error("No EPW files found in /data directory")
    st.stop()

epw_names = [f.stem.replace("_", " ") for f in epw_files]

selected_epw = st.sidebar.selectbox(
    "Select EPW weather file",
    epw_names
)

epw_path = epw_files[epw_names.index(selected_epw)]

st.sidebar.markdown("---")
st.sidebar.header("Run Simulation")

# -------------------------------------------------------
# Constants
# -------------------------------------------------------

ORIENTATION = 180  # South-facing

GAIN_OCC = 120 * N_OCC
GAIN_EQUIP = 8 * FLOOR_AREA
GAIN_LIGHTS = 10 * FLOOR_AREA
GAIN_INTERNAL = GAIN_OCC + GAIN_EQUIP + GAIN_LIGHTS
#some details about each location 
place = {"lag": {"unit_price": 0.12, "unit_C": 0.38}, "mad": {"unit_price": 0.20, "unit_C": 0.12}, "cam": {"unit_price": 0.27, "unit_C": 0.12}}

# -------------------------------------------------------
# Glazing definitions
# -------------------------------------------------------

GLAZING = {
    "Normal Glass": {
        "U": 5.5,
        "SHGC": 0.75,
        "pv_eff": 0.0
    },
    "Solar-Control Glass": {
        "U": 2.0,
        "SHGC": 0.35,
        "pv_eff": 0.0
    },
    "CdTe PV Glass": {
        "U": 3.0,
        "SHGC": 0.12,
        "pv_eff": 0.08
    }
}

# -------------------------------------------------------
# Solar geometry
# -------------------------------------------------------

def solar_geometry(df):
    doy = df.index.dayofyear + df.index.hour / 24
    lat = 52.205  # Cambridge

    decl = 23.45 * np.sin(np.deg2rad(360 * (284 + doy) / 365))
    hra = 15 * (df.index.hour - 12)

    alt = np.rad2deg(np.arcsin(
        np.sin(np.deg2rad(lat)) * np.sin(np.deg2rad(decl)) +
        np.cos(np.deg2rad(lat)) * np.cos(np.deg2rad(decl)) * np.cos(np.deg2rad(hra))
    ))
    alt = np.maximum(alt, 0)

    az = np.rad2deg(np.arctan2(
        -np.cos(np.deg2rad(decl)) * np.sin(np.deg2rad(hra)),
        np.cos(np.deg2rad(lat)) * np.sin(np.deg2rad(decl)) -
        np.sin(np.deg2rad(lat)) * np.cos(np.deg2rad(decl)) * np.cos(np.deg2rad(hra))
    ))

    df["altitude"] = alt
    df["azimuth"] = az
    return df


def irr_vertical(df, orientation_deg):
    alt = np.deg2rad(df["altitude"])
    azi = np.deg2rad(df["azimuth"])
    ori = np.deg2rad(orientation_deg)

    cos_theta = (
        np.cos(alt) * np.cos(azi - ori)
    )
    cos_theta = np.maximum(cos_theta, 0)

    I_direct = df["DNI"] * cos_theta
    I_diffuse = df["DHI"] * 0.5

    df["I_façade"] = I_direct + I_diffuse
    return df

# -------------------------------------------------------
# EPW loader
# -------------------------------------------------------

def load_epw(path):
    df = pd.read_csv(path, skiprows=8, header=None)
    df.index = pd.date_range("2020-01-01 00:00", periods=len(df), freq="h")

    return df.rename(columns={
        6: "DryBulb",
        13: "DHI",
        14: "DNI",
        15: "GHI"
    })[["DryBulb", "GHI", "DNI", "DHI"]]

# -------------------------------------------------------
# Cooling simulation
# -------------------------------------------------------

def simulate_cooling(df, glazing):
    U = glazing["U"]
    SHGC = glazing["SHGC"]
    pv_eff = glazing["pv_eff"]

    cool_energy = 0.0

    for i in range(len(df)):
        Tout = df["DryBulb"].iloc[i]
        I = df["I_façade"].iloc[i]

        Q_cond = U * GLASS_AREA * max(Tout - T_COOL, 0)
        Q_solar = SHGC * GLASS_AREA * I
        Q_PV = pv_eff * GLASS_AREA * I

        Q_total = GAIN_INTERNAL + Q_cond + Q_solar - Q_PV

        if Q_total > 0:
            cool_energy += Q_total / COP_COOL

    return cool_energy / 1000  # kWh/year

# -------------------------------------------------------
# Main app logic
# -------------------------------------------------------

if st.button("Run annual cooling simulation"):
    with st.spinner("Running simulation..."):
        df = load_epw(epw_path)
        df = solar_geometry(df)
        df = irr_vertical(df, ORIENTATION)


        results = {}

        for name, g in GLAZING.items():
            results[name] = simulate_cooling(df, g)

    st.success("Simulation complete ✅")
    
    #selected location (mad, CAM, Lag) to access data place dict
    for key in place:
        if key.lower() in epw.selected.lower()
        data = place[key]
        break
    unit_price = data["unit_price"]
    unit_C = data["unit_C"]
    
    # Results table
    results_df = pd.DataFrame.from_dict(
        results, orient="index", columns=["Annual Cooling (kWh)"]
    )
    baseline = results_df.loc["Normal Glass", "Annual Cooling (kWh)"] #added

    results_df["Reduction (%)"] = (
        100 * (baseline - results_df["Annual Cooling (kWh)"]) / baseline
    ) #added

    #attempt to get grid  carbon and cost savings involved
    #grid_df = pd.DataFrame.from_dict(place, orient="index")
    
    results_df["Cost Saving (£)"] = (unit_price * results_df["Annual Cooling (kWh)"])

    results_df["CO2 savings (kgCO"/kWh)"] = (unit_C * results_df["Annual Cooling (kWh)"])
        
    st.dataframe(results_df.style.format("{:.1f}"))

    # Plot
    fig, ax = plt.subplots()
    ax.bar(results.keys(), results.values())
    ax.set_ylabel("Cooling Energy (kWh)")
    ax.set_title("Annual Cooling Energy Comparison")

    st.pyplot(fig)

else:
    st.info("Select an EPW file to begin.")
