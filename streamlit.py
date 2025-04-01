import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import plotly.express as px

# Streamlit App Title
st.title("Water Quality Site Finder")

# Upload Water Quality Data
st.sidebar.header("Upload Data Files")
uploaded_results = st.sidebar.file_uploader("Upload USGS Water Quality CSV File", type=["csv"])
uploaded_sites = st.sidebar.file_uploader("Upload USGS Site Locations CSV File", type=["csv"])

if uploaded_results and uploaded_sites:
    # Load datasets
    df_results = pd.read_csv(uploaded_results, parse_dates=["ActivityStartDate"])
    df_sites = pd.read_csv(uploaded_sites)

    # Convert ResultMeasureValue to numeric, forcing errors to NaN
    df_results["ResultMeasureValue"] = pd.to_numeric(df_results["ResultMeasureValue"], errors="coerce")

    # Drop missing values in key columns
    df_results = df_results.dropna(subset=["CharacteristicName", "MonitoringLocationIdentifier", "ActivityStartDate", "ResultMeasureValue"])
    df_sites = df_sites.dropna(subset=["MonitoringLocationIdentifier", "LatitudeMeasure", "LongitudeMeasure"])

    # Ensure data types are correct
    df_results["CharacteristicName"] = df_results["CharacteristicName"].astype(str)
    df_sites["MonitoringLocationIdentifier"] = df_sites["MonitoringLocationIdentifier"].astype(str)
    df_results["MonitoringLocationIdentifier"] = df_results["MonitoringLocationIdentifier"].astype(str)

    # Merge data on MonitoringLocationIdentifier
    df = pd.merge(df_results, df_sites, on="MonitoringLocationIdentifier", how="left")

    # Rename columns for clarity
    df.rename(columns={"LatitudeMeasure": "Latitude", "LongitudeMeasure": "Longitude"}, inplace=True)

    # Sidebar Filters
    st.sidebar.header("Filter Data")

    # Select Contaminant
    selected_contaminant = st.sidebar.selectbox("Select Contaminant", sorted(df["CharacteristicName"].unique()))

    # Filter dataset for selected contaminant
    df_filtered_contaminant = df[df["CharacteristicName"] == selected_contaminant].copy()

    # Ensure the column is numeric
    df_filtered_contaminant["ResultMeasureValue"] = pd.to_numeric(df_filtered_contaminant["ResultMeasureValue"], errors="coerce")
    df_filtered_contaminant = df_filtered_contaminant.dropna(subset=["ResultMeasureValue"])

    # Dynamically update min/max range based on selected contaminant
    if not df_filtered_contaminant.empty:
        min_value, max_value = df_filtered_contaminant["ResultMeasureValue"].min(), df_filtered_contaminant["ResultMeasureValue"].max()
        value_range = st.sidebar.slider(
            "Select Contaminant Value Range", 
            float(min_value) if pd.notna(min_value) else 0, 
            float(max_value) if pd.notna(max_value) else 1, 
            (float(min_value) if pd.notna(min_value) else 0, float(max_value) if pd.notna(max_value) else 1)
        )
    else:
        st.sidebar.warning("No data available for this contaminant.")
        value_range = (0, 0)  # Default range if no data

    # Select Date Range
    df["ActivityStartDate"] = pd.to_datetime(df["ActivityStartDate"])  # Ensure correct datetime format
    min_date, max_date = df["ActivityStartDate"].min(), df["ActivityStartDate"].max()
    start_date, end_date = st.sidebar.date_input("Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    # Filter data based on user selection
    df_filtered = df[
        (df["CharacteristicName"] == selected_contaminant) &
        (df["ActivityStartDate"] >= pd.to_datetime(start_date)) &
        (df["ActivityStartDate"] <= pd.to_datetime(end_date)) &
        (df["ResultMeasureValue"] >= value_range[0]) &
        (df["ResultMeasureValue"] <= value_range[1])
    ]

    if df_filtered.empty:
        st.warning("No data found for the selected filters.")
    else:
        # Create Map
        st.subheader("Sites Matching the Selected Filters")
        site_map = folium.Map(location=[df_filtered["Latitude"].mean(), df_filtered["Longitude"].mean()], zoom_start=7)

        for _, row in df_filtered.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=f"Site: {row['MonitoringLocationIdentifier']}<br>Value: {row['ResultMeasureValue']}<br>Date: {row['ActivityStartDate'].date()}",
                tooltip=row["MonitoringLocationIdentifier"]
            ).add_to(site_map)

        # Display Map
        folium_static(site_map)

        # Trend Plot
        st.subheader("Trend of Contaminant Values Over Time")
        trend_data = df_filtered.groupby(["ActivityStartDate", "MonitoringLocationIdentifier"])["ResultMeasureValue"].mean().reset_index()
        
        if not trend_data.empty:
            fig = px.line(trend_data, x="ActivityStartDate", y="ResultMeasureValue", color="MonitoringLocationIdentifier", 
                          title=f"Trend of {selected_contaminant} Over Time")
            st.plotly_chart(fig)
        else:
            st.warning("Insufficient data to generate trend plot.")
