import pandas as pd
import numpy as np

# Load the combined TSV file
df = pd.read_csv('data/combined.tsv', sep='\t')

def check_data_types(df):
    # Group by survey and check data types
    type_consistency = {}
    for survey in df['survey'].unique():
        survey_df = df[df['survey'] == survey]
        types = survey_df.dtypes
        type_consistency[survey] = types
    
    # Compare data types across surveys
    inconsistent_columns = []
    for column in df.columns:
        if column != 'survey':
            column_types = set([str(type_consistency[survey][column]) for survey in type_consistency])
            if len(column_types) > 1:
                inconsistent_columns.append(column)
    
    return inconsistent_columns

def find_category_superset(df, column):
    return set.union(*[set(df[df['survey'] == survey][column].unique()) for survey in df['survey'].unique()])

def check_categories(df):
    # Identify categorical columns (integers)
    cat_columns = df.select_dtypes(include=['int64']).columns
    
    # Check categories for each categorical column
    inconsistent_categories = {}
    for column in cat_columns:
        superset = find_category_superset(df, column)
        categories = {}
        for survey in df['survey'].unique():
            survey_categories = set(df[df['survey'] == survey][column].unique())
            if not survey_categories.issubset(superset):
                categories[survey] = survey_categories
        
        if categories:
            inconsistent_categories[column] = categories
    
    return inconsistent_categories

# Perform checks
inconsistent_data_types = check_data_types(df)
inconsistent_categories = check_categories(df)

# Save all columns data types and categories to a file
with open('reference/data_types.tsv', 'w') as f:
    f.write("Column\tData Type\n")
    for column in df.columns:
        f.write(f"{column}\t{df[column].dtype}\n")
    print("Data types saved to reference/data_types.tsv")

# Print results
print("Columns with inconsistent data types across surveys:")
for column in inconsistent_data_types:
    print(f"- {column}")

print("\nCategorical columns with inconsistent categories (not subset of superset):")
for column, categories in inconsistent_categories.items():
    print(f"- {column}:")
    superset = find_category_superset(df, column)
    print(f"  Superset: {superset}")
    for survey, cats in categories.items():
        print(f"  {survey}: {cats} (Difference: {cats - superset})")
