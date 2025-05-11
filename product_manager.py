import pandas as pd
from typing import List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Product:
    amazon_url: str
    affiliate_link: str
    posted: bool = False

class ProductManager:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.products: List[Product] = []
        self.load_products()
        logger.info(f"Initialized ProductManager with {len(self.products)} products")

    def clean_url(self, url: str) -> str:
        """Clean and validate Amazon URL."""
        from urllib.parse import unquote
        if not isinstance(url, str):
            return ""
        url = unquote(str(url)).strip()
        if '/dp/' in url:
            product_id = url.split('/dp/')[1].split('/')[0].split('?')[0]
            return f"https://www.amazon.in/dp/{product_id}"
        return url

    def load_products(self) -> None:
        """Load products from Excel file."""
        try:
            df = pd.read_excel(self.excel_path)
            # Filter out rows with NaN values
            df = df.dropna(subset=['amazon_url', 'affiliate_link'])
            
            # Ensure 'posted' column exists and has valid boolean values
            if 'posted' not in df.columns:
                df['posted'] = False
            else:
                # Convert any non-boolean values to False
                df['posted'] = df['posted'].fillna(False).astype(bool)
            
            # Clean URLs before creating Product objects
            df['amazon_url'] = df['amazon_url'].apply(self.clean_url)
            df = df[df['amazon_url'] != ""]  # Remove rows with invalid URLs
            
            self.products = [
                Product(
                    amazon_url=str(row['amazon_url']),
                    affiliate_link=str(row['affiliate_link']),
                    posted=bool(row['posted'])
                )
                for _, row in df.iterrows()
            ]
            
            unposted_count = len([p for p in self.products if not p.posted])
            logger.info(f"Loaded {len(self.products)} products from Excel ({unposted_count} unposted)")
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            self.products = []

    def update_product_status(self, index: int) -> None:
        """Mark product as posted in Excel."""
        try:
            df = pd.read_excel(self.excel_path)
            if 'posted' not in df.columns:
                df['posted'] = False
            df.loc[index, 'posted'] = True
            df.to_excel(self.excel_path, index=False)
            logger.info(f"Updated status for product at index {index} as posted")
        except Exception as e:
            logger.error(f"Error updating Excel file: {e}")
            # Revert the posted status in memory if Excel update fails
            if 0 <= index < len(self.products):
                self.products[index].posted = False