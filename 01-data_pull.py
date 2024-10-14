#!/bin/env python3

from dotenv import load_dotenv
from utils.notebook_check import in_notebook
import os
from redcap import Project
import pandas as pd

# Constants
JUPYTER = in_notebook()
DEBUG = False
DATA = 'data'
os.makedirs(DATA, exist_ok=True)

# Load environment variables
load_dotenv('dot.env')
token = eval(os.getenv('API_TOKEN'))
api_url = os.getenv('API_URL')

# data['key'] = DataFrame
data = {}

# Check is csv's exist, if not then download from REDCap
for key in token:
    if os.path.exists(f"{DATA}/{key}.tsv"):
        data[key] = pd.read_csv(f"{DATA}/{key}.tsv", sep='\t')
        print(f"Loaded: {key}.tsv")
    else:
        try:
            api_key = token[key]
            project = Project(api_url, api_key)
            data[key] = pd.DataFrame(project.export_records())
            data[key].to_csv(f"{DATA}/{key}.tsv", index=False, sep='\t')
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

if check_columns(data):
    print("All dataframes have the same columns")
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
