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
            related[col] = [(field, col) for field in data_dict[col]['exploded_fields']]
        else:
            related[col] = [(col, None)]
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
        for child, parent in child_cols:
            if child not in sampled_data.columns:
                continue
            
            title = f'Distribution of {child}'
            
            if parent and data_dict[parent]['type'] == 'checkbox':
                # Handle exploded checkbox fields
                counts = sampled_data[child].value_counts(dropna=True).to_dict()
                labels = ['Unchecked', 'Checked']
                count_values = [counts.get(0, 0), counts.get(1, 0)]
                graph = generate_bar_chart(labels, count_values, title, cohort)
                distribution_summary[child] = {
                    'counts': dict(zip(labels, count_values)),
                    'graph': graph
                }
            elif child in data_dict and data_dict[child]['type'] == 'text':
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

    # Retrieve column labels and types
    column_details = {}
    for parent_col, child_cols in related_columns.items():
        for child, parent in child_cols:
            if child in data_dict:
                column_details[child] = {
                    'label': data_dict[child]['label'],
                    'type': data_dict[child]['type'],
                    'value_labels': data_dict[child].get('value_labels')
                }
            elif parent in data_dict:
                parent_value_labels = data_dict[parent].get('value_labels', {})
                child_number = child.split('_')[-1]
                column_details[child] = {
                    'label': f"{data_dict[parent]['label']} - {parent_value_labels.get(child_number, 'Option ' + child_number)}",
                    'type': 'binary',
                    'value_labels': {'0': 'Unchecked', '1': 'Checked'}
                }

    summary.append({
        'domain': domain,
        'item': item,
        'columns': column_details,
        'distributions_all': distributions_all,
        'distributions_english': distributions_english,
        'distributions_spanish': distributions_spanish,
        'distributions_chinese': distributions_chinese
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
        .cohort-tabs { display: flex; margin-bottom: 10px; }
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
    {% for entry in summary %}
    <div class="domain">
        <h2>Domain: {{ entry.domain }}</h2>
        <div class="item">
            <h3>Item: {{ entry.item }}</h3>
            <div class="cohort-tabs">
                <div class="cohort-tab active" onclick="showCohort('all-cohorts-{{ loop.index }}', this)">All Cohorts</div>
                <div class="cohort-tab" onclick="showCohort('english-cohort-{{ loop.index }}', this)">English Cohort</div>
                <div class="cohort-tab" onclick="showCohort('spanish-cohort-{{ loop.index }}', this)">Spanish Cohort</div>
                <div class="cohort-tab" onclick="showCohort('chinese-cohort-{{ loop.index }}', this)">Chinese Cohort</div>
            </div>
            <div id="all-cohorts-{{ loop.index }}" class="cohort-content active">
                <h4>All Cohorts Combined</h4>
                {% with distributions=entry.distributions_all %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="english-cohort-{{ loop.index }}" class="cohort-content">
                <h4>English Cohort</h4>
                {% with distributions=entry.distributions_english %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="spanish-cohort-{{ loop.index }}" class="cohort-content">
                <h4>Spanish Cohort</h4>
                {% with distributions=entry.distributions_spanish %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
            </div>
            <div id="chinese-cohort-{{ loop.index }}" class="cohort-content">
                <h4>Chinese Cohort</h4>
                {% with distributions=entry.distributions_chinese %}
                    {% include 'cohort_table.html' %}
                {% endwith %}
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

print("Updated domain report with individual distribution summaries and cohort analysis has been successfully generated as 'domain_report.html'. You can open it in your web browser to review the improved report.")
