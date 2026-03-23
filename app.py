import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Caliper Support Dashboard", layout="wide")

def process_data(file, selected_companies):
    # Load data
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Clean column names
    df.columns = df.columns.str.strip()

    # 1. Filter for Completed/Auto Completed tickets
    df = df[df['Status'].isin(['Completed', 'Auto Completed'])]

    # 2. Filter by Selected Companies from Sidebar
    if selected_companies:
        df = df[df['Company'].isin(selected_companies)]

    # 3. Map Severity to P1-P4
    # Map 1->P1, 2->P2, 3->P3, 4->P4
    sev_map = {1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'}
    df['Priority_Mapped'] = df['Severity'].map(sev_map)

    # 4. Convert TAT from Minutes to Hours
    df['TAT_Hr'] = df['TAT'] / 60.0

    # 5. Clean and Map Ticket Category (Fixing the "Others" issue)
    def map_category(cat):
        cat_str = str(cat).lower().strip()
        if 'operat' in cat_str:
            return 'Operational Issues'
        elif 'tech' in cat_str or 'sap' in cat_str:
            return 'Tech Issues'
        elif 'enhan' in cat_str:
            return 'Enhancement'
        elif 'develop' in cat_str:
            return 'New Development'
        else:
            return 'Others'

    df['Category_Mapped'] = df['Ticket Category'].apply(map_category)

    # 6. Pivot Quantities
    pivot_qty = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='Ticket SR#',
        aggfunc='count'
    ).fillna(0)

    # 7. Pivot Average TAT
    pivot_tat = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='TAT_Hr',
        aggfunc='mean'
    ).fillna(0)

    # 8. Build the Final Display Table
    final_df = pd.DataFrame()
    priorities = ['P1', 'P2', 'P3', 'P4']
    
    for p in priorities:
        # Check if priority exists in data to avoid errors
        qty_col = pivot_qty[p] if p in pivot_qty.columns else 0
        tat_col = pivot_tat[p] if p in pivot_tat.columns else 0
        final_df[f'{p} (Qty)'] = qty_col
        final_df[f'{p} TAT (Hr)'] = tat_col

    # Calculate Row Totals
    final_df['Total Tickets'] = pivot_qty.sum(axis=1)

    # Reset index for better display
    final_df = final_df.reset_index()
    final_df.rename(columns={'Category_Mapped': 'Category', 'Company': 'Company Name'}, inplace=True)
    
    return final_df

# --- Streamlit UI Layout ---
st.title("📊 Caliper Support Performance Dashboard")
st.markdown("Upload your raw report to generate the P1-P4 Severity & TAT Analysis.")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Get unique companies for the sidebar filter
    temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    temp_df.columns = temp_df.columns.str.strip()
    all_companies = sorted(temp_df['Company'].dropna().unique().tolist())
    
    # Sidebar: Company Selection
    st.sidebar.header("Dashboard Filters")
    selected_companies = st.sidebar.multiselect(
        "Select Companies:",
        options=all_companies,
        default=all_companies
    )

    try:
        # Process and display the data
        uploaded_file.seek(0) # Reset file pointer
        report_df = process_data(uploaded_file, selected_companies)
        
        st.subheader(f"Performance Report for {len(selected_companies)} Selected Companies")
        
        # Display the table with 2 decimal places for TAT
        st.table(report_df.style.format({
            'P1 TAT (Hr)': "{:.2f}", 'P2 TAT (Hr)': "{:.2f}",
            'P3 TAT (Hr)': "{:.2f}", 'P4 TAT (Hr)': "{:.2f}",
            'P1 (Qty)': "{:.0f}", 'P2 (Qty)': "{:.0f}",
            'P3 (Qty)': "{:.0f}", 'P4 (Qty)': "{:.0f}",
            'Total Tickets': "{:.0f}"
        }))

        # Download Processed Data
        csv_data = report_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Report (CSV)",
            data=csv_data,
            file_name="Caliper_TAT_Report.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.info("Please ensure your file has columns named: 'Company', 'Severity', 'TAT', 'Status', and 'Ticket Category'.")
