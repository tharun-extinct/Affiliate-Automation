from telegram import Bot
import logging
from typing import Optional
from dotenv import load_dotenv
import os

logger = logging.getLogger(__name__)


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
            caption = f"🛒 *{title}*\n\n🔗 [Buy Now]({affiliate_link})"
            
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=image_url,
                caption=caption,
                parse_mode='Markdown'
            )
            #logger.info(f"Posted product: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")
            return False