import streamlit as st
import pandas as pd
import re

# Streamlit App
st.title("CSV Data Extraction and Transformation Tool")

# File upload
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Uploaded Data:")
    st.dataframe(df)

    def extract_tables_from_csv(dataframe):
        non_null_counts = dataframe.notna().sum(axis=1)
        total_columns = dataframe.shape[1]
        non_null_percentage = (non_null_counts / total_columns) * 100
        rows_to_extract = dataframe[non_null_percentage > 70]
        remaining_rows = dataframe[non_null_percentage <= 70]

        if rows_to_extract.empty:
            st.warning("No rows with more than 70% non-null values found.")
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

        package_type_keywords = [
            'CTNS', 'QTN', 'Pellate', 'Boxes', 
            'Euro Pellate', 'Bags', 'Cases', 'Carton'
        ]
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

    extracted_rows, remaining_rows = extract_tables_from_csv(df)
    
    if not extracted_rows.empty:
        st.write("Extracted Rows:")
        st.dataframe(extracted_rows)
    else:
        st.warning("No rows extracted.")

    # Process remaining rows
    if not remaining_rows.empty:
        st.write("Remaining Rows:")
        st.dataframe(remaining_rows)

        # Consigner Name and Street
        consigner_name_and_street = remaining_rows.applymap(
            lambda x: x if pd.notnull(x) and bool(
                pd.Series(x).str.contains(r'\bHoyland\b', regex=True).iloc[0]
            ) else None
        )
        consigner_name_and_street.dropna(how="all", inplace=True)

        st.subheader("Consigner Name and Street:")
        for cell in consigner_name_and_street.values.flatten():
            if pd.notna(cell):
                parts = cell.split(',', 1)
                consigner_name = parts[0].strip()
                consignee_street_name = parts[1].strip() if len(parts) > 1 else "N/A"
                st.write(f"Consigner : {consigner_name}")
                st.write(f"Consigner Street : {consignee_street_name}")

        # EORI Extraction
        def extract_eori_value(text, eori_type):
            match = re.search(f'{eori_type} EORI\\s+(\\S+)', str(text))
            return match.group(1) if match else None

        consigner_eori_values = remaining_rows.applymap(lambda x: extract_eori_value(x, 'GEM'))
        consigner_eori_values.dropna(how="all", inplace=True)

        st.subheader("Consigner EORI:")
        for value in consigner_eori_values.values.flatten():
            if pd.notna(value):
                st.write(f"Consigner EORI: {value}")

        # VAT Number Extraction
        def extract_vat_number(text):
            match = re.search(r'Vat No:\\s+(\\d+(\\s\\d+)*)', str(text))
            return match.group(1) if match else None

        vat_values = remaining_rows.applymap(extract_vat_number)
        vat_values.dropna(how="all", inplace=True)

        st.subheader("Consigner VAT Number:")
        for value in vat_values.values.flatten():
            if pd.notna(value):
                st.write(f"Consigner VAT No: {value}")

        # Invoice Number
        st.subheader("Invoice Numbers:")
        invoice_numbers = []
        for index, row in remaining_rows.iterrows():
            for col_index, cell in enumerate(row):
                if isinstance(cell, str) and "Invoice Number:" in cell:
                    if col_index + 2 < len(row):
                        result = [value for value in row[col_index + 1: col_index + 3] if pd.notna(value) and value != ""]
                        if result:
                            invoice_numbers.append(result)

        for res in invoice_numbers:
            st.write(f"Invoice Number: {res[0]}")

        # Gross Weight Extraction
        def extract_gross_weight(text):
            match = re.search(r'Gross Weight\\s+(\\S+)', str(text))
            return match.group(1) if match else None

        gross_weight_values = remaining_rows.applymap(extract_gross_weight)
        gross_weight_values.dropna(how="all", inplace=True)

        st.subheader("Gross Weights:")
        for value in gross_weight_values.values.flatten():
            if pd.notna(value):
                st.write(f"H-total gross mass: {value}")

        # Country of Origin
        def extract_and_map_text(text):
            match = re.search(r'Origin\\s+(\\S+)(.*)', str(text))
            if match:
                extracted_text = match.group(2).strip()
                if "China" in extracted_text:
                    return "CN"
                return extracted_text
            return None

        country_values = remaining_rows.applymap(extract_and_map_text)
        country_values.dropna(how="all", inplace=True)

        st.subheader("Country of Origin:")
        for value in country_values.values.flatten():
            if pd.notna(value):
                st.write(f"H_Country_of_origin: {value}")
else:
    st.info("Please upload a CSV file to begin.")
