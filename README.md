# SDF → CSV + Pharmacology Merger

### *A Streamlit App for Integrating Chemical Structure Files with Biological Activity Data*

This Streamlit application allows users to:

* Upload one or more **SDF files** containing ligand structures
* Upload a **pharmacology Excel file** with activity measurements
* Automatically extract all molecular properties + SMILES
* Merge SDF data with pharmacology data using **CAS numbers**
* Generate:

  * A **full merged CSV** with all pharmacology aggregated by CAS
  * A **parameter-focused CSV** (e.g., IC50, MIC, EC50) containing only ligands that have values for the selected parameter

Useful for cheminformatics workflows, activity databases, and screening studies.

---

## Features

### ✔ Extracts all properties from SDF files

RDKit reads every available property field and converts it into a table.

### ✔ Merges pharmacology data via CAS

The app identifies *Ligand CAS RN* inside the Excel file and matches it to `cas.rn` from the SDF.

### ✔ Automatically detects available pharmacology **Parameters**

Examples: IC50, MIC, EC50, Ki, LD50...

User selects the parameter from a **dropdown**.

### ✔ Parameter-specific export

Produces a clean CSV containing:

| SMILES | cas.index.name | cas.rn | Parameter | Value |

Only ligands with valid values for that parameter are included.

### ✔ Correct file naming

Outputs are automatically prefixed using the uploaded `.sdf` filename:

```
MyLigands_Ligands_with_Pharmacology_aggregated_by_CAS.csv
MyLigands_IC50_summary.csv
```

---

## Installation

It is recommended to use **Conda**.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

### 2. Create and activate environment

```bash
conda create -n sdfmerge python=3.10 -y
conda activate sdfmerge
```

### 3. Install dependencies

```bash
pip install streamlit pandas rdkit-pypi openpyxl
```

(On some systems RDKit must be installed via Conda.)

---

## Running the Application

Inside the project folder:

```bash
streamlit run app.py
```

Streamlit will open automatically at:

```
http://localhost:8501
```

---

# Tutorial

This section walks through a complete workflow using screenshots.

---

## **Step 1 — Upload SDF File(s)**

Upload one or more `.sdf` structure files using the sidebar:

```
📁 Upload SDF file(s)
```

Each molecule is parsed using RDKit and all properties are extracted.

---

## **Step 2 — Upload Pharmacology Excel File**

Upload an Excel file formatted like:

| Ligand CAS RN | Parameter | Value | Target | Organism | Notes |
| ------------- | --------- | ----- | ------ | -------- | ----- |

**Important:**
The header row in the Excel file must contain the text `"Ligand CAS RN"`.

The app automatically finds this row and uses it as the header.

---

## **Step 3 — Select Parameter to Export**

Once the Excel file loads, a dropdown appears:

```
Select Parameter to export:
[ IC50 ▼ ]
```

This list is generated from all unique values in the `"Parameter"` column.

---

## **Step 4 — View and Download Outputs**

### **A. Full merged table**

This table contains:

* 1 row per ligand in the SDF
* All SDF fields
* All pharmacology values aggregated by CAS (multiple entries combined using `|`)

Download:

```
<MyPrefix>_Ligands_with_Pharmacology_aggregated_by_CAS.csv
```

---

### **B. Parameter-focused table**

Only rows where the selected parameter exists and has a value.

Example (IC50):

| SMILES | cas.index.name | cas.rn | Parameter | Value |
| ------ | -------------- | ------ | --------- | ----- |

Download:

```
<MyPrefix>_IC50_summary.csv
```

---

# 📁 Output Files

### 1. **Full merged CSV**

```
<Prefix>_Ligands_with_Pharmacology_aggregated_by_CAS.csv
```

Contains:

* All ligands from SDF
* All pharmacology aggregated per CAS
* All Excel columns preserved

---

### 2. **Parameter-focused CSV**

```
<Prefix>_<Parameter>_summary.csv
```

Contains:

* Only entries with a match for the selected parameter
* Useful for QSAR, docking benchmarks, ML model training, etc.

---

# How Filename Prefixing Works

If you upload:

* `MyLigands.sdf` → prefix is `"MyLigands"`
* Multiple files (`A.sdf`, `B.sdf`) → prefix is `"A_and_others"`

Spaces are automatically replaced with underscores.

---

# Technologies Used

* **Python + RDKit** for cheminformatics
* **Pandas** for data processing
* **Streamlit** for the interactive web UI

---

# 📄 License

MIT License — modify and reuse freely.

---

# Citation (optional)

If you use this tool in academic work:

```
Borges, R. (2025). SDF → CSV + Pharmacology Merger Tool. 
GitHub Repository: https://github.com/YOUR_USERNAME/YOUR_REPO_NAME
```
