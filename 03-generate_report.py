import pandas as pd
import json
import os
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import numpy as np
from scipy import stats

# Load domain mappings
domain_map_path = 'reference/domain_map.tsv'
domain_map = pd.read_csv(domain_map_path, sep='\t')

# Load data dictionary
data_dictionary_path = 'reference/data_dictionary.json'
with open(data_dictionary_path, 'r') as f:
    data_dict = json.load(f)

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
    plt.bar(labels, counts, color='skyblue')
    plt.title(title + (f' ({cohort})' if cohort else ''))
    plt.xlabel('Values')
    plt.ylabel('Counts')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return f'<img src="data:image/png;base64,{img_base64}" alt="{title}"/>'

# Function to compute distribution summaries
def compute_distributions(sampled_data, columns_dict, cohort=None):
    distribution_summary = {}
    for parent_col, child_cols in columns_dict.items():
        if parent_col in data_dict and data_dict[parent_col]['type'] == 'checkbox':
            # Handle exploded checkbox fields
            counts = {label: sampled_data[child].sum() for child, label in zip(child_cols, data_dict[parent_col]['value_labels'].values())}
            title = f'Distribution of {parent_col}'
            graph = generate_bar_chart(list(counts.keys()), list(counts.values()), title, cohort)
            distribution_summary[parent_col] = {
                'counts': counts,
                'graph': graph
            }
        else:
            for child in child_cols:
                if child not in sampled_data.columns:
                    continue
                
                title = f'Distribution of {child}'
                
                if child in data_dict and data_dict[child]['type'] == 'text':
                    # Check if the 'text' column is numerical
                    try:
                        pd.to_numeric(sampled_data[child].dropna().iloc[0])
                        is_numeric = True
                    except:
                        is_numeric = False
                    if is_numeric:
                        graph = generate_histogram(sampled_data, child, cohort)
                        distribution_summary[child] = {
                            'counts': None,
                            'description': sampled_data[child].describe().to_dict(),
                            'graph': graph
                        }
                    else:
                        counts = sampled_data[child].value_counts(dropna=True).to_dict()
                        graph = generate_bar_chart(list(counts.keys()), list(counts.values()), title, cohort)
                        distribution_summary[child] = {
                            'counts': counts,
                            'graph': graph
                        }
                elif child in data_dict and data_dict[child]['type'] in ['radio', 'checkbox']:
                    counts = sampled_data[child].value_counts(dropna=True).to_dict()
                    labels = list(counts.keys())
                    count_values = list(counts.values())
                    graph = generate_bar_chart(labels, count_values, title, cohort)
                    distribution_summary[child] = {
                        'counts': counts,
                        'graph': graph
                    }
                else:
                    if sampled_data[child].dtype == 'object':
                        counts = sampled_data[child].value_counts(dropna=True).to_dict()
                        distribution_summary[child] = {'counts': counts}
                    else:
                        desc = sampled_data[child].describe().to_dict()
                        distribution_summary[child] = {'description': desc}
    return distribution_summary

# Function to perform pairwise comparisons
def pairwise_comparison(data, columns, cohort1, cohort2):
    results = {}
    for col in columns:
        if col not in data.columns:
            continue
        data1 = data[data['survey'] == cohort1][col]
        data2 = data[data['survey'] == cohort2][col]
        
        if data1.dtype == 'object' or data2.dtype == 'object':
            # For categorical data, perform chi-square test
            contingency_table = pd.crosstab(data['survey'].isin([cohort1]), data[col])
            chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
            results[col] = f"Chi-square test p-value: {p_value:.4f}"
        else:
            # For numerical data, perform t-test
            t_stat, p_value = stats.ttest_ind(data1.dropna(), data2.dropna())
            results[col] = f"T-test p-value: {p_value:.4f}"
    return results

# Read a sample of the data to compute distributions
data_sample_path = 'data/combined.tsv'
# Adjust 'nrows' as needed to get a representative sample without loading entire file
sample_size = 10000
try:
    sampled_data = pd.read_csv(data_sample_path, sep='\t', nrows=sample_size)
except FileNotFoundError:
    print(f"Data file {data_sample_path} not found.")
    sampled_data = pd.DataFrame()

# Prepare summary data
summary = []

