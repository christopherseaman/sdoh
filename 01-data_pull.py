#!/bin/env python3

from dotenv import load_dotenv
from utils import in_notebook
import os
from redcap import Project
import pandas as pd
import re
import json
import git

# Get the repository root directory
git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
git_root = git_repo.git.rev_parse("--show-toplevel")

# Constants
JUPYTER = in_notebook()
DEBUG = False
DATA = os.path.join(git_root, 'data')
os.makedirs(DATA, exist_ok=True)
os.makedirs(f'{DATA}/raw', exist_ok=True)

# Construct the path to dot.env
dotenv_path = os.path.join(git_root, 'dot.env')

if os.path.exists(dotenv_path):
    print(f"dot.env file found at {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    raise Exception(f"dot.env file not found at {dotenv_path}")

api_url = os.getenv('API_URL')
token = json.loads(os.getenv('API_TOKEN'))

# data['key'] = DataFrame
data = {}

def strip_html(text):
    return re.sub('<[^<]+?>', '', text)

# Check if CSVs exist; if not, download from REDCap
for key in token:
    if os.path.exists(f"{DATA}/raw/{key}.tsv"):
        data[key] = pd.read_csv(f"{DATA}/raw/{key}.tsv", sep='\t')
        data[key] = pd.read_csv(f"{DATA}/raw/{key}.tsv", sep='\t')
        print(f"Loaded: {key}.tsv")
    else:
        try:
            api_key = token[key]
            project = Project(api_url, api_key)
            
            # Get metadata
            metadata = project.export_metadata()
            
            # Strip HTML from field labels
            for field in metadata:
                field['field_label'] = strip_html(field['field_label'])
            
            field_names = [field['field_name'] for field in metadata]
            
            # Export records with specific fields
            data[key] = pd.DataFrame(project.export_records(fields=field_names))
            
            # Create a dictionary for value labels
            value_labels = {}
            for field in metadata:
                if field['field_type'] in ['radio', 'dropdown', 'checkbox']:
                    field_name = field['field_name']
                    value_labels[field_name] = {}
                    choices = field['select_choices_or_calculations'].split('|')
                    for choice in choices:
                        value, label = choice.strip().split(',', 1)
                        value_labels[field_name][value.strip()] = label.strip()
            
            # Save metadata with stripped HTML and value labels
            metadata_df = pd.DataFrame(metadata)
            metadata_df['value_labels'] = metadata_df['field_name'].map(value_labels)
            metadata_df.to_csv(f"{DATA}/raw/{key}_metadata.tsv", index=False, sep='\t')
            print(f"Saved: {key}_metadata.tsv")
            
            # Save data
            data[key].to_csv(f"{DATA}/raw/{key}.tsv", index=False, sep='\t')
            print(f"Saved: {key}.tsv")
        except Exception as e:
            print(f"Error: {e}")

if DEBUG:
    for key in data:
        print(data[key].head()) if JUPYTER else print(data[key])

# Columns known to be different
q_c = {
    'chinese_traditional': 'mac_sdoh_questionnaire_traditional_chinese_complete',
    'chinese_simplified': 'mac_sdoh_questionnaire_chinese_complete',
    'english': 'mac_sdoh_questionnaire_english_complete',
    'spanish': 'mac_sdoh_questionnaire_spanish_complete'
}

for key in data:
    # Replace multiple underscores with a single underscore
    data[key].columns = data[key].columns.str.replace(r'__+', '_', regex=True)
    data[key].rename(columns={'msoc_bas_45': 'msoc_bas_46'}, inplace=True)
    data[key].rename(columns={q_c[key]: 'questionnaire_complete'}, inplace=True)
    # Combine Chinese surveys
    if key in ['chinese_traditional', 'chinese_simplified']:
        data[key]['survey'] = 'chinese'
    else:
        data[key]['survey'] = key

# Combine dataframes into a single dataframe
if all(set(df.columns) == set(data['english'].columns) for df in data.values()):
    print("All dataframes have the same columns")
    combined_df = pd.concat(data.values(), ignore_index=True)
else:
    print("Dataframes have different columns. Cannot proceed with combining.")
    exit(1)

# Load English metadata
english_metadata_file = f"{DATA}/raw/english_metadata.tsv"
if os.path.exists(english_metadata_file):
    english_metadata = pd.read_csv(english_metadata_file, sep='\t')
    print("Loaded English metadata")
else:
    print("English metadata file not found. Cannot proceed.")
    exit(1)

# Function to check if a column should be converted to numeric
def should_convert_to_numeric(col, metadata_df):
    field_info = metadata_df[metadata_df['field_name'] == col]
    if not field_info.empty:
        field_type = field_info['field_type'].iloc[0]
        return field_type == 'text'  # Only convert 'text' fields
    return False  # If not found in metadata, don't convert

# Attempt to convert text columns to numeric if possible in combined_df
numeric_converted_columns = []
for col in combined_df.columns:
    if combined_df[col].dtype == object and should_convert_to_numeric(col, english_metadata):
        non_missing = combined_df[col].dropna()
        try:
            converted = pd.to_numeric(non_missing, errors='raise')
            # If conversion is successful, update the column
            combined_df.loc[non_missing.index, col] = converted
            combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce')
            numeric_converted_columns.append(col)
            print(f"Converted column '{col}' to numeric.")
        except ValueError:
            pass  # Column cannot be converted to numeric

# Save combined data
combined_df.to_csv(f"{DATA}/combined.tsv", index=False, sep='\t')
print(f"Saved: combined.tsv")

# Load the column configuration
column_config_file = os.path.join(git_root, 'reference', 'column_config.json')
with open(column_config_file, 'r', encoding='utf-8') as f:
    column_config = json.load(f)

def create_data_dictionary(metadata_df, column_config, combined_df):
    try:
        data_dictionary = {}
        
        for _, row in metadata_df.iterrows():
            field_name = row['field_name']
            
            # Skip omitted columns
            if any(field_name.startswith(omit.replace('*', '')) for omit in column_config['omit']):
                continue
            
            # Determine field type based on metadata and data in combined_df
            field_type = row['field_type']
            if field_name in combined_df.columns:
                if field_type == 'text' and pd.api.types.is_numeric_dtype(combined_df[field_name]):
                    field_type = 'numeric'
            
            # Retrieve value labels from metadata
            select_choices = row['select_choices_or_calculations']
            value_labels = None
            if pd.notna(select_choices):
                value_labels = {}
                choices = select_choices.split('|')
                for choice in choices:
                    parts = choice.strip().split(',', 1)
                    if len(parts) == 2:
                        value, label = parts
                        value_labels[value.strip()] = strip_html(str(label.strip()))
            
            # Convert field_label to string before stripping HTML
            field_label = str(row['field_label']) if pd.notna(row['field_label']) else ''
            
            data_dictionary[field_name] = {
                'type': field_type,
                'label': strip_html(field_label),
                'value_labels': value_labels
            }
            
            # Handle non-standard exploding variables first
            if field_name in column_config['non_standard_exploding']:
                data_dictionary[field_name]['exploding'] = True
                data_dictionary[field_name]['exploded_fields'] = column_config['non_standard_exploding'][field_name]
            # Then check if it's a checkbox field (which gets "exploded")
            elif field_type == 'checkbox':
                data_dictionary[field_name]['is_checkbox'] = True
                if value_labels:
                    exploded_fields = [f"{field_name}_{value}" for value in value_labels.keys()]
                    data_dictionary[field_name]['exploded_fields'] = exploded_fields
    
        return data_dictionary
        
    except Exception as e:
        print(f"Error creating data dictionary: {e}")
        import traceback
        traceback.print_exc()
        return None  # Return None if there's an error

# Create data dictionary, passing English metadata and combined_df
data_dictionary = create_data_dictionary(english_metadata, column_config, combined_df)

# Optionally, print out how many fields are numeric
numeric_fields = [field for field, info in data_dictionary.items() if info['type'] == 'numeric']
print(f"Numeric fields detected: {len(numeric_fields)}")

# Save data dictionary
data_dict_file = os.path.join(git_root, 'reference', 'data_dictionary.json')
os.makedirs(os.path.dirname(data_dict_file), exist_ok=True)
print(f"Data dictionary contains {len(data_dictionary)} entries")

# Add a comment about checkbox fields
checkbox_fields = [field for field, info in data_dictionary.items() if info.get('is_checkbox')]
if checkbox_fields:
    print(f"Checkboxes exploded into multiple columns: {', '.join(checkbox_fields)}")

exploding_fields = [field for field, info in data_dictionary.items() if info.get('exploding')]
if exploding_fields:
    print(f"\nNon-checkbox exploding fields: {', '.join(exploding_fields)}")

with open(data_dict_file, 'w', encoding='utf-8') as f:
    json.dump(data_dictionary, f, indent=2, ensure_ascii=False)

# Verify that the file was created and has content
if os.path.exists(data_dict_file) and os.path.getsize(data_dict_file) > 0:
    # Trim git root from data_dict_file
    rel_path = os.path.relpath(data_dict_file, git_root)
    print(f"Data dictionary successfully saved to {rel_path}")
else:
    print(f"Error: Data dictionary file is empty or not created")