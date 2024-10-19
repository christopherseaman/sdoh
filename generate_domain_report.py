import pandas as pd
import json
import os
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt
from io import BytesIO
import base64

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
            related[col] = []
    return related

# Function to generate bar chart and return HTML image tag
def generate_bar_chart(labels, counts, title):
    if not counts:
        return "No data to plot."
    plt.figure(figsize=(8,5))
    plt.bar(labels, counts, color='skyblue')
    plt.title(title)
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
def compute_distributions(sampled_data, columns_dict):
    distribution_summary = {}
    for parent_col, child_cols in columns_dict.items():
        if child_cols:  # If there are exploded fields
            for child in child_cols:
                if child not in sampled_data.columns:
                    continue
                title = f'Distribution of {child}'
                if sampled_data[child].dtype == 'object':
                    counts = sampled_data[child].value_counts(dropna=True).to_dict()
                    labels = list(counts.keys())
                    count_values = list(counts.values())
                    graph = generate_bar_chart(labels, count_values, title)
                    distribution_summary[child] = {
                        'counts': counts,
                        'graph': graph,
                        'type': data_dict[child]['type']
                    }
                else:
                    desc = sampled_data[child].describe().to_dict()
                    distribution_summary[child] = {'description': desc}
        else:  # No exploded fields
            col = parent_col
            if col not in sampled_data.columns:
                continue
            if col in data_dict and data_dict[col]['type'] in ['radio', 'checkbox']:
                counts = sampled_data[col].value_counts(dropna=True).to_dict()
                labels = list(counts.keys())
                count_values = list(counts.values())
                graph = generate_bar_chart(labels, count_values, f'Distribution of {col}')
                distribution_summary[col] = {
                    'counts': counts,
                    'graph': graph,
                    'type': data_dict[col]['type']
                }
            else:
                if sampled_data[col].dtype == 'object':
                    counts = sampled_data[col].value_counts(dropna=True).to_dict()
                    distribution_summary[col] = {'counts': counts}
                else:
                    desc = sampled_data[col].describe().to_dict()
                    distribution_summary[col] = {'description': desc}
    return distribution_summary

# Read a sample of the data to compute distributions
data_sample_path = 'data/combined.tsv'
# Adjust 'nrows' as needed to get a representative sample without loading entire file
sample_size = 1000
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

    # Compute distributions for related columns
    distributions = compute_distributions(sampled_data, related_columns)

    # Retrieve column labels and types
    column_details = {}
    for parent_col, child_cols in related_columns.items():
        if parent_col in data_dict:
            column_details[parent_col] = {
                'label': data_dict[parent_col]['label'],
                'type': data_dict[parent_col]['type'],
                'value_labels': data_dict[parent_col].get('value_labels')
            }
        if child_cols:
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
        'distributions': distributions
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
    </style>
</head>
<body>
    <h1>Domain Report</h1>
    {% for entry in summary %}
    <div class="domain">
        <h2>Domain: {{ entry.domain }}</h2>
        <div class="item">
            <h3>Item: {{ entry.item }}</h3>
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
                        {% if entry.distributions[col] %}
                            {% if entry.distributions[col].graph %}
                                {{ entry.distributions[col].graph | safe }}
                            {% endif %}
                            {% if entry.distributions[col].counts %}
                                <ul>
                                {% for key, value in entry.distributions[col].counts.items() %}
                                    <li>{{ key }}: {{ value }}</li>
                                {% endfor %}
                                </ul>
                            {% endif %}
                            {% if entry.distributions[col].description %}
                                <ul>
                                    <li>Count: {{ entry.distributions[col].description.get('count', 'N/A') }}</li>
                                    <li>Mean: {{ entry.distributions[col].description.get('mean', 'N/A') }}</li>
                                    <li>Std: {{ entry.distributions[col].description.get('std', 'N/A') }}</li>
                                    <li>Min: {{ entry.distributions[col].description.get('min', 'N/A') }}</li>
                                    <li>25%: {{ entry.distributions[col].description.get('25%', 'N/A') }}</li>
                                    <li>50%: {{ entry.distributions[col].description.get('50%', 'N/A') }}</li>
                                    <li>75%: {{ entry.distributions[col].description.get('75%', 'N/A') }}</li>
                                    <li>Max: {{ entry.distributions[col].description.get('max', 'N/A') }}</li>
                                </ul>
                            {% endif %}
                        {% else %}
                            N/A
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
    {% endfor %}
</body>
</html>
""")

html_content = template.render(summary=summary)

# Write HTML report to file
with open('domain_report.html', 'w') as f:
    f.write(html_content)

print("Domain report with individual distribution summaries has been successfully generated as 'domain_report.html'. You can open it in your web browser to review the report.")