for _, row in domain_map.iterrows():
    domain = row['domain']
    item = row['item']
    columns = row['column_name']
    related_columns = get_related_columns(columns)

    # Compute distributions for all cohorts combined
    distributions_all = compute_distributions(sampled_data, related_columns)

    # Compute distributions for each cohort
    distributions_english = compute_distributions(sampled_data[sampled_data['survey'] == 'english'], related_columns, 'English')
    distributions_spanish = compute_distributions(sampled_data[sampled_data['survey'] == 'spanish'], related_columns, 'Spanish')
    distributions_chinese = compute_distributions(sampled_data[sampled_data['survey'] == 'chinese'], related_columns, 'Chinese')

    # Perform pairwise comparisons
    pairwise_comparisons = {
        'English vs Spanish': pairwise_comparison(sampled_data, [col for cols in related_columns.values() for col in cols], 'english', 'spanish'),
        'English vs Chinese': pairwise_comparison(sampled_data, [col for cols in related_columns.values() for col in cols], 'english', 'chinese'),
        'Spanish vs Chinese': pairwise_comparison(sampled_data, [col for cols in related_columns.values() for col in cols], 'spanish', 'chinese')
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
template = env.from_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Domain Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .domain { margin-bottom: 40px; }
        .item { margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; vertical-align: top; }
        th { background-color: #f2f2f2; }
        .distribution { margin-top: 10px; }
        .cohort-tabs { position: sticky; top: 0; background-color: white; z-index: 1000; display: flex; margin-bottom: 10px; }
        .cohort-tab { padding: 10px; cursor: pointer; border: 1px solid #ccc; background-color: #f1f1f1; }
        .cohort-tab.active { background-color: #ccc; }
        .cohort-content { display: none; }
        .cohort-content.active { display: block; }
    </style>
    <script>
        function showCohort(cohortName, element) {
            // Hide all cohort contents
            var contents = document.getElementsByClassName('cohort-content');
            for (var i = 0; i < contents.length; i++) {
                contents[i].classList.remove('active');
            }
            
            // Deactivate all tabs
            var tabs = document.getElementsByClassName('cohort-tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            // Show selected cohort content and activate tab
            document.getElementById(cohortName).classList.add('active');
            element.classList.add('active');
        }
    </script>
</head>
<body>
    <h1>Domain Report</h1>
    <div class="cohort-tabs">
        <div class="cohort-tab active" onclick="showCohort('all-cohorts', this)">All Cohorts</div>
        <div class="cohort-tab" onclick="showCohort('english-cohort', this)">English Cohort</div>
        <div class="cohort-tab" onclick="showCohort('spanish-cohort', this)">Spanish Cohort</div>
        <div class="cohort-tab" onclick="showCohort('chinese-cohort', this)">Chinese Cohort</div>
        <div class="cohort-tab" onclick="showCohort('pairwise-comparison', this)">Pairwise Comparison</div>
    </div>
    {% for entry in summary %}
    <div class="domain">
        <h2>{{ entry.domain }}</h2>
        <div class="item">
            <h3>{{ entry.item }}</h3>
            <div id="all-cohorts" class="cohort-content active">
                <h4>All Cohorts Combined</h4>
                {% with distributions=entry.distributions_all %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="english-cohort" class="cohort-content">
                <h4>English Cohort</h4>
                {% with distributions=entry.distributions_english %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="spanish-cohort" class="cohort-content">
                <h4>Spanish Cohort</h4>
                {% with distributions=entry.distributions_spanish %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="chinese-cohort" class="cohort-content">
                <h4>Chinese Cohort</h4>
                {% with distributions=entry.distributions_chinese %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="pairwise-comparison" class="cohort-content">
                <h4>Pairwise Comparisons</h4>
                <table>
                    <tr>
                        <th>Column</th>
                        <th>English vs Spanish</th>
                        <th>English vs Chinese</th>
                        <th>Spanish vs Chinese</th>
                    </tr>
                    {% for col in entry.columns %}
                    <tr>
                        <td>{{ col }}</td>
                        <td>{{ entry.pairwise_comparisons['English vs Spanish'].get(col, 'N/A') }}</td>
                        <td>{{ entry.pairwise_comparisons['English vs Chinese'].get(col, 'N/A') }}</td>
                        <td>{{ entry.pairwise_comparisons['Spanish vs Chinese'].get(col, 'N/A') }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </div>
    {% endfor %}
</body>
</html>
""")

cohort_table_template = """
<table>
    <tr>
        <th>Column Name</th>
        <th>Label</th>
        <th>Type</th>
        <th>Value Labels</th>
        <th>Distribution Summary</th>
    </tr>
    {% for col, details in entry.columns.items() %}
    <tr>
        <td>{{ col }}</td>
        <td>{{ details.label }}</td>
        <td>{{ details.type }}</td>
        <td>
            {% if details.value_labels %}
                <ul>
                {% for key, value in details.value_labels.items() %}
                    <li>{{ key }}: {{ value }}</li>
                {% endfor %}
                </ul>
            {% else %}
                {% if details.type == 'checkbox' %}
                    Multiple selections possible
                {% else %}
                    N/A
                {% endif %}
            {% endif %}
        </td>
        <td>
            {% if distributions and col in distributions %}
                {% if distributions[col].graph %}
                    {{ distributions[col].graph | safe }}
                {% endif %}
                {% if distributions[col].counts %}
                    <ul>
                    {% for key, value in distributions[col].counts.items() %}
                        <li>{{ key }}: {{ value }}</li>
                    {% endfor %}
                    </ul>
                {% endif %}
                {% if distributions[col].description %}
                    <ul>
                        <li>Count: {{ distributions[col].description.get('count', 'N/A') }}</li>
                        <li>Mean: {{ '{:.2f}'.format(distributions[col].description.get('mean', 'N/A')) }}</li>
                        <li>Std: {{ '{:.2f}'.format(distributions[col].description.get('std', 'N/A')) }}</li>
                        <li>Min: {{ '{:.2f}'.format(distributions[col].description.get('min', 'N/A')) }}</li>
                        <li>25%: {{ '{:.2f}'.format(distributions[col].description.get('25%', 'N/A')) }}</li>
                        <li>50%: {{ '{:.2f}'.format(distributions[col].description.get('50%', 'N/A')) }}</li>
                        <li>75%: {{ '{:.2f}'.format(distributions[col].description.get('75%', 'N/A')) }}</li>
                        <li>Max: {{ '{:.2f}'.format(distributions[col].description.get('max', 'N/A')) }}</li>
                    </ul>
                {% endif %}
            {% else %}
                N/A
            {% endif %}
        </td>
    </tr>
    {% endfor %}
</table>
"""

# Write cohort_table template to file
with open('cohort_table.html', 'w') as f:
    f.write(cohort_table_template)

html_content = template.render(summary=summary)

# Write HTML report to file
with open('domain_report.html', 'w') as f:
    f.write(html_content)

print("Updated domain report with individual distribution summaries, cohort analysis, and pairwise comparisons has been successfully generated as 'domain_report.html'. You can open it in your web browser to review the improved report.")
