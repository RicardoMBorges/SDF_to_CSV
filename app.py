import io
import streamlit as st
import pandas as pd
from rdkit import Chem
from pathlib import Path  # NEW: for getting the filename prefix

st.title("SDF → CSV + Pharmacology Merger (1 row per ligand + parameter export)")

st.write(
    """
    **Starting point:**
    1. https://biofinder.cas.org/
    2. 
    3. 
    4. 
    5. 
    
    
    **Workflow**


    1. Upload one or more `.sdf` files (ligands).  
    2. Optionally upload the pharmacology Excel file (`Ligand_Pharmacology_Data_C_ATCC.xlsx`).  
    3. I will:
       - Extract all SDF properties + SMILES  
       - Merge with pharmacology data using CAS (`cas.rn` ↔ `Ligand CAS RN`)  
       - Keep **each column from the Excel file as a separate column**  
       - Generate:
         - A full merged table (1 row per ligand, CAS-aggregated pharmacology)  
         - A second table filtered by a **selected Parameter** (e.g. IC50, MIC, EC50) with:  
           `SMILES`, `cas.index.name`, `cas.rn`, `Parameter`, `Value`.
    """
)

# ---------------- SIDEBAR: INPUTS ----------------
st.sidebar.header("Inputs")

uploaded_sdf_files = st.sidebar.file_uploader(
    "Upload SDF file(s)", type=["sdf"], accept_multiple_files=True
)

uploaded_pharm_file = st.sidebar.file_uploader(
    "Upload pharmacology Excel file (optional)", type=["xlsx"]
)

# --- HELPER: LOAD PHARMACOLOGY EXCEL WITH HEADER ROW DETECTION ---
def load_pharmacology_excel(file) -> pd.DataFrame:
    """
    Reads the Excel file where the real header row contains 'Ligand CAS RN'
    and returns a clean dataframe with that row as header.
    Each original column remains a separate column.
    """
    raw = pd.read_excel(file, header=None)

    # Find the row where column 0 == 'Ligand CAS RN'
    header_row_idx = raw.index[raw.iloc[:, 0] == "Ligand CAS RN"][0]
    new_header = raw.iloc[header_row_idx]

    pharm = raw[header_row_idx + 1 :].copy()
    pharm.columns = new_header
    pharm = pharm.reset_index(drop=True)

    return pharm

# ---------------- SIDEBAR: PARAMETER SELECTION ----------------
selected_param = None
pharm_param_options = []

if uploaded_pharm_file is not None:
    try:
        # We can reuse this later; but here we only need the Parameter column for choices
        pharm_preview = load_pharmacology_excel(uploaded_pharm_file)
        if "Parameter" in pharm_preview.columns:
            pharm_param_options = (
                pharm_preview["Parameter"]
                .dropna()
                .astype(str)
                .sort_values()
                .unique()
                .tolist()
            )
    except Exception as e:
        st.sidebar.warning(f"Could not read pharmacology file yet: {e}")

if pharm_param_options:
    # Prefer IC50 as default if present
    default_index = pharm_param_options.index("IC50") if "IC50" in pharm_param_options else 0
    selected_param = st.sidebar.selectbox(
        "Select Parameter to export",
        options=pharm_param_options,
        index=default_index,
        help="This will be used to build the second, parameter-focused table.",
    )
else:
    st.sidebar.info("Upload pharmacology Excel to select a Parameter (e.g. IC50, MIC, EC50).")


