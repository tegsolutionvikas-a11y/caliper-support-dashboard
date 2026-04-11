import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Caliper Support Dashboard", layout="wide")

def get_sla(row):
    """
    SLA Logic: Returns a single value for the 'Expected Completion' column.
    Handles potential missing or malformed data gracefully.
    """
    try:
        # Example logic: If Severity is P1 (1), SLA might be 4 hours
        # Ensure 'Created On' is a valid datetime before doing math
        if pd.isna(row['Created On']):
            return "N/A"
            
        if row['Severity'] == 1:
            return row['Created On'] + pd.Timedelta(hours=4)
        elif row['Severity'] == 2:
            return row['Created On'] + pd.Timedelta(hours=8)
        else:
            return row['Created On'] + pd.Timedelta(hours=24)
    except:
        return "Manual Review Req."

def process_data(df, selected_companies):
    # 1. Basic Cleaning
    df.columns = df.columns.str.strip()
    
    # Convert Dates and Numeric columns immediately to avoid 'apply' errors
    df['Created On'] = pd.to_datetime(df['Created On'], errors='coerce')
    df['Severity'] = pd.to_numeric(df['Severity'], errors='coerce').fillna(4)
    # Fix: Convert TAT string "-" to 0 so math works
    df['TAT'] = pd.to_numeric(df['TAT'], errors='coerce').fillna(0)

    # 2. Filter for Completed/Auto Completed tickets
    df = df[df['Status'].isin(['Completed', 'Auto Completed'])]

    # 3. Filter by Selected Companies
    if selected_companies:
        df = df[df['Company'].isin(selected_companies)]

    if df.empty:
        return pd.DataFrame()

    # 4. Apply SLA Logic
    # FIX: Using a lambda and ensuring get_sla is defined prevents the ValueError
    df['Expected Completion'] = df.apply(lambda x: get_sla(x), axis=1)

    # 5. Map Severity to P1-P4
    sev_map = {1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'}
    df['Priority_Mapped'] = df['Severity'].map(sev_map)

    # 6. Convert TAT from Minutes to Hours
    df['TAT_Hr'] = df['TAT'] / 60.0

    # 7. Clean and Map Ticket Category
    def map_category(cat):
        if pd.isna(cat) or str(cat).strip() in ["", "-"]:
            return 'Operational Issues'
        cat_str = str(cat).lower().strip()
        if 'operat' in cat_str: return 'Operational Issues'
        if 'tech' in cat_str or 'sap' in cat_str: return 'Tech Issues'
        if 'enhan' in cat_str: return 'Enhancement'
        if 'develop' in cat_str: return 'New Development'
        return 'Operational Issues'

    # Ensure column exists before applying
    col_name = 'Ticket Category' if 'Ticket Category' in df.columns else 'Query Type'
    df['Category_Mapped'] = df[col_name].apply(map_category)

    # 8. Pivot Tables
    pivot_qty = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='Ticket SR#',
        aggfunc='count'
    ).fillna(0)

    pivot_tat = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='TAT_Hr',
        aggfunc='mean'
    ).fillna(0)

    # 9. Build final display table
    final_df = pd.DataFrame()
    priorities = ['P1', 'P2', 'P3', 'P4']
    
    for p in priorities:
        final_df[f'{p} (Qty)'] = pivot_qty[p] if p in pivot_qty.columns else 0
        final_df[f'{p} TAT (Hr)'] = pivot_tat[p] if p in pivot_tat.columns else 0

    final_df['Total Tickets'] = pivot_qty.sum(axis=1)
    final_df = final_df.reset_index()
    final_df.rename(columns={'Category_Mapped': 'Category', 'Company': 'Company Name'}, inplace=True)
    
    return final_df

# --- Streamlit UI ---
st.title("📊 Caliper Support Performance Dashboard")
st.markdown("Upload your raw report to generate the P1-P4 Severity & TAT Analysis.")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        # Load data once
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
        
        raw_df.columns = raw_df.columns.str.strip()
        
        # Sidebar
        all_companies = sorted(raw_df['Company'].dropna().unique().tolist())
        st.sidebar.header("Dashboard Filters")
        selected_companies = st.sidebar.multiselect("Select Companies:", options=all_companies, default=all_companies)

        # Process
        report_df = process_data(raw_df.copy(), selected_companies)
        
        if not report_df.empty:
            st.subheader("Performance Report")
            st.table(report_df.style.format({
                'P1 TAT (Hr)': "{:.2f}", 'P2 TAT (Hr)': "{:.2f}",
                'P3 TAT (Hr)': "{:.2f}", 'P4 TAT (Hr)': "{:.2f}",
                'P1 (Qty)': "{:.0f}", 'P2 (Qty)': "{:.0f}",
                'P3 (Qty)': "{:.0f}", 'P4 (Qty)': "{:.0f}",
                'Total Tickets': "{:.0f}"
            }))
            
            csv_data = report_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Report", data=csv_data, file_name="Caliper_TAT_Report.csv", mime="text/csv")
        else:
            st.info("No data available for the selected filters.")

    except Exception as e:
        st.error(f"Dashboard Error: {e}")
