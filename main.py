import os
import logging
from typing import Optional, Tuple, List
import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from dotenv import load_dotenv
import pandas as pd
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s'
)
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

    def load_products(self) -> None:
        """Load products from Excel file."""
        try:
            df = pd.read_excel(self.excel_path)
            self.products = [
                Product(
                    amazon_url=row['amazon_url'],
                    affiliate_link=row['affiliate_link'],
                    posted=bool(row.get('posted', False))
                )
                for _, row in df.iterrows()
            ]
            logger.info(f"Loaded {len(self.products)} products from Excel")
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            self.products = []

    def update_product_status(self, index: int) -> None:
        """Mark product as posted in Excel."""
        try:
            df = pd.read_excel(self.excel_path)
            df.loc[index, 'posted'] = True
            df.to_excel(self.excel_path, index=False)
            logger.info(f"Updated status for product at index {index}")
        except Exception as e:
            logger.error(f"Error updating Excel file: {e}")

class AmazonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        }

    async def get_product_details(self, product: Product) -> Tuple[str, Optional[str]]:
        """Scrape product details from Amazon."""
        try:
            response = requests.get(product.amazon_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find(id='productTitle')
            image = soup.find('img', {'id': 'landingImage'})
            
            product_title = title.get_text(strip=True) if title else 'No Title Found'
            image_url = image['src'] if image else None
            
            if image_url and not image_url.startswith('http'):
                image_url = f"https://www.amazon.in{image_url}"
                
            return product_title, image_url
            
        except requests.RequestException as e:
            logger.error(f"Error fetching product details: {e}")
            return 'No Title Found', None

class TelegramPoster:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

    async def post_product(self, title: str, image_url: Optional[str], affiliate_link: str) -> bool:
        """Post product to Telegram channel."""
        if not all([self.token, self.chat_id]):
            logger.error("Missing required environment variables")
            return False

        if not image_url:
            logger.error("No image URL available")
            return False

        try:
            bot = Bot(token=self.token)
            caption = f"🛒 *{title}*\n🔗 [Buy Now]({affiliate_link})"
            
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode='Markdown'
            )
            logger.info(f"Posted product: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")
            return False

async def main():
    # Initialize classes
    product_manager = ProductManager('products.xlsx')
    scraper = AmazonScraper()
    poster = TelegramPoster()
    
    while True:
        for index, product in enumerate(product_manager.products):
            if not product.posted:
                # Get product details
                title, image_url = await scraper.get_product_details(product)
                
                # Post to Telegram
                success = await poster.post_product(title, image_url, product.affiliate_link)
                
                if success:
                    # Update Excel file
                    product_manager.update_product_status(index)
                    product.posted = True
                
                # Wait for 1 minute before next product
                await asyncio.sleep(60)
        
        # All products posted, wait for 5 minutes before checking for new products
        logger.info("Checking for new products in 5 minutes...")
        await asyncio.sleep(300)
        product_manager.load_products()  # Reload products from Excel

if __name__ == "__main__":
    asyncio.run(main())