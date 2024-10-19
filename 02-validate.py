import pandas as pd
import numpy as np
import json
from utils import load_data

# Load the data and data dictionary
df, data_dictionary = load_data()

def check_data_types(df, data_dictionary):
    inconsistencies = []
    for column in df.columns:
        if column in data_dictionary:
            expected_type = data_dictionary[column]['type']
            actual_type = df[column].dtype
            if not type_matches(expected_type, actual_type):
                inconsistencies.append(f"Column '{column}': Expected {expected_type}, got {actual_type}")
    return inconsistencies

def type_matches(expected_type, actual_type):
    if expected_type in ['radio', 'dropdown', 'checkbox', 'checkbox_option']:
        return isinstance(actual_type, pd.CategoricalDtype) or pd.api.types.is_bool_dtype(actual_type)
    elif expected_type == 'text':
        return pd.api.types.is_string_dtype(actual_type)
    elif expected_type in ['number', 'calc']:
        return pd.api.types.is_numeric_dtype(actual_type)
    elif expected_type == 'yesno':
        return pd.api.types.is_bool_dtype(actual_type)
    elif expected_type == 'date_ymd':
        return pd.api.types.is_datetime64_any_dtype(actual_type)
    return True  # Default to True for unknown types

def check_value_ranges(df, data_dictionary):
    inconsistencies = []
    for column, info in data_dictionary.items():
        if column in df.columns and info['type'] in ['radio', 'dropdown']:
            valid_values = set(int(key) for key in info['value_labels'].keys() if info['value_labels'])
            actual_values = set(df[column].dropna().unique())
            
            # Convert float values to int if they're whole numbers
            actual_values = {int(val) if isinstance(val, float) and val.is_integer() else val for val in actual_values}
            
            invalid_values = actual_values - valid_values
            if invalid_values:
                inconsistencies.append(f"Column '{column}': Invalid values found: {invalid_values}")
    return inconsistencies

def check_checkbox_consistency(df, data_dictionary):
    inconsistencies = []
    for column, info in data_dictionary.items():
        if info.get('type') == 'checkbox':
            expected_fields = [f"{column}___{key}" for key in info.get('value_labels', {}).keys()]
            actual_fields = [col for col in df.columns if col.startswith(f"{column}___")]
            
            unexpected_fields = set(actual_fields) - set(expected_fields)
            if unexpected_fields:
                inconsistencies.append(f"Checkbox field '{column}' has unexpected exploded fields: {unexpected_fields}")
            
            for field in actual_fields:
                if not pd.api.types.is_bool_dtype(df[field]):
                    inconsistencies.append(f"Exploded checkbox field '{field}' is not boolean type")
    
    return inconsistencies

def check_missing_columns(df, data_dictionary):
    missing_columns = []
    for column, info in data_dictionary.items():
        if info.get('exploding'):  # Check for non-standard exploding first
            if 'exploded_fields' in info:
                expected_columns = info['exploded_fields']
                missing = [col for col in expected_columns if col not in df.columns]
                if missing:
                    missing_columns.append(f"Non-standard exploding field '{column}' is missing exploded fields: {missing}")
            else:
                print(f"Warning: {column} is marked as exploding but does not have 'exploded_fields' defined in the data dictionary.")
        elif info.get('is_checkbox'):  # Then check for standard checkboxes
            if 'exploded_fields' in info:
                expected_columns = info['exploded_fields']
                missing = [col for col in expected_columns if col not in df.columns]
                if missing:
                    missing_columns.append(f"Checkbox field '{column}' is missing exploded fields: {missing}")
            else:
                print(f"Warning: {column} is marked as checkbox but does not have 'exploded_fields' defined in the data dictionary.")
        elif column not in df.columns:
            missing_columns.append(column)
    return missing_columns

# Perform checks
data_type_inconsistencies = check_data_types(df, data_dictionary)
value_range_inconsistencies = check_value_ranges(df, data_dictionary)
checkbox_inconsistencies = check_checkbox_consistency(df, data_dictionary)
missing_columns = check_missing_columns(df, data_dictionary)

# Print results
if data_type_inconsistencies:
    print("\nData type inconsistencies:")
    for inconsistency in data_type_inconsistencies:
        print(f"- {inconsistency}")
else:
    print("\nData type inconsistencies: None")

if value_range_inconsistencies:
    print("\nValue range inconsistencies:")
    for inconsistency in value_range_inconsistencies:
        print(f"- {inconsistency}")
else:
    print("\nValue range inconsistencies: None")

if checkbox_inconsistencies:
    print("\nCheckbox inconsistencies:")
    for inconsistency in checkbox_inconsistencies:
        print(f"- {inconsistency}")
else:
    print("\nCheckbox inconsistencies: None")

if missing_columns:
    print("\nMissing columns:")
    for column in missing_columns:
        print(f"- {column}")
else:
    print("\nMissing columns: None")

print("\n")