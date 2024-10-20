import json
import os
from io import BytesIO
import base64
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
from utils import load_data

# Set paths
report_path = 'domain_report.html'
domain_map_path = 'reference/domain_map.tsv'
cohort_var = 'survey'

# Load domain mappings and data
domain_map = pd.read_csv(domain_map_path, sep='\t')
data, data_dict = load_data()

# Function to get related columns
def get_related_columns(column_names):
    related = {}
    for col in column_names.split(', '):
        if col in data_dict and data_dict[col].get('exploded_fields'):
            related[col] = data_dict[col]['exploded_fields']
        else:
            related[col] = [col]
    return related

# Function to generate histogram and return HTML image tag
def generate_histogram(data, column, cohort=None):
    plt.figure(figsize=(8,6))
    plt.hist(pd.to_numeric(data[column], errors='coerce').dropna(), bins=20, color='skyblue', edgecolor='black')
    plt.title(f'Distribution of {column}' + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Values')
    plt.ylabel('Frequency')
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='svg')
    plt.close()
    buffer.seek(0)
    return buffer.getvalue().decode('utf-8')

# Function to generate bar chart and return HTML image tag
def generate_bar_chart(labels, counts, title, cohort=None, max_count=None):
    if not counts:
        return "No data to plot."
    plt.figure(figsize=(10,6))
    
    x = range(len(labels))
    bars = plt.bar(x, counts, color='skyblue')
    
    plt.title(title + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Values')
    plt.ylabel('Counts')
    
    # Set y-axis limit to max_count if provided
    if max_count:
        plt.ylim(0, max_count)
    
    # Label bars with their values
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                 f'{height}',
                 ha='center', va='bottom')
    
    plt.xticks(x, labels, rotation=45, ha='right')
    
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='svg')
    plt.close()
    buffer.seek(0)
    return buffer.getvalue().decode('utf-8')

# Function to compute distribution summaries
def compute_distributions(data, columns_dict, cohort=None):
    distribution_summary = {}
    max_count = 0  # Track the maximum count across all columns
    
    for parent_col, child_cols in columns_dict.items():
        if parent_col in data_dict and data_dict[parent_col]['type'] == 'checkbox':
            # Handle exploded checkbox fields
            counts = {label: data[child].sum() for child, label in zip(child_cols, data_dict[parent_col]['value_labels'].values())}
            if counts:
                max_count = max(max_count, max(counts.values()))
            title = f'Distribution of {parent_col}'
            graph = generate_bar_chart(list(counts.keys()), list(counts.values()), title, cohort)
            distribution_summary[parent_col] = {
                'counts': counts,
                'graph': graph
            }
        else:
            for child in child_cols:
                if child not in data.columns:
                    print(f"Warning: Column '{child}' not found in data")
                    continue
                
                # print(f"Processing child column: {child}")
                # print(f"Child column type: {data_dict.get(child, {}).get('type', 'Unknown')}")
                # print(f"Sample data: {data[child].head()}")
                
                title = f'Distribution of {child}'
                
                if data_dict[child]['type'] == 'numeric':
                    # Ensure we're working with numeric data
                    numeric_data = pd.to_numeric(data[child], errors='coerce')
                    if not numeric_data.isna().all():
                        graph = generate_histogram(numeric_data.dropna(), child, cohort)
                        desc = numeric_data.describe().to_dict()
                        distribution_summary[child] = {
                            'description': desc,
                            'graph': graph
                        }
                    else:
                        print(f"Warning: Column '{child}' is marked as numeric but contains no valid numeric data.")
                        distribution_summary[child] = {
                            'description': 'No valid numeric data',
                            'graph': None
                        }
                elif data_dict[child]['type'] in ['radio', 'checkbox', 'dropdown', 'text']:
                    counts = data[child].value_counts(dropna=False).to_dict()
                    non_nan_counts = {k: v for k, v in counts.items() if pd.notna(k)}
                    if non_nan_counts:
                        max_count = max(max_count, max(non_nan_counts.values()))
                        graph = generate_bar_chart(list(non_nan_counts.keys()), list(non_nan_counts.values()), title, cohort)
                    else:
                        print(f"Warning: Column '{child}' contains only NaN values")
                        graph = "No non-NaN data to plot."
                    distribution_summary[child] = {
                        'counts': counts,  # Keep nan in counts
                        'graph': graph     # Will be either the graph or the warning message
                    }
                else:
                    print(f"Warning: Unhandled column type '{data_dict[child]['type']}' for column '{child}'")
                    distribution_summary[child] = {
                        'description': f"Unhandled column type: {data_dict[child]['type']}",
                        'graph': None
                    }
    
    for key, value in distribution_summary.items():
        if 'counts' in value:
            non_nan_counts = {k: v for k, v in value['counts'].items() if pd.notna(k)}
            if non_nan_counts:
                value['graph'] = generate_bar_chart(list(non_nan_counts.keys()), list(non_nan_counts.values()), f'Distribution of {key}', cohort, max_count)
            else:
                value['graph'] = "No non-NaN data to plot."
    
    return distribution_summary

# Prepare summary data
summary = []

for _, row in domain_map.iterrows():
    domain = row['domain']
    item = row['item']
    columns = row['column_name']
    related_columns = get_related_columns(columns)

    # Compute distributions for all cohorts combined
    distributions_all = compute_distributions(data, related_columns)

    # Compute distributions for each cohort
    distributions_english = compute_distributions(data[data[cohort_var] == 'english'], related_columns, 'English')
    distributions_spanish = compute_distributions(data[data[cohort_var] == 'spanish'], related_columns, 'Spanish')
    distributions_chinese = compute_distributions(data[data[cohort_var] == 'chinese'], related_columns, 'Chinese')

    # Compile distributions by cohort
    distributions_by_cohort = {
        'English': distributions_english,
        'Spanish': distributions_spanish,
        'Chinese': distributions_chinese
    }

    # Retrieve column labels and types
    column_details = {}
    for parent_col, child_cols in related_columns.items():
        if parent_col in data_dict and data_dict[parent_col]['type'] == 'checkbox':
            column_details[parent_col] = {
                'label': data_dict[parent_col]['label'],
                'type': 'checkbox',
                'value_labels': data_dict[parent_col]['value_labels']
            }
        else:
            for child in child_cols:
                if child in data_dict:
                    column_details[child] = {
                        'label': data_dict[child]['label'],
                        'type': data_dict[child]['type'],
                        'value_labels': data_dict[child].get('value_labels')
                    }

    summary.append({
        'domain': domain,
        'item': item,
        'columns': column_details,
        'distributions_all': distributions_all,
        'distributions_by_cohort': distributions_by_cohort
    })

# Generate HTML report using Jinja2
env = Environment(loader=FileSystemLoader('.'))
report_template = env.get_template('templates/report.html')
cohort_table_template = env.get_template('templates/cohort_table.html')

html_content = report_template.render(summary=summary)

# Write HTML report to file
with open(report_path, 'w') as f:
    f.write(html_content)

print("Domain report with combined and by cohort summaries, including value labels and graphs, has been successfully generated as 'domain_report.html'. You can open it in your web browser to review the updated report.")
