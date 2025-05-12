
import logging
from amazon_scraper import AmazonScraper
from product_manager import ProductManager
from telegram_poster import TelegramPoster
#import requests
import asyncio


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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