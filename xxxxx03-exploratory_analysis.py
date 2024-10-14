import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# Read the combined dataset
df = pd.read_csv('data/combined.tsv', sep='\t')
print(f"Total columns in the dataset: {len(df.columns)}")

# Read the domain map
domain_map = pd.read_csv('reference/domain_map.tsv', sep='\t')

# Get the list of columns that exist in the dataset
columns_to_analyze = [col for col in domain_map['Column Name'] if col in df.columns]

# Group columns by domain
domain_groups = domain_map.groupby('Domain')['Column Name'].apply(lambda x: [col for col in x if col in df.columns]).to_dict()

# Explore the data by domain across surveys
for domain, columns in domain_groups.items():
    print(f"\nDomain: {domain}")
    domain_df = df[columns + ['survey']]
    
    # Check data types
    print("\nData types:")
    print(domain_df.dtypes)
    
    # Check unique values for categorical columns
    cat_columns = domain_df.select_dtypes(include=['int64']).columns
    for column in cat_columns:
        print(f"\nColumn: {column}")
        print(domain_df[column].value_counts())
    
    # Check missing values
    missing_values = domain_df.isnull().sum()
    if missing_values.sum() > 0:
        print("\nMissing values:")
        print(missing_values)
    
    # Plot distributions for numerical columns
    num_columns = domain_df.select_dtypes(include=['float64']).columns
    for column in num_columns:
        print(f"\nColumn: {column}")
        sns.histplot(data=domain_df, x=column, hue='survey', kde=True)
        plt.title(f"Distribution of {column} by survey")
        