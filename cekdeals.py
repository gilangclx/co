import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import httpx
import json

# Suppress logs for httpx and telegram libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Setup logging for your bot (optional, can be set to WARNING to avoid clutter)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)

# URL endpoint
url = "https://m.dana.id/wallet/api/dana.dealsprod.brand.queryBrand.json?ctoken=ZH8c-zkPpr7nr9Zb"

# Headers for the request
headers = {
    "X-Timestamp": "1750935822765",
    "referer": "https://m.dana.id/n/dana-deals-v2/deals/search?remainingSeconds=30",
    "accept-language": "id-ID,id;q=0.9,en",
    "X-Local-Config": "0",
    "User-Agent": "Skywalker/2.55.0 EDIK/1.0.0 Dalvik/2.1.0 (Linux; U; Android 11; Redmi 14 Build/RQ3A.211001.001) Ariver/2.52.0 LocalKit/1.5.1.3  Lang/id-ID okhttp/3.12.12",
    "X-UTDID": "",
    "X-Client-Key": "",
    "X-Nonce": "",
    "x-fe-request-id": "undefined",
    "X-Sign": "",
    "x-fe-version": "1.29.0",
    "X-AppKey": "23936057",
    "X-Location": "",
    "x-rds": "",
    "X-Apdid-Token": "",
    "Accept-Language": "id_ID",
    "Cookie": "",
    "X-Location": ""
}

# Function to send the request and return formatted data
async def send_post_request(keyword: str):
    payload = {
        "brandPagination": {
            "page": 1,
            "size": 10
        },
        "providerPagination": {
            "page": 1,
            "size": 10
        },
        "providerGoodsPagination": {
            "page": 1,
            "size": 10
        },
        "keyword": keyword,
        "filters": [],
        "sorting": None,
        "category": None,
        "brandId": None
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            response_json = response.json()
            vouchers = response_json.get('result', {}).get('brands', [])
            output = ""
            for brand in vouchers:
                for provider in brand.get('providerInfos', []):
                    for voucher in provider.get('goodsInfos', []):
                        voucher_name = voucher.get('goodsTitle', 'N/A')
                        price = voucher.get('voucherPrice', {}).get('amount', 0)
                        output += f"{voucher_name}, Price: Rp {price:,}\n"
            return output if output else "No data found."
        else:
            return f"Error occurred. Status code: {response.status_code}"

# Start command handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Please enter the keyword to search:")

# Message handler for user input
async def handle_message(update: Update, context: CallbackContext):
    user_input = update.message.text
    result = await send_post_request(user_input)
    await update.message.reply_text(result)

# Main function to run the bot
def main():
    # Replace 'YOUR_API_KEY' with your actual Telegram bot API token
    application = Application.builder().token("8079874285:AAGyx-XBx1r-jQ3lNpCdHoIhVqeaBpC_ZVY").build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
