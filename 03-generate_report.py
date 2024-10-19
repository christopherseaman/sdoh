import json
import os
from io import BytesIO
import base64
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
from scipy import stats
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
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return f'<img src="data:image/png;base64,{img_base64}" alt="Histogram of {column}"/>'

# Function to generate bar chart and return HTML image tag
def generate_bar_chart(labels, counts, title, cohort=None):
    if not counts:
        return "No data to plot."
    plt.figure(figsize=(10,6))
    
    # Use numeric indices for x-axis if labels are too long
    x = range(len(labels))
    plt.bar(x, counts, color='skyblue')
    
    plt.title(title + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Values')
    plt.ylabel('Counts')
    
    # Set x-ticks to numeric indices and use short labels
    plt.xticks(x, [str(i+1) for i in x], rotation=0)
    
    # Add a legend with full labels
    legend_labels = [f"{i+1}: {label}" for i, label in enumerate(labels)]
    plt.legend(legend_labels, title="Value Labels", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return f'<img src="data:image/png;base64,{img_base64}" alt="{title}"/>'

# Function to compute distribution summaries
def compute_distributions(data, columns_dict, cohort=None):
    distribution_summary = {}
    for parent_col, child_cols in columns_dict.items():
        if parent_col in data_dict and data_dict[parent_col]['type'] == 'checkbox':
            # Handle exploded checkbox fields
            counts = {label: data[child].sum() for child, label in zip(child_cols, data_dict[parent_col]['value_labels'].values())}
            title = f'Distribution of {parent_col}'
            graph = generate_bar_chart(list(counts.keys()), list(counts.values()), title, cohort)
            distribution_summary[parent_col] = {
                'counts': counts,
                'graph': graph
            }
        else:
            for child in child_cols:
                if child not in data.columns:
                    continue
                
                title = f'Distribution of {child}'
                
                if child in data_dict and data_dict[child]['type'] == 'text':
                    # Check if the 'text' column is numerical
                    try:
                        pd.to_numeric(data[child].dropna().iloc[0])
                        is_numeric = True
                    except:
                        is_numeric = False
                    if is_numeric:
                        graph = generate_histogram(data, child, cohort)
                        distribution_summary[child] = {
                            'counts': None,
                            'description': data[child].describe().to_dict(),
                            'graph': graph
                        }
                    else:
                        counts = data[child].value_counts(dropna=True).to_dict()
                        graph = generate_bar_chart(list(counts.keys()), list(counts.values()), title, cohort)
                        distribution_summary[child] = {
                            'counts': counts,
                            'graph': graph
                        }
                elif child in data_dict and data_dict[child]['type'] in ['radio', 'checkbox']:
                    counts = data[child].value_counts(dropna=True).to_dict()
                    labels = list(counts.keys())
                    count_values = list(counts.values())
                    graph = generate_bar_chart(labels, count_values, title, cohort)
                    distribution_summary[child] = {
                        'counts': counts,
                        'graph': graph
                    }
                else:
                    if data[child].dtype == 'object':
                        counts = data[child].value_counts(dropna=True).to_dict()
                        distribution_summary[child] = {'counts': counts}
                    else:
                        desc = data[child].describe().to_dict()
                        distribution_summary[child] = {'description': desc}
    return distribution_summary

# Function to perform pairwise comparisons
def pairwise_comparison(data, columns, cohort1, cohort2):
    results = {}
    for col in columns:
        if col not in data.columns:
            continue
        data1 = data[data[cohort_var] == cohort1][col]
        data2 = data[data[cohort_var] == cohort2][col]
        
        if data1.dtype == 'object' or data2.dtype == 'object':
            # For categorical data, perform chi-square test
            contingency_table = pd.crosstab(data[cohort_var].isin([cohort1]), data[col])
            chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
            results[col] = f"Chi-square test p-value: {p_value:.4f}"
        else:
            # For numerical data, perform t-test
            t_stat, p_value = stats.ttest_ind(data1.dropna(), data2.dropna())
            results[col] = f"T-test p-value: {p_value:.4f}"
    return results

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

    # Perform pairwise comparisons
    pairwise_comparisons = {
        'English vs Spanish': pairwise_comparison(data, [col for cols in related_columns.values() for col in cols], 'english', 'spanish'),
        'English vs Chinese': pairwise_comparison(data, [col for cols in related_columns.values() for col in cols], 'english', 'chinese'),
        'Spanish vs Chinese': pairwise_comparison(data, [col for cols in related_columns.values() for col in cols], 'spanish', 'chinese')
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
        'distributions_english': distributions_english,
        'distributions_spanish': distributions_spanish,
        'distributions_chinese': distributions_chinese,
        'pairwise_comparisons': pairwise_comparisons
    })

# Generate HTML report using Jinja2
env = Environment(loader=FileSystemLoader('.'))
report_template = env.get_template('templates/report.html')
cohort_table_template = env.get_template('templates/cohort_table.html')

html_content = report_template.render(summary=summary)

# Write HTML report to file
with open(report_path, 'w') as f:
    f.write(html_content)

print("Domain report with individual distribution summaries, cohort analysis, and pairwise comparisons has been successfully generated as 'domain_report.html'. You can open it in your web browser to review the improved report.")
