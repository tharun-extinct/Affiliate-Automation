import pandas as pd

# Sample data
data = {
    'amazon_url': [
        'https://www.amazon.in/product1',
        'https://www.amazon.in/product2',
        'https://www.amazon.in/product3'
    ],
    'affiliate_link': [
        'https://amzn.to/link1',
        'https://amzn.to/link2',
        'https://amzn.to/link3'
    ],
    'posted': [False, False, False]
}

# Create DataFrame
df = pd.DataFrame(data)

# Save to Excel
df.to_excel('products.xlsx', index=False)
print("Excel file created successfully!")