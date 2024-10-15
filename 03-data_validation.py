import pandas as pd
import os

# Constants
DATA_DIR = 'data'

# Load TSV files
data = {}
for file in os.listdir(DATA_DIR):
    if file.endswith('.tsv'):
        key = file.split('.')[0]
        data[key] = pd.read_csv(os.path.join(DATA_DIR, file), sep='\t')
        print(f"Loaded: {file}")

# Combine datasets
combined_data = pd.concat(data.values(), keys=data.keys())
print(f"Combined dataset shape: {combined_data.shape}")

# Function to check column data types
def check_column_types(df):
    return df.dtypes

# Check column types for each survey
for key, df in data.items():
    print(f"\nColumn types for {key}:")
    print(check_column_types(df))

# Function to get unique categories for categorical columns
def get_unique_categories(df):
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns
    return {col: set(df[col].unique()) for col in categorical_columns}

# Compare categories across surveys
all_categories = {}
for key, df in data.items():
    categories = get_unique_categories(df)
    for col, cats in categories.items():
        if col not in all_categories:
            all_categories[col] = {}
        all_categories[col][key] = cats

# Find categories that exist in one survey but not in others
print("\nCategories that exist in one survey but not in others:")
for col, survey_cats in all_categories.items():
    all_cats = set.union(*survey_cats.values())
    for survey, cats in survey_cats.items():
        diff = all_cats - cats
        if diff:
            print(f"Column: {col}, Survey: {survey}, Missing categories: {diff}")
