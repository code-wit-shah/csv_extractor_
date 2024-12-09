import streamlit as st
import pandas as pd
import re
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Function to extract tables from the CSV file
def extract_tables_from_csv(file_path):
    df = pd.read_csv(file_path)

    non_null_counts = df.notna().sum(axis=1)
    total_columns = df.shape[1]
    non_null_percentage = (non_null_counts / total_columns) * 100
    rows_to_extract = df[non_null_percentage > 70]
    remaining_rows = df[non_null_percentage <= 70]

    if rows_to_extract.empty:
        return pd.DataFrame(), remaining_rows

    rows_to_extract.columns = rows_to_extract.iloc[0]
    rows_to_extract = rows_to_extract[1:]

    rows_to_extract.columns = [
        f"Unnamed{i+1}" if pd.isna(col) else col
        for i, col in enumerate(rows_to_extract.columns)
    ]

    columns = pd.Series(rows_to_extract.columns)
    for dup in columns[columns.duplicated()].unique():
        columns[columns[columns == dup].index.values.tolist()] = [
            f"{dup}_{i+1}" if i != 0 else dup
            for i in range(sum(columns == dup))
        ]
    rows_to_extract.columns = columns

    package_type_keywords = ['CTNS', 'QTN', 'Pellate', 'Boxes', 'Euro Pellate', 'Bags', 'Cases', 'Carton']
    rows_to_extract['Package Type'] = rows_to_extract.apply(
        lambda row: next(
            (keyword for keyword in package_type_keywords if keyword in row.to_string()),
            None
        ),
        axis=1
    )

    rows_to_extract = rows_to_extract.applymap(
        lambda x: str(x).replace("£", "").strip() if isinstance(x, str) and "£" in x else x
    )

    return rows_to_extract, remaining_rows

# Streamlit app starts here
st.title('Extracted Data Viewer')

# Upload CSV file through Streamlit
file = st.file_uploader("Upload CSV File", type=["csv"])

if file is not None:
    # Process the uploaded file
    extracted_rows, remaining_rows = extract_tables_from_csv(file)

    # Show the extracted table data in a Streamlit table
    st.subheader('Extracted Table Data')
    st.write(extracted_rows)

    # Show the remaining rows in a separate table
    st.subheader('Remaining Data')
    st.write(remaining_rows)

    # Extract form fields like Consigner Name, EORI, etc.
    results = []

    # Consigner Name and Street
    consigner_name_and_street = remaining_rows.applymap(lambda x: x if pd.notnull(x) and bool(pd.Series(x).str.contains(r'\bHoyland\b', regex=True).iloc[0]) else None)
    consigner_name_and_street.dropna(how='all', inplace=True)

    for cell in consigner_name_and_street.values.flatten():
        if pd.notna(cell):
            parts = cell.split(',', 1)
            consigner_name = parts[0].strip()
            consignee_street_name = parts[1].strip() if len(parts) > 1 else "N/A"
            st.write(f"Consigner Name: {consigner_name}")
            st.write(f"Consigner Street: {consignee_street_name}")

    # Extract and display Consigner EORI
    def extract_eori_value(text, eori_type):
        match = re.search(f'{eori_type} EORI\s+(\S+)', str(text))
        return match.group(1) if match else None

    consigner_eori_values = remaining_rows.applymap(lambda x: extract_eori_value(x, 'GEM'))
    consigner_eori_values.dropna(how='all', inplace=True)
    consigner_eori_values.dropna(axis=1, how='all', inplace=True)

    for value in consigner_eori_values.values.flatten():
        if pd.notna(value):
            st.write(f"Consigner EORI: {value}")

    # Extract VAT Number (Consigner VAT)
    def extract_vat_number(text):
        match = re.search(r'Vat No:\s+(\d+(\s\d+)*)', str(text))
        return match.group(1).replace(" ", " ") if match else None

    vat_values = remaining_rows.applymap(extract_vat_number)
    vat_values.dropna(how='all', inplace=True)
    vat_values.dropna(axis=1, how='all', inplace=True)

    for value in vat_values.values.flatten():
        if pd.notna(value):
            st.write(f"Consigner VAT No: {value}")

    # Extract Consignee Name, Street, and Country
    for i, row in remaining_rows.iterrows():
        if 'Invoice To:' in str(row[0]):
            consignee_data = remaining_rows.iloc[i+1:i+6, 0].tolist()
            consignee_name = consignee_data[0]
            consignee_street = " ".join(consignee_data[1:4])
            consignee_country = consignee_data[4]

            st.write(f"Consignee Name: {consignee_name}")
            st.write(f"Consignee Street: {consignee_street}")
            st.write(f"Consignee Country: {consignee_country}")

    # Extract and map "Country of Origin"
    def extract_and_map_text(text):
        match = re.search(r'Origin\s+(\S+)(.*)', str(text))
        if match:
            extracted_text = match.group(2).strip()
            if "China" in extracted_text:
                return "CN"
            return extracted_text
        return None

    country_of_origin_values = remaining_rows.applymap(extract_and_map_text)
    country_of_origin_values.dropna(how='all', inplace=True)
    country_of_origin_values.dropna(axis=1, how='all', inplace=True)

    for value in country_of_origin_values.values.flatten():
        if pd.notna(value):
            st.write(f"Country of Origin: {value}")

    # Extract Gross Weight (Total Gross Mass)
    def extract_gross_weight(text):
        match = re.search(r'Gross Weight\s+(\S+)', str(text))
        return match.group(1) if match else None

    gross_weight_values = remaining_rows.applymap(extract_gross_weight)
    gross_weight_values.dropna(how='all', inplace=True)
    gross_weight_values.dropna(axis=1, how='all', inplace=True)

    for value in gross_weight_values.values.flatten():
        if pd.notna(value):
            st.write(f"Total Gross Mass: {value}")

    # Extract Pallets (Total Package Quantity)
    def extract_pallets(text):
        match = re.search(r'Pallets\s+(\S+)', str(text))
        return match.group(1) if match else None

    pallets_values = remaining_rows.applymap(extract_pallets)
    pallets_values.dropna(how='all', inplace=True)
    pallets_values.dropna(axis=1, how='all', inplace=True)

    for value in pallets_values.values.flatten():
        if pd.notna(value):
            st.write(f"Total Packages: {value}")

    # Extract "Grand Total"
    results = []
    for index, row in remaining_rows.iterrows():
        for col_index, cell in enumerate(row):
            if isinstance(cell, str) and "Grand Total:" in cell:
                right_cells = row[col_index + 1:]
                last_value = right_cells.dropna().iloc[-1] if not right_cells.dropna().empty else None
                if last_value:
                    results.append(str(last_value).replace("£", "").strip())

    for res in results:
        st.write(f"Total Amount: {res}")
