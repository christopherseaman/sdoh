import pandas as pd
import numpy as np
import os
import json

DATA_DIR = 'data'
RAW_DIR = os.path.join(DATA_DIR, 'raw')

def load_data():
    # Load the combined TSV file
    df = pd.read_csv(os.path.join(DATA_DIR, 'combined.tsv'), sep='\t')
    
    # Load the data dictionary
    with open('reference/data_dictionary.json', 'r') as f:
        data_dictionary = json.load(f)
    
    # Apply data types and categories based on data dictionary
    for column, info in data_dictionary.items():
        if column == 'survey':
            continue
        
        field_type = info['type']
        
        if field_type == 'checkbox':
            # For checkbox fields, look for the exploded columns
            checkbox_columns = [col for col in df.columns if col.startswith(f"{column}___")]
            for checkbox_col in checkbox_columns:
                df[checkbox_col] = df[checkbox_col].astype(bool)
        elif column in df.columns:
            if field_type in ['radio', 'dropdown']:
                df[column] = pd.Categorical(df[column])
            elif field_type == 'text':
                df[column] = df[column].astype(str)
            elif field_type in ['number', 'calc']:
                df[column] = pd.to_numeric(df[column], errors='coerce')
            elif field_type == 'yesno':
                df[column] = df[column].map({'1': True, '0': False})
            elif field_type == 'date_ymd':
                df[column] = pd.to_datetime(df[column], errors='coerce')
    
    return df, data_dictionary

def in_notebook():
    try:
        from IPython import get_ipython
        if 'IPKernelApp' not in get_ipython().config:
            return False
    except ImportError:
        return False
    except AttributeError:
        return False
    return True
