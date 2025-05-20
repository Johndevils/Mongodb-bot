import logging
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient, errors
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory user session storage
user_sessions = {}

class MongoDBTransferBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        self.port = int(os.getenv("PORT", 8080))
        self.app = Application.builder().token(self.token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command handlers"""
        handlers = [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help),
            CommandHandler("set_source", self.set_source),
            CommandHandler("set_target", self.set_target),
            CommandHandler("transfer", self.transfer),
        ]
        for handler in handlers:
            self.app.add_handler(handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message handler"""
        user = update.effective_user
        await update.message.reply_html(
            rf"👋 Hi {user.mention_html()}! I'm your MongoDB Transfer Bot."
            "\n\nUse /help to see available commands."
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        help_text = """
📚 **Available Commands**:
- /start - Show welcome message
- /help - Display this help message
- /set_source <URI> - Set source MongoDB connection URI
- /set_target <URI> - Set target MongoDB connection URI
- /transfer <src_collection> <dest_collection> - Transfer data between collections

🔍 **Examples**:
- /set_source mongodb://user:pass@host:27017/source_db
- /set_target mongodb://user:pass@host:27017/target_db
- /transfer users users_backup
"""
        await update.message.reply_text(help_text)

    async def set_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set source MongoDB URI"""
        chat_id = update.message.chat_id
        if not context.args:
            await update.message.reply_text("❌ Please provide a MongoDB URI. Usage: /set_source <URI>")
            return

        user_sessions[chat_id] = user_sessions.get(chat_id, {})
        user_sessions[chat_id]['source_uri'] = context.args[0]
        await update.message.reply_text("✅ Source URI set successfully!")
        logger.info(f"Set source URI for chat {chat_id}")

    async def set_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set target MongoDB URI"""
        chat_id = update.message.chat_id
        if not context.args:
            await update.message.reply_text("❌ Please provide a MongoDB URI. Usage: /set_target <URI>")
            return

        user_sessions[chat_id] = user_sessions.get(chat_id, {})
        user_sessions[chat_id]['target_uri'] = context.args[0]
        await update.message.reply_text("✅ Target URI set successfully!")
        logger.info(f"Set target URI for chat {chat_id}")

    async def transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data transfer between MongoDB collections"""
        chat_id = update.message.chat_id
        session = user_sessions.get(chat_id, {})

        # Validate input
        if not context.args or len(context.args) != 2:
            await update.message.reply_text("❌ Usage: /transfer <source_collection> <target_collection>")
            return
        if 'source_uri' not in session or 'target_uri' not in session:
            await update.message.reply_text("❌ Please set both source and target URIs first!")
            return

        src_collection, tgt_collection = context.args
        src_uri, tgt_uri = session['source_uri'], session['target_uri']

        try:
            # Establish connections
            with MongoClient(src_uri) as src_client, MongoClient(tgt_uri) as tgt_client:
                src_db = self._get_database(src_client, src_uri)
                tgt_db = self._get_database(tgt_client, tgt_uri)

                # Perform data transfer
                docs = list(src_db[src_collection].find())
                if not docs:
                    await update.message.reply_text("ℹ️ No documents found in source collection")
                    return

                tgt_db[tgt_collection].insert_many(docs)
                await update.message.reply_text(
                    f"✅ Successfully transferred {len(docs)} documents "
                    f"from {src_collection} to {tgt_collection}"
                )
                logger.info(f"Transferred {len(docs)} docs for chat {chat_id}")

        except errors.PyMongoError as e:
            await update.message.reply_text(f"❌ MongoDB Error: {str(e)}")
            logger.error(f"MongoDB error: {str(e)}")
        except Exception as e:
            await update.message.reply_text(f"❌ Unexpected error: {str(e)}")
            logger.error(f"Unexpected error: {str(e)}")

    def _get_database(self, client, uri):
        """Extract database name from URI"""
        db_name = uri.split('/')[-1].split('?')[0]
        return client[db_name] if db_name else client.get_database()

    async def startup_notification(self):
        """Send notification when bot starts"""
        if self.admin_chat_id:
            try:
                await self.app.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text="🚀 Bot deployed successfully!\n"
                         f"Service URL: {os.getenv('RENDER_EXTERNAL_URL', 'N/A')}"
                )
            except Exception as e:
                logger.error(f"Failed to send startup notification: {str(e)}")

    async def web_handler(self):
        """Simple web server for health checks"""
        async def handle(request):
            return web.Response(text="Arsynox Successfully")

        app = web.Application()
        app.router.add_get('/', handle)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"Web server running on port {self.port}")
        while True:
            await asyncio.sleep(3600)  # Run indefinitely

    def run(self):
        """Start bot and web server"""
        async def main():
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Start web server and send notification
            await asyncio.gather(
                self.web_handler(),
                self.startup_notification()
            )

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main())
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            loop.run_until_complete(self.app.stop())
            loop.close()

if __name__ == "__main__":
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.error("TELEGRAM_BOT_TOKEN environment variable missing!")
        exit(1)
    MongoDBTransferBot().run()
