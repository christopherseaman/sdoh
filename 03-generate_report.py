import json
import os
from utils import load_data
from io import BytesIO
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
            # For checkbox fields, use the parent column name
            related[col] = data_dict[col]['exploded_fields']
        else:
            related[col] = [col]
    return related

# Function to generate histogram and return HTML image
def generate_histogram(data_series, column, cohort=None):
    plt.figure(figsize=(10, 6))
    
    # Create histogram
    sns.histplot(data_series.dropna(), bins=20, kde=False, color='skyblue')
    
    plt.title(f'Distribution of {column}' + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Values')
    plt.ylabel('Frequency')
    
    # # Add summary statistics as text
    # stats = data_series.describe()
    # stats_text = f"Mean: {stats['mean']:.2f}\nMedian: {stats['50%']:.2f}\nStd: {stats['std']:.2f}"
    # plt.figtext(0.5, -0.1, stats_text, ha='center', va='center', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    return buffer.getvalue().decode('utf-8')

# Function to generate bar chart and return HTML image
def generate_bar_chart(labels, counts, title, cohort=None, max_count=None):
    if not counts:
        return "No data to plot."

    # Filter out 'nan' and non-numeric values
    valid_data = [(label, count) for label, count in zip(labels, counts) if pd.notna(label) and label != 'nan']
    
    if not valid_data:
        return "No valid data to plot."

    valid_labels, valid_counts = zip(*valid_data)

    num_values = len(valid_labels)
    # Adjust figure height based on the number of labels to accommodate them
    fig_height = max(6, num_values * 0.4)
    plt.figure(figsize=(10, fig_height))

    x = range(len(valid_labels))
    bars = plt.bar(x, valid_counts, color='skyblue')

    plt.title(f'{title}' + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Options')
    plt.ylabel('Counts')

    # Set y-axis limit to max_count if provided
    # Note: this used to set all y-axes to the same maximum
    plt.ylim(0, max(valid_counts) * 1.1)
    # if max_count is not None:
    #     plt.ylim(0, max_count * 1.1)  # Add 10% padding to the top
    # else:
    #     plt.ylim(0, max(valid_counts) * 1.1)

    # Label bars with their counts
    for bar, count in zip(bars, valid_counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height,
                 f'{int(count)}',
                 ha='center', va='bottom')

    plt.xticks(x, valid_labels, rotation=45, ha='right')

    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='svg', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    return buffer.getvalue().decode('utf-8')

# Function to compute distributions and maximum counts
def compute_distributions(data_subset, columns_dict, cohort=None):
    distribution_summary = {}
    max_counts = {}

    for parent_col, child_cols in columns_dict.items():
        field_info = data_dict.get(parent_col, {})
        col_type = field_info.get('type', 'unknown')

        if col_type == 'checkbox' and 'exploded_fields' in field_info:
            # Handle checkbox fields by aggregating counts of exploded fields
            counts = {}
            labels = []
            for exploded_col in child_cols:
                value_key = exploded_col.split('_')[-1]
                labels.append(value_key)
                if exploded_col in data_subset.columns:
                    counts[value_key] = data_subset[exploded_col].sum()
                else:
                    counts[value_key] = 0  # If the column doesn't exist, count is zero

            distribution_summary[parent_col] = {
                'counts': counts,
                'labels': labels,
                'graph': None  # Will generate graph later
            }
            if counts:
                max_counts[parent_col] = max(counts.values())
        else:
            for col in child_cols:
                if col not in data_subset.columns:
                    logging.warning(f"Column '{col}' not found in data")
                    continue

                col_info = data_dict.get(col, {})
                col_type = col_info.get('type', 'unknown')
                if col_type == 'numeric':
                    # Handle numeric data
                    numeric_data = pd.to_numeric(data_subset[col], errors='coerce')
                    if not numeric_data.isna().all():
                        desc = numeric_data.describe().to_dict()
                        graph = generate_histogram(numeric_data, col, cohort)
                        distribution_summary[col] = {
                            'description': desc,
                            'graph': graph
                        }
                    else:
                        logging.warning(f"Column '{col}' has no valid numeric data.")
                        distribution_summary[col] = {
                            'description': 'No valid numeric data',
                            'graph': None
                        }
                elif col_type in ['radio', 'dropdown', 'text']:
                    counts = data_subset[col].value_counts(dropna=False).to_dict()
                    labels = list(map(str, counts.keys()))
                    graph = generate_bar_chart(
                        labels,
                        list(counts.values()),
                        f'Distribution of {col}',
                        cohort,
                        max_count=None
                    )
                    distribution_summary[col] = {
                        'counts': counts,
                        'labels': labels,
                        'graph': graph
                    }
                    non_nan_counts = {k: v for k, v in counts.items() if pd.notna(k)}
                    if non_nan_counts:
                        max_counts[col] = max(non_nan_counts.values())
                else:
                    logging.warning(f"Unhandled column type '{col_type}' for column '{col}'")
                    distribution_summary[col] = {
                        'description': f"Unhandled column type: {col_type}",
                        'graph': None
                    }

    return distribution_summary, max_counts

# Prepare summary data
summary = []
domains = []

# Group entries by domain
domain_entries = {}

for _, row in domain_map.iterrows():
    domain = row['domain']
    item = row['item']
    columns = row['column_name']
    related_columns = get_related_columns(columns)

    # Compute distributions for all cohorts combined
    distributions_all, _ = compute_distributions(data, related_columns)

    # Compute distributions for each cohort and collect max counts
    distributions_by_cohort = {}
    global_max_counts = {}
    cohorts = data[cohort_var].unique()
    for cohort_name in cohorts:
        cohort_data = data[data[cohort_var] == cohort_name]
        distributions_cohort, max_counts_cohort = compute_distributions(cohort_data, related_columns, cohort_name)
        distributions_by_cohort[cohort_name.capitalize()] = distributions_cohort

        # Update global_max_counts with max counts from cohorts
        for key, value in max_counts_cohort.items():
            if key not in global_max_counts or value > global_max_counts[key]:
                global_max_counts[key] = value

    # Generate graphs for all cohorts combined
    for key, value in distributions_all.items():
        if 'counts' in value and value['counts']:
            counts = value['counts']
            labels = value['labels']
            nan_count = counts.pop('nan', 0)  # Remove 'nan' and get its count
            value['graph'] = generate_bar_chart(
                list(counts.keys()),
                list(counts.values()),
                f'Distribution of {key}',
                'All Cohorts'
            )
            # Add 'nan' count to the summary if it exists
            if nan_count > 0:
                value['nan_count'] = nan_count
        elif 'description' in value and value['description']:
            # Generate histogram for numeric data
            numeric_data = pd.to_numeric(data[key], errors='coerce')
            value['graph'] = generate_histogram(numeric_data, key, 'All Cohorts')

    # Generate graphs for each cohort using global_max_counts from cohorts only
    for cohort_name, distribution_set in distributions_by_cohort.items():
        for key, value in distribution_set.items():
            if 'counts' in value and value['counts']:
                counts = value['counts']
                nan_count = counts.pop('nan', 0)  # Remove 'nan' and get its count
                graph = generate_bar_chart(
                    list(counts.keys()),
                    list(counts.values()),
                    f'Distribution of {key}',
                    cohort_name,
                    max_count=global_max_counts.get(key)
                )
                distribution_set[key]['graph'] = graph
                # Add 'nan' count to the summary if it exists
                if nan_count > 0:
                    distribution_set[key]['nan_count'] = nan_count
            elif 'description' in value and value['description']:
                # Generate histogram for numeric data
                numeric_data = pd.to_numeric(data[data[cohort_var] == cohort_name.lower()][key], errors='coerce')
                graph = generate_histogram(numeric_data, key, cohort_name)
                distribution_set[key]['graph'] = graph

    # Retrieve column labels and types
    column_details = {}
    for parent_col, child_cols in related_columns.items():
        field_info = data_dict.get(parent_col, {})
        column_details[parent_col] = {
            'label': field_info.get('label', ''),
            'type': field_info.get('type', ''),
            'value_labels': field_info.get('value_labels', {})
        }

    entry = {
        'domain': domain,
        'item': item,
        'columns': column_details,
        'distributions_all': distributions_all,
        'distributions_by_cohort': distributions_by_cohort
    }

    if domain not in domain_entries:
        domain_entries[domain] = []
    domain_entries[domain].append(entry)

# Create domains list for the template
for domain, entries in domain_entries.items():
    domains.append({
        'id': domain.lower().replace(' ', '_'),
        'description': domain,
        'entries': entries
    })

# Generate HTML report using Jinja2
env = Environment(loader=FileSystemLoader('.'))
report_template = env.get_template('templates/report.html')

html_content = report_template.render(domains=domains)

# Write HTML report to file
with open(report_path, 'w') as f:
    f.write(html_content)

logging.info(f"Domain report has been successfully generated as '{report_path}'. You can open it in your web browser to review the updated report.")
