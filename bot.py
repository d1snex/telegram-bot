import os
import requests
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update  # Add this import

# Fetch Bitcoin price from CoinGecko
def get_bitcoin_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
        data = response.json()
        return data['bitcoin']['usd']
    except Exception as e:
        return f"Error fetching price: {e}"

# Define the /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    print("Chat_id: ", chat_id)
    await update.message.reply_text('Hello! I am your Bitcoin price bot. Use /price to get the current Bitcoin price.')
    # Store chat_id for price updates
    context.bot_data['chat_id'] = chat_id
    # Schedule price updates every 10 minutes (600 seconds)
    # context.job_queue.run_repeating(send_price_update, interval=15, first=10, data=chat_id)

# Define the /price command handler
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    btc_price = get_bitcoin_price()
    await update.message.reply_text(f'Current Bitcoin price: ${btc_price}')

# Function to send periodic price updates
async def send_price_update(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data  # Retrieve chat_id from data
    btc_price = get_bitcoin_price()
    await context.bot.send_message(chat_id=chat_id, text=f'Bitcoin price update: ${btc_price}')

def main() -> None:
    token = os.getenv('BOT_TOKEN')  # Get from env var
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set!")
    application = Application.builder().token(token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()