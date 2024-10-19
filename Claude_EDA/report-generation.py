# Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('report_template.html')

# Render the template with our data
html_content = template.render(summaries=all_summaries)

# Write the report to a file
with open('data_analysis_report.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Report generated as 'data_analysis_report.html'")
