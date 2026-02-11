import os
import requests
import psycopg2
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update, BotCommand  # Add this import

# Fetch Bitcoin price from CoinGecko
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

    # Store chat_id and username in database
    try:
        with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT profile_id FROM followed_profiles WHERE chat_id = %s ORDER BY follow_date ASC;",
                    (chat_id,)
                )
                profiles = cur.fetchall()
                cur.close()
                conn.close()
                
                if not profiles:
                    await update.message.reply("You don't follow any profiles yet.")
                    return
                
                # Format as a numbered list (or comma-separated, etc.)
                profile_list = "\n".join(f"{i+1}. {profile[0]}" for i, profile in enumerate(profiles))
                await update.message.reply(f"Profiles you follow:\n{profile_list}")

    except Exception as e:
        await update.message.reply("Sorry, there was an error retrieving your followed profiles. Try again later.")


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
    
     # Build application and register post_init
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)          # ← this is the key addition
        .build()
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("list", list))
    application.add_handler(CommandHandler("help", help))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()