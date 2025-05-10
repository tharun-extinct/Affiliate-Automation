import os
import logging
from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s/n - %(name)s/n - %(levelname)s/n - %(message)s/n'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AmazonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        }

    def get_product_details(self) -> Tuple[str, Optional[str]]:
        """Scrape product details from Amazon."""
        # Reload environment variables
        load_dotenv(override=True)
        self.amazon_url = os.getenv('AMAZON_URL')
        
        try:
            response = requests.get(self.amazon_url, headers=self.headers, timeout=10)
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
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.affiliate_link = os.getenv('AFFILIATE_LINK')

    async def post_product(self, title: str, image_url: Optional[str]) -> None:
        """Post product to Telegram channel."""
        if not all([self.token, self.chat_id, self.affiliate_link]):
            logger.error("Missing required environment variables")
            return

        if not image_url:
            logger.error("No image URL available")
            return

        try:
            bot = Bot(token=self.token)
            caption = f"🛒 *{title}*\n🔗 [Buy Now]({self.affiliate_link})"
            
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode='Markdown'
            )
            logger.info("Posted to Telegram successfully!")
            
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")

async def main():
    # Initialize classes
    scraper = AmazonScraper()
    poster = TelegramPoster()
    
    # Get product details
    title, image_url = scraper.get_product_details()
    
    # Post to Telegram
    await poster.post_product(title, image_url)

if __name__ == "__main__":
    asyncio.run(main())