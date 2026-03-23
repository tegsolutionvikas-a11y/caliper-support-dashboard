import streamlit as st
import pandas as pd
import numpy as np

# Set page configuration
st.set_page_config(page_title="Caliper Support Dashboard", layout="wide")

def process_data(file):
    # Load data (handles both CSV and Excel)
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Clean column names to avoid matching errors
    df.columns = df.columns.str.strip()

    # 1. Filter for valid tickets
    # Including "Auto Completed" as per your instruction
    df = df[df['Status'].isin(['Completed', 'Auto Completed'])]

    # 2. Map Severity to P1-P4
    # Remapping 1->P1, 2->P2, 3->P3, 4->P4
    sev_map = {1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4'}
    df['Priority_Mapped'] = df['Severity'].map(sev_map)

    # 3. Convert TAT from Minutes to Hours
    df['TAT_Hr'] = df['TAT'] / 60.0

    # 4. Map Ticket Category to Groups (Operations vs Tech)
    def map_category(cat):
        cat_str = str(cat).lower()
        if 'operations' in cat_str:
            return 'Operations'
        elif 'tech' in cat_str or 'sap response' in cat_str:
            return 'Tech'
        elif 'development' in cat_str:
            return 'Development'
        elif 'enhancement' in cat_str:
            return 'Enhancement'
        else:
            return 'Others'

    df['Category_Mapped'] = df['Ticket Category'].apply(map_category)

    # 5. Grouping and Aggregation
    # Qty Pivot
    pivot_qty = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='Ticket SR#',
        aggfunc='count'
    ).fillna(0)

    # Mean TAT Pivot
    pivot_tat = df.pivot_table(
        index=['Category_Mapped', 'Company'],
        columns='Priority_Mapped',
        values='TAT_Hr',
        aggfunc='mean'
    ).fillna(0)

    # 6. Build final table layout
    final_df = pd.DataFrame()
    priorities = ['P1', 'P2', 'P3', 'P4']
    
    for p in priorities:
        qty_col = pivot_qty[p] if p in pivot_qty.columns else 0
        tat_col = pivot_tat[p] if p in pivot_tat.columns else 0
        final_df[f'{p} (Qty)'] = qty_col
        final_df[f'{p} TAT (Hr)'] = tat_col

    # Calculate Total Tickets per row
    final_df['Total'] = pivot_qty.sum(axis=1)

    # Format the index for the dashboard
    final_df = final_df.reset_index()
    final_df.rename(columns={'Category_Mapped': 'Category', 'Company': 'Company Name'}, inplace=True)
    
    return final_df

# --- Streamlit UI ---
st.title("📊 Caliper Support Performance Dashboard")
st.markdown("Upload your raw report to generate the P1-P4 Severity & TAT Analysis.")

uploaded_file = st.file_uploader("Choose an Excel or CSV file", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:
        report_df = process_data(uploaded_file)
        
        st.subheader("Performance Matrix (By Company & Category)")
        
        # Style the table to match the requested decimal format
        styled_df = report_df.style.format({
            'P1 TAT (Hr)': "{:.2f}",
            'P2 TAT (Hr)': "{:.2f}",
            'P3 TAT (Hr)': "{:.2f}",
            'P4 TAT (Hr)': "{:.2f}",
            'P1 (Qty)': "{:.0f}",
            'P2 (Qty)': "{:.0f}",
            'P3 (Qty)': "{:.0f}",
            'P4 (Qty)': "{:.0f}",
            'Total': "{:.0f}"
        })
        
        st.table(styled_df)

        # Export button
        csv = report_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Processed Report (CSV)",
            data=csv,
            file_name="Caliper_TAT_Report.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
