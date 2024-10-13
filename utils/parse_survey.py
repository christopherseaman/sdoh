import re
from bs4 import BeautifulSoup

def extract_field_info(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    fields = []

    for table in soup.find_all('table', class_='frmedit_tbl'):
        variable_name = table.find('span', {'data-kind': 'variable-name'})
        label = table.find('div', {'data-mlm-type': 'label'})
        
        if variable_name and label:
            fields.append((variable_name.text.strip(), label.text.strip()))

    return fields

def parse_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    return extract_field_info(content)

# Usage
file_path = 'reference/survey_english.html'
fields = parse_html_file(file_path)

# Print results
print("Column\tQuestion")
for variable, question in fields:
    print(f"{variable}\t{question}")