# --- HELPER: AGGREGATE PHARMACOLOGY BY CAS (COLUMN-WISE) ---
def aggregate_pharmacology_by_cas(pharm_df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups pharmacology records by CAS (cas_norm).
    For each non-CAS column, concatenates unique non-null values as 'v1 | v2 | v3'.
    Each original column stays as a separate column in the aggregated table.
    """
    # Ensure we have a normalized CAS column
    if "cas_norm" not in pharm_df.columns:
        pharm_df["cas_norm"] = pharm_df["Ligand CAS RN"].astype(str).str.strip()

    def agg_unique(series: pd.Series):
        vals = series.dropna().astype(str).unique()
        return " | ".join(vals) if len(vals) > 0 else None

    grouped = (
        pharm_df.groupby("cas_norm", dropna=False)
        .agg(agg_unique)
        .reset_index()
    )

    return grouped


# ---------------- MAIN LOGIC ----------------
if uploaded_sdf_files:
    all_mols = []
    file_tags = []

    # --- Decide filename prefix from SDF uploads ---
    if len(uploaded_sdf_files) == 1:
        prefix = Path(uploaded_sdf_files[0].name).stem
    else:
        # Use first filename + "_and_others" as prefix for multi-file runs
        first_stem = Path(uploaded_sdf_files[0].name).stem
        prefix = f"{first_stem}_and_others"
    prefix = prefix.replace(" ", "_")  # sanitize spaces

    # --- Read molecules from each uploaded SDF ---
    for up_file in uploaded_sdf_files:
        sdf_bytes = up_file.read()
        bio = io.BytesIO(sdf_bytes)

        suppl = Chem.ForwardSDMolSupplier(bio, sanitize=True)
        mols = [m for m in suppl if m is not None]

        all_mols.extend(mols)
        file_tags.extend([up_file.name] * len(mols))

    if not all_mols:
        st.error("No valid molecules were found in the uploaded SDF file(s).")
    else:
        # --- Collect all SDF property names ---
        all_props = sorted({p for m in all_mols for p in m.GetPropNames()})

        # --- Build SDF dataframe ---
        sdf_rows = []
        for idx, (m, src_name) in enumerate(zip(all_mols, file_tags), start=1):
            row = {"ID": idx, "SourceFile": src_name}

            # SMILES
            try:
                row["SMILES"] = Chem.MolToSmiles(m)
            except Exception:
                row["SMILES"] = None

            # SDF properties
            for p in all_props:
                row[p] = m.GetProp(p) if m.HasProp(p) else None

            sdf_rows.append(row)

        sdf_df = pd.DataFrame(sdf_rows)

        st.success(f"Parsed {len(all_mols)} molecules from {len(uploaded_sdf_files)} SDF file(s).")

        # Normalize SDF CAS for merging
        if "cas.rn" in sdf_df.columns:
            sdf_df["cas_norm"] = sdf_df["cas.rn"].astype(str).str.strip()
        else:
            sdf_df["cas_norm"] = None
            st.warning("Column 'cas.rn' not found in SDF properties; CAS-based merge may be empty.")

        merged_full_df = sdf_df.copy()
        param_df_export = None  # will hold the Parameter-focused table

        # --- If pharmacology file provided, aggregate by CAS and merge ---
        if uploaded_pharm_file is not None:
            pharm_df = load_pharmacology_excel(uploaded_pharm_file)

            # Normalize CAS in pharmacology table
            pharm_df["cas_norm"] = pharm_df["Ligand CAS RN"].astype(str).str.strip()

            # 1) FULL MERGED TABLE (1 ROW PER LIGAND, PHARMACOLOGY AGGREGATED BY CAS)
            pharm_agg = aggregate_pharmacology_by_cas(pharm_df)

            merged_full_df = merged_full_df.merge(
                pharm_agg,
                on="cas_norm",
                how="left",
                suffixes=("", "_pharm"),
            )

            st.info(
                "Pharmacology file merged using CAS with **aggregation per CAS**: "
                "`cas.rn` (SDF) ↔ `Ligand CAS RN` (Excel).\n\n"
                "Each original Excel column remains a separate column. "
                "If a CAS has multiple pharmacology records, the unique entries for each column "
                "are combined as `value1 | value2 | ...`."
            )

            # 2) PARAMETER-FOCUSED TABLE (MULTIPLE ROWS PER LIGAND POSSIBLE)
            if selected_param and "Parameter" in pharm_df.columns and "Value" in pharm_df.columns:
                # Exact match on the selected parameter (case-insensitive)
                param_series = pharm_df["Parameter"].astype(str)
                mask = param_series.str.lower() == selected_param.lower()

                pharm_param = pharm_df[mask].copy()

                if not pharm_param.empty:
                    # Merge parameter pharmacology with key ligand columns
                    base_cols = ["SMILES", "cas.index.name", "cas.rn", "cas_norm"]
                    for col in base_cols:
                        if col not in sdf_df.columns:
                            sdf_df[col] = None

                    param_df_export = sdf_df[base_cols].merge(
                        pharm_param[["cas_norm", "Parameter", "Value"]],
                        on="cas_norm",
                        how="left",
                    )

                    # Remove helper
                    param_df_export = param_df_export.drop(columns=["cas_norm"])

                    # Keep only rows where the parameter exists and has a value
                    param_df_export = param_df_export[
                        param_df_export["Parameter"].notna()
                        & param_df_export["Value"].notna()
                    ].reset_index(drop=True)

                    st.success(
                        f"'{selected_param}' table created with {len(param_df_export)} rows "
                        "(one row per pharmacology record matching a ligand CAS)."
                    )
                else:
                    st.warning(
                        f"No rows with Parameter == '{selected_param}' found in the pharmacology file."
                    )
            elif uploaded_pharm_file is not None and not selected_param:
                st.warning("No Parameter selected; parameter-focused table not created.")
            else:
                if uploaded_pharm_file is not None and "Parameter" not in pharm_df.columns:
                    st.warning("Column 'Parameter' not found in the pharmacology file — parameter-focused table not created.")
        else:
            st.info("No pharmacology file uploaded — showing only SDF-derived data (no parameter-focused table).")

        # --- Show preview of full merged table ---
        st.subheader("Full merged table (SDF + aggregated pharmacology)")
        st.dataframe(merged_full_df.head(50))
        st.write("Rows × Columns:", merged_full_df.shape)

        # --- Download full merged table ---
        full_csv_bytes = merged_full_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download FULL merged CSV",
            data=full_csv_bytes,
            file_name=f"{prefix}_Ligands_with_Pharmacology_aggregated_by_CAS.csv",
            mime="text/csv",
        )

        # --- If parameter-focused table available, show and offer download ---
        if param_df_export is not None:
            st.subheader(f"'{selected_param}'-focused table")
            st.dataframe(param_df_export.head(50))
            st.write("Rows × Columns:", param_df_export.shape)

            param_csv_bytes = param_df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"Download '{selected_param}'-focused CSV",
                data=param_csv_bytes,
                file_name=f"{prefix}_{selected_param}_summary.csv".replace(" ", "_"),
                mime="text/csv",
            )

else:
    st.info("Please upload at least one `.sdf` file to begin.")
