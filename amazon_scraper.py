from bs4 import BeautifulSoup
import logging
from typing import Tuple, Optional
import asyncio
from product_manager import Product

logger = logging.getLogger(__name__)


class AmazonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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
            from urllib.parse import unquote, urlparse
            clean_url = unquote(product.amazon_url).strip()
            
            # Parse the URL
            parsed_url = urlparse(clean_url)
            if not parsed_url.scheme:
                clean_url = f"https://www.amazon.in/{clean_url.lstrip('/')}"
            
            # Extract product ID if present
            if '/dp/' in clean_url:
                product_id = clean_url.split('/dp/')[1].split('/')[0]
                clean_url = f"https://www.amazon.in/dp/{product_id}"
            
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
                    '.a-size-large.product-title-word-break'
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
                    'img[data-a-dynamic-image]'
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
