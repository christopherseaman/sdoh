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

# Check if csv's exist, if not then download from REDCap
for key in token:
    if os.path.exists(f"{DATA}/raw/{key}.tsv"):
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
                    # trim html from field label
                    value_labels[field_name] = {}
                    choices = field['select_choices_or_calculations'].split('|')
                    for choice in choices:
                        value, label = choice.strip().split(',', 1)
                        value_labels[field_name][value.strip()] = label.strip()
                else:
                    # Convert numeric columns and log the changes
                    for col in data[key].columns:
                        if data[key][col].dtype == object:
                            try:
                                numeric_col = pd.to_numeric(data[key][col], errors='coerce')
                                if not np.isnan(numeric_col).all():
                                    data[key][col] = numeric_col
                                    print(f"Converted column '{col}' in '{key}' to numeric.")
                            except:
                                pass  # Column is not numeric
            
            # Save metadata with stripped HTML and value labels
            metadata_df = pd.DataFrame(metadata)
            metadata_df['value_labels'] = metadata_df['field_name'].map(value_labels)
            metadata_df.to_csv(f"{DATA}/raw/{key}_metadata.tsv", index=False, sep='\t')
            print(f"Saved : {key}_metadata.tsv")
            
            # Save data
            data[key].to_csv(f"{DATA}/raw/{key}.tsv", index=False, sep='\t')
            print(f"Saved : {key}.tsv")
        except Exception as e:
            print(f"Error : {e}")

if DEBUG:
    for key in data:
        print(data[key].head()) if JUPYTER else print(data[key])

# Columns known to be different (2024.10.12):
# chinese_traditional: {'mac_sdoh_questionnaire_traditional_chinese_complete', 'msoc_bas_46'}
# chinese_simplified: {'mac_sdoh_questionnaire_chinese_complete', 'msoc_bas_46'}
# english: {'mac_sdoh_questionnaire_english_complete', 'msoc_bas_46'}
# spanish: {'msoc_bas_45', 'mac_sdoh_questionnaire_spanish_complete'}

# Change known misnamed column, add 'survey' to identify language, combine questionnaire complete columns
q_c = {}
q_c['chinese_traditional'] = 'mac_sdoh_questionnaire_traditional_chinese_complete'
q_c['chinese_simplified'] = 'mac_sdoh_questionnaire_chinese_complete'
q_c['english'] = 'mac_sdoh_questionnaire_english_complete'
q_c['spanish'] = 'mac_sdoh_questionnaire_spanish_complete'

for key in data:
    # Replace multiple underscores with single underscore
    data[key].columns = data[key].columns.str.replace(r'__+', '_', regex=True)
    data[key].rename(columns={'msoc_bas_45': 'msoc_bas_46'}, inplace=True)
    data[key].rename(columns={q_c[key]: 'questionnaire_complete'}, inplace=True)
    # Combine Chinese surveys
    if key in ['chinese_traditional', 'chinese_simplified']:
        data[key]['survey'] = 'chinese'
    else:
        data[key]['survey'] = key



# Check if dataframes have the same columns
def check_columns(data):
    columns = None
    for key in data:
        if columns is None:
            columns = set(data[key].columns)
        else:
            if columns != set(data[key].columns):
                return False
    return True

# Load the column configuration
column_config_file = os.path.join(git_root, 'reference', 'column_config.json')
with open(column_config_file, 'r', encoding='utf-8') as f:
    column_config = json.load(f)

def create_data_dictionary(metadata_file, column_config):
    try:
        data_dictionary = {}
        
        if os.path.exists(metadata_file):
            metadata = pd.read_csv(metadata_file, sep='\t')
            for _, row in metadata.iterrows():
                field_name = row['field_name']
                
                # Skip omitted columns
                if any(field_name.startswith(omit.replace('*', '')) for omit in column_config['omit']):
                    continue
                
                select_choices = row['select_choices_or_calculations']
                
                value_labels = None
                if pd.notna(select_choices):
                    value_labels = {}
                    choices = select_choices.split('|')
                    for choice in choices:
                        parts = choice.strip().split(',', 1)
                        if len(parts) == 2:
                            value, label = parts
                            value_labels[value.strip()] = strip_html(label.strip())
                
                # Update type to 'numeric' if column was converted to numeric
                field_type = row['field_type']
                for df in data.values():
                    if field_name in df.columns and pd.api.types.is_numeric_dtype(df[field_name]):
                        field_type = 'numeric'
                        break
                
                data_dictionary[field_name] = {
                    'type': field_type,
                    'label': strip_html(row['field_label']),
                    'value_labels': value_labels
                }
                
                # Handle non-standard exploding variables first
                if field_name in column_config['non_standard_exploding']:
                    data_dictionary[field_name]['exploding'] = True
                    data_dictionary[field_name]['exploded_fields'] = column_config['non_standard_exploding'][field_name]
                # Then check if it's a checkbox field (which gets "exploded")
                elif row['field_type'] == 'checkbox':
                    data_dictionary[field_name]['is_checkbox'] = True
                    if value_labels:
                        exploded_fields = [f"{field_name}_{value}" for value in value_labels.keys()]
                        data_dictionary[field_name]['exploded_fields'] = exploded_fields
        
        return data_dictionary
        
    except Exception as e:
        print(f"Error creating data dictionary: {e}")
        import traceback
        traceback.print_exc()

if check_columns(data):
    print("All dataframes have the same columns")
    # Combine into single dataframe and save
    combined_df = pd.concat(data.values(), ignore_index=True)
    
    try:
        # Save combined data
        combined_df.to_csv(f"{DATA}/combined.tsv", index=False, sep='\t')
        print(f"Saved : combined.tsv")
        
        # Create data dictionary
        data_dictionary = create_data_dictionary(f"{DATA}/raw/english_metadata.tsv", column_config)

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
            # trim git root from data_dict_file
            rel_path = os.path.relpath(data_dict_file, git_root)
            print(f"Data dictionary successfully saved to {rel_path}")
        else:
            print(f"Error: Data dictionary file is empty or not created")
    
    except Exception as e:
        print(f"Error saving data dictionary: {e}")
        import traceback
        traceback.print_exc()

else:
    # Find the columns that are different
    columns = None
    for key in data:
        if columns is None:
            columns = set(data[key].columns)
        else:
            columns = columns.intersection(set(data[key].columns))
    print("Columns that are different:")
    for key in data:
        print(f"{key}: {set(data[key].columns) - columns}")
