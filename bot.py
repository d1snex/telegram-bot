import os
import requests
import psycopg2
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update, BotCommand
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)

    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning("Transient network error with Telegram → polling should retry automatically")

# Fetch Solana price from CoinGecko
def get_solana_price():
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd')
        data = response.json()
        return data['solana']['usd']
    except Exception as e:
        return f"Error fetching price: {e}"

# Define the /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    username = update.effective_chat.username
    print("Chat_id: ", chat_id)
    await update.message.reply_text('Hello! I am your Bitcoin price bot. Use /price to get the current Bitcoin price.')
    # Store chat_id for price updates
    context.bot_data['chat_id'] = chat_id

    # Store chat_id and username in database
    try:
        with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO telegram_users (chat_id, username) VALUES (%s, %s) ON CONFLICT (chat_id) DO NOTHING",
                    (chat_id, username)
                )
                conn.commit()
        update.message.reply_text("Your chat ID has been saved!")
    except Exception as e:
        update.message.reply_text(f"Error saving chat ID: {str(e)}")

# Define the /price command handler
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sol_price = get_solana_price()
    await update.message.reply_text(f'Current Solana price: ${sol_price}')

# Define the /list command handler
async def list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    try:
        with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT profile_id FROM followed_profiles WHERE chat_id = %s ORDER BY follow_date ASC;",
                    (chat_id,)
                )
                profiles = cur.fetchall()

        if not profiles:
            await update.message.reply_text("You don't follow any profiles yet.")
            return

        profile_list = "\n".join(f"{i+1}. {profile[0]}" for i, profile in enumerate(profiles))
        await update.message.reply_text(f"Profiles you follow:\n{profile_list}")

    except Exception as e:
        print(f"Error in /list: {e}")
        await update.message.reply_text("Sorry, there was an error retrieving your followed profiles. Try again later.")


# Define the /help command handler
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*Welcome to Apeye \\- your X posts AI evaluator\\!*\n\n"
        "I can do the following:\n\n"
        "• /start — get started\n"
        "• /price — current SOL price\n"
        "• /list — list currently monitored X profiles\n"
        "• /help — show this help\n\n"
        "Just type / to see the command menu\\."
    )
    await update.message.reply_text(
        help_text,
        parse_mode="MarkdownV2"
    )

async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start",  "Start the bot "),
        BotCommand("price",  "Get current SOL price"),
        BotCommand("list",  "List monitored X profiles"),
        BotCommand("help",   "Show help"),
    ]
    await application.bot.set_my_commands(commands)

def main() -> None:
    token = os.getenv('BOT_TOKEN')  # Get from env var
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set!")
    
    request = HTTPXRequest(
        connect_timeout = 20.0,
        read_timeout    = 45.0,
        write_timeout   = 30.0,
        pool_timeout    = 30.0,
    )

    # Build application and register post_init
    application = (
        Application.builder()
        .token(token)
        .request(request)           # ← attach custom request backend
        .post_init(post_init)
        .build()
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("list", list))
    application.add_handler(CommandHandler("help", help))

    application.add_error_handler(error_handler)

    # Start the bot
    print("Bot is running...")
    logger.info("Starting polling with increased timeouts...")
    application.run_polling(
        drop_pending_updates=True
    )

if __name__ == '__main__':
    main()