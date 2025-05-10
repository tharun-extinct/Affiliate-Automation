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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            # Filter out rows with NaN values
            df = df.dropna(subset=['amazon_url', 'affiliate_link'])
            self.products = [
                Product(
                    amazon_url=str(row['amazon_url']),
                    affiliate_link=str(row['affiliate_link']),
                    posted=bool(row.get('posted', False))
                )
                for _, row in df.iterrows()
                if pd.notna(row['amazon_url']) and pd.notna(row['affiliate_link'])
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def get_product_details(self, product: Product) -> Tuple[str, Optional[str]]:
        """Scrape product details from Amazon."""
        try:
            session = await self._get_session()
            async with session.get(product.amazon_url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"Error fetching product: HTTP {response.status}")
                    await asyncio.sleep(5)  # Wait before retry
                    return 'No Title Found', None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Try multiple selectors for title
                title = (
                    soup.find(id='productTitle') or 
                    soup.find('h1', {'class': 'a-text-normal'}) or
                    soup.find('span', {'class': 'a-size-large product-title-word-break'})
                )
                
                # Try multiple selectors for image
                image = (
                    soup.find('img', {'id': 'landingImage'}) or
                    soup.find('img', {'id': 'imgBlkFront'}) or
                    soup.find('img', {'class': 'a-dynamic-image'})
                )
                
                product_title = title.get_text(strip=True) if title else 'No Title Found'
                image_url = image.get('src') if image else None
                
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://www.amazon.in{image_url}"
                    
                # Add a small delay between requests to avoid rate limiting
                await asyncio.sleep(2)
                return product_title, image_url
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching product: {product.amazon_url}")
            await asyncio.sleep(5)  # Wait before retry
            return 'No Title Found', None
        except Exception as e:
            logger.error(f"Error fetching product details: {type(e).__name__}: {str(e)}")
            await asyncio.sleep(5)  # Wait before retry
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
    
    try:
        while True:
            for index, product in enumerate(product_manager.products):
                if not product.posted:
                    # Try up to 3 times for each product
                    for attempt in range(3):
                        try:
                            # Get product details
                            title, image_url = await scraper.get_product_details(product)
                            
                            if title == 'No Title Found' or not image_url:
                                logger.warning(f"Attempt {attempt + 1}: Failed to get product details, retrying...")
                                await asyncio.sleep(10)  # Wait before retry
                                continue
                            
                            # Post to Telegram
                            success = await poster.post_product(title, image_url, product.affiliate_link)
                            
                            if success:
                                # Update Excel file
                                product_manager.update_product_status(index)
                                product.posted = True
                                # Break the retry loop on success
                                break
                            
                            logger.warning(f"Attempt {attempt + 1}: Failed to post product, retrying...")
                            await asyncio.sleep(10)  # Wait before retry
                            
                        except Exception as e:
                            logger.error(f"Error processing product: {type(e).__name__}: {str(e)}")
                            if attempt == 2:  # Last attempt
                                logger.error("Failed all retry attempts, moving to next product")
                            await asyncio.sleep(10)
                    
                    # Wait for 1 minute before next product
                    await asyncio.sleep(60)
            
            # All products posted, wait for 5 minutes before checking for new products
            logger.info("Checking for new products in 5 minutes...")
            await asyncio.sleep(300)
            product_manager.load_products()  # Reload products from Excel
            
    except Exception as e:
        logger.error(f"Main loop error: {type(e).__name__}: {str(e)}")
    finally:
        # Cleanup
        if scraper._session:
            await scraper._session.close()

if __name__ == "__main__":
    asyncio.run(main())