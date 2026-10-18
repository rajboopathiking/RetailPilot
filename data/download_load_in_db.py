import kagglehub
import pandas as pd
from pathlib import Path

# Download public dataset
path = kagglehub.dataset_download(
    "s26sharma/customer-dataset"
)

# Find the CSV file
csv_files = list(Path(path).rglob("*.csv"))

if not csv_files:
    raise FileNotFoundError("No CSV files found")

# Prefer the Customer Analysis CSV
csv_file = next(
    (f for f in csv_files if f.name == "Customer Analysis.csv"),
    csv_files[0]
)

df = pd.read_csv(csv_file)

# Fix whitespace in column names
df.columns = df.columns.str.strip()

def data_store(n:int):
    return df[:n]


import json
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from data import df,engine

# Clean column names
df.columns = df.columns.str.strip()

df.to_sql(
    "customers",
    engine,
    if_exists="append",
    chunksize=10
)