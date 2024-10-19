def visualize_item(df, item, output_dir='visualizations'):
    columns = get_related_columns(item)
    for col in columns:
        if col in df.columns:
            plt.figure(figsize=(10, 6))
            if df[col].dtype.name == 'category' or df[col].dtype == bool:
                sns.countplot(y=col, data=df)
                plt.title(f'Distribution of {col}')
                plt.xlabel('Count')
            elif np.issubdtype(df[col].dtype, np.number):
                sns.histplot(df[col], kde=True)
                plt.title(f'Distribution of {col}')
                plt.xlabel('Value')
            else:
                # For text columns, we might want to show the most common values
                value_counts = df[col].value_counts().head(10)
                sns.barplot(x=value_counts.values, y=value_counts.index)
                plt.title(f'Top 10 values for {col}')
                plt.xlabel('Count')
            plt.tight_layout()
            plt.savefig(f'{output_dir}/{item}_{col}.png')
            plt.close()

# Generate visualizations for all items
os.makedirs('visualizations', exist_ok=True)
for domain in domain_map['domain'].unique():
    domain_items = domain_map[domain_map['domain'] == domain]['item'].unique()
    for item in domain_items:
        visualize_item(df, item)

print("Visualizations generated in the 'visualizations' directory.")
