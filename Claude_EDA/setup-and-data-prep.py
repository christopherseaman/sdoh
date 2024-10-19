import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from ydata_profiling import ProfileReport
from jinja2 import Environment, FileSystemLoader
import json
import os

# Import the load_data function from utils
from utils import load_data

# Load the data and data dictionary using the provided function
df, data_dict = load_data()

# Load domain map
domain_map = pd.read_csv('reference/domain_map.tsv', sep='\t')

# Function to get all related columns for an item
def get_related_columns(item):
    related_cols = domain_map[domain_map['item'] == item]['column_name'].tolist()
    exploded_cols = []
    for col in related_cols:
        if col in data_dict and 'exploded_fields' in data_dict[col]:
            exploded_cols.extend(data_dict[col]['exploded_fields'])
        else:
            exploded_cols.append(col)
    return exploded_cols

# Function to generate summary for an item
def generate_item_summary(df, item):
    columns = get_related_columns(item)
    summary = {}
    for col in columns:
        if col in df.columns:
            if df[col].dtype.name == 'category' or df[col].dtype == bool:
                summary[col] = df[col].value_counts(normalize=True).to_dict()
            elif np.issubdtype(df[col].dtype, np.number):
                summary[col] = df[col].describe().to_dict()
            else:
                summary[col] = df[col].describe().to_dict()
    return summary

# Generate summaries for all items
all_summaries = {}
for domain in domain_map['domain'].unique():
    domain_items = domain_map[domain_map['domain'] == domain]['item'].unique()
    all_summaries[domain] = {item: generate_item_summary(df, item) for item in domain_items}

# Print a sample summary to verify
sample_domain = list(all_summaries.keys())[0]
sample_item = list(all_summaries[sample_domain].keys())[0]
print(f"Sample summary for {sample_domain} - {sample_item}:")
print(json.dumps(all_summaries[sample_domain][sample_item], indent=2))

# Print info about the dataset
print(f"\nDataset info:")
print(f"Number of rows: {len(df)}")
print(f"Number of columns: {len(df.columns)}")
print(f"Cohorts (survey): {df['survey'].value_counts().to_dict()}")
