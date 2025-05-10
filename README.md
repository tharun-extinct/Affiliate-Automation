# Amazon Affiliate Product Automation

An automated system for scraping Amazon product details and posting them to Telegram channels with affiliate links. This project helps affiliate marketers automate their product posting workflow.

## Features

- 🔄 Continuous monitoring of product list from Excel
- 🛍️ Amazon product detail scraping
- 📱 Automated Telegram channel posting
- ⏱️ Time-managed posting with intervals
- 📊 Tracking of posted products
- 🔄 Auto-reload of new products

## Prerequisites

- Python 3.8+
- A Telegram Bot Token
- A Telegram Channel/Group ID
- Amazon Affiliate Account

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd affiliate-automation
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # For Unix
venv\Scripts\activate     # For Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file with your credentials:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=@your_channel_name
```

2. Set up your products list:
- Use `create_excel.py` to create initial `products.xlsx`
- Or create your own Excel file with columns:
  - amazon_url
  - affiliate_link
  - posted

## File Structure

- `main.py` - Main application script
- `create_excel.py` - Helper script to create products Excel file
- `requirements.txt` - Python dependencies
- `products.xlsx` - Product database (not in repo)
- `.env` - Environment variables (not in repo)

## Usage

1. Add your products to `products.xlsx`:
   - `amazon_url`: Original Amazon product URL
   - `affiliate_link`: Your affiliate link for the product
   - `posted`: Leave as FALSE (will be auto-updated)

2. Run the script:
```bash
python main.py
```

The script will:
- Load products from Excel
- Scrape product details from Amazon
- Post to Telegram with 1-minute intervals
- Mark products as posted
- Check for new products every 5 minutes

## Classes Overview

### ProductManager
- Handles Excel file operations
- Loads and tracks product status

### AmazonScraper
- Manages Amazon product scraping
- Extracts titles and images

### TelegramPoster
- Handles Telegram bot operations
- Posts products with formatted messages

## Best Practices

1. **Rate Limiting**:
   - Default 1-minute gap between posts
   - 5-minute reload interval
   - Adjust in `main.py` if needed

2. **Error Handling**:
   - Failed posts won't be marked as posted
   - Logs errors for debugging
   - Continues operation on errors

3. **Data Management**:
   - Keep `products.xlsx` backed up
   - Don't commit sensitive data
   - Use `.gitignore` for secrets

## Logging

The application logs important events with timestamps:
- Product loading
- Posting success/failure
- Error messages
- Status updates

## Security Notes

- Keep your `.env` file secure
- Don't share your Telegram bot token
- Protect your affiliate links
- Use proper User-Agent headers

## Contributing

1. Follow Python best practices
2. Maintain error handling
3. Update requirements.txt
4. Test thoroughly before commits

## Troubleshooting

Common issues:
1. Excel file not found
   - Ensure `products.xlsx` exists
   - Check file permissions

2. Telegram posting fails
   - Verify bot token
   - Confirm channel ID
   - Check bot channel permissions

3. Amazon scraping issues
   - Update User-Agent
   - Check URL format
   - Verify product availability

## License

This project is licensed under the MIT License - see the LICENSE file for details.