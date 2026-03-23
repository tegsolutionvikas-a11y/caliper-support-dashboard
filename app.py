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

    # 1. Filter for valid tickets
    df = df[df['Status'].isin(['Completed', 'Auto Completed'])]

    # 2. Filter by Selected Companies
    if selected_companies:
        df = df[df['Company'].isin(selected_companies)]

    # 3. Map Severity to P1-P4
    sev_map = {1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'}
    df['Priority_Mapped'] = df['Severity'].map(sev_map)

    # 4. Convert TAT from Minutes to Hours
    df['TAT_Hr'] = df['TAT'] / 60.0

    # 5. Map Ticket Category
    def map_category(cat):
        cat_str = str(cat).lower()
        if 'operations' in cat_str: return 'Operations'
        elif 'tech' in cat_str or 'sap response' in cat_str: return 'Tech'
        elif 'development' in cat_str: return 'Development'
        elif 'enhancement' in cat_str: return 'Enhancement'
        else: return 'Others'

    df['Category_Mapped'] = df['Ticket Category'].apply(map_category)

    # 6. Grouping and Aggregation
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

    # 7. Build final table
    final_df = pd.DataFrame()
    priorities = ['P1', 'P2', 'P3', 'P4']
    
    for p in priorities:
        qty_col = pivot_qty[p] if p in pivot_qty.columns else 0
        tat_col = pivot_tat[p] if p in pivot_tat.columns else 0
        final_df[f'{p} (Qty)'] = qty_col
        final_df[f'{p} TAT (Hr)'] = tat_col

    final_df['Total'] = pivot_qty.sum(axis=1)
    final_df = final_df.reset_index()
    final_df.rename(columns={'Category_Mapped': 'Category', 'Company': 'Company Name'}, inplace=True)
    
    return final_df

# --- Streamlit UI ---
st.title("📊 Caliper Support Performance Dashboard")

uploaded_file = st.file_uploader("Upload Caliper Report", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # Peek at the file to get unique companies for the sidebar
    temp_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    temp_df.columns = temp_df.columns.str.strip()
    available_companies = sorted(temp_df['Company'].dropna().unique().tolist())
    
    # Sidebar Filter
    st.sidebar.header("Filter Options")
    selected_companies = st.sidebar.multiselect(
        "Select Companies to View:",
        options=available_companies,
        default=available_companies
    )

    try:
        # Reset file pointer for processing
        uploaded_file.seek(0)
        report_df = process_data(uploaded_file, selected_companies)
        
        st.subheader(f"Performance Matrix for {len(selected_companies)} Selected Companies")
        
        # Display table
        st.table(report_df.style.format({
            'P1 TAT (Hr)': "{:.2f}", 'P2 TAT (Hr)': "{:.2f}",
            'P3 TAT (Hr)': "{:.2f}", 'P4 TAT (Hr)': "{:.2f}",
            'P1 (Qty)': "{:.0f}", 'P2 (Qty)': "{:.0f}",
            'P3 (Qty)': "{:.0f}", 'P4 (Qty)': "{:.0f}",
            'Total': "{:.0f}"
        }))

        # Download
        st.download_button("📥 Download Filtered CSV", report_df.to_csv(index=False), "Caliper_Filtered.csv")

    except Exception as e:
        st.error(f"Error: {e}")
