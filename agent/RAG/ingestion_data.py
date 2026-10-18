import pandas as pd

from pathlib import Path

file_path = Path(__name__).resolve().parent

data_path = file_path/"data/retailpilot_case/data/knowledge_base.csv"

print(data_path)

kb = pd.read_csv(data_path)

print(kb.info())