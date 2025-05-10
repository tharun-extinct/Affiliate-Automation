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
        logger.info(f"Initialized ProductManager with {len(self.products)} products")    

    def clean_url(self, url: str) -> str:
        """Clean and validate Amazon URL."""
        from urllib.parse import unquote, quote
        if not isinstance(url, str):
            return ""
        
        url = unquote(str(url)).strip()
        
        # Handle /dp/ format
        if '/dp/' in url:
            product_id = url.split('/dp/')[1].split('/')[0].split('?')[0]
            return f"https://www.amazon.in/dp/{product_id}"
        
        # Handle URLs with spaces and full titles
        if 'amazon.in' in url:
            # Split by amazon.in/ and encode the rest
            base_url = url.split('amazon.in/')
            if len(base_url) > 1:
                path = base_url[1].split('?')[0].split(':')[0].strip()
                return f"https://www.amazon.in/{quote(path)}"
        
        return ""

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


class AmazonScraper:    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self._session

    async def get_product_details(self, product: Product) -> Tuple[str, Optional[str]]:
        """Scrape product details from Amazon."""
        try:
            # Clean and decode the URL
            from urllib.parse import unquote, urlparse, quote
            clean_url = unquote(product.amazon_url).strip()
            
            # Parse the URL
            parsed_url = urlparse(clean_url)
            if not parsed_url.scheme:
                clean_url = f"https://www.amazon.in/{clean_url.lstrip('/')}"
            
            # Extract product ID if present
            if '/dp/' in clean_url:
                product_id = clean_url.split('/dp/')[1].split('/')[0]
                clean_url = f"https://www.amazon.in/dp/{product_id}"
            else:
                # Handle full product name URLs
                parts = clean_url.split('amazon.in/')
                if len(parts) > 1:
                    path = parts[1].split('?')[0].split(':')[0].strip()
                    clean_url = f"https://www.amazon.in/{quote(path)}"
            
            logger.info(f"Fetching product from: {clean_url}")
            session = await self._get_session()
            
            async with session.get(clean_url) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status} for {clean_url}")
                    return None, None
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Try multiple selectors for title
                title_selectors = [
                    '#productTitle',
                    '.product-title-word-break',
                    '.a-size-large.product-title-word-break',
                    'h1.a-spacing-none',
                    'span#productTitle',
                    'h1 span.a-text-normal'
                ]
                
                title = None
                for selector in title_selectors:
                    element = soup.select_one(selector)
                    if element:
                        title = element.get_text(strip=True)
                        break
                
                # Try multiple selectors for image
                image_selectors = [
                    '#landingImage',
                    '#imgBlkFront',
                    '#main-image',
                    'img[data-old-hires]',
                    'img[data-a-dynamic-image]',
                    '.a-dynamic-image',
                    '#product-image'
                ]
                
                image_url = None
                for selector in image_selectors:
                    img = soup.select_one(selector)
                    if img:
                        image_url = (
                            img.get('data-old-hires') or 
                            img.get('src') or 
                            img.get('data-a-dynamic-image')
                        )
                        if image_url:
                            break
                
                if not title or not image_url:
                    logger.error(f"Failed to extract details from {clean_url}")
                    return None, None
                
                # Clean up image URL
                if isinstance(image_url, str):
                    if not image_url.startswith('http'):
                        image_url = f"https:{image_url}" if image_url.startswith('//') else f"https://www.amazon.in{image_url}"
                else:
                    # Handle JSON-encoded image URLs
                    import json
                    try:
                        image_urls = json.loads(image_url)
                        image_url = next(iter(image_urls.keys()))
                    except:
                        logger.error("Failed to parse image URL JSON")
                        return None, None
                
                logger.info(f"Successfully extracted details for: {title[:50]}...")
                return title, image_url
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout while fetching product")
            return None, None
        except Exception as e:
            logger.error(f"Error fetching product details: {type(e).__name__}: {str(e)}")
            return None, None

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
            # Count unposted products
            unposted_products = [p for p in product_manager.products if not p.posted]
            unposted_count = len(unposted_products)
            
            if unposted_count > 0:
                logger.info(f"Found {unposted_count} unposted products")
                
                # Only process unposted products
                for product in unposted_products:
                    index = product_manager.products.index(product)
                    logger.info(f"Processing product {index + 1}/{len(product_manager.products)}")
                    
                    # Try up to 3 times for each product
                    for attempt in range(3):
                        try:
                            # Get product details
                            title, image_url = await scraper.get_product_details(product)
                            
                            if not title or not image_url:
                                logger.warning(f"Attempt {attempt + 1}: Failed to get product details")
                                if attempt < 2:  # Only sleep if we're going to retry
                                    await asyncio.sleep(10)
                                continue
                            
                            # Post to Telegram
                            success = await poster.post_product(title, image_url, product.affiliate_link)
                            
                            if success:
                                # Update Excel file and memory
                                product_manager.update_product_status(index)
                                product.posted = True
                                logger.info(f"Successfully posted product {index + 1}")
                                # Force reload products to ensure we have the latest status
                                product_manager.load_products()
                                break  # Break retry loop on success
                            
                            logger.warning(f"Attempt {attempt + 1}: Failed to post product")
                            if attempt < 2:  # Only sleep if we're going to retry
                                await asyncio.sleep(10)
                            
                        except Exception as e:
                            logger.error(f"Error processing product: {type(e).__name__}: {str(e)}")
                            if attempt < 2:  # Only sleep if we're going to retry
                                await asyncio.sleep(10)
                    
                    # Wait between products to avoid rate limiting
                    await asyncio.sleep(60)
            
            # If no unposted products, wait longer before next check
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