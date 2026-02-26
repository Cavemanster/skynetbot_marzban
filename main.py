"""
VPN Bot for Marzban - Main Entry Point
Telegram bot for managing VPN subscriptions via Marzban panel
"""

import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

# Load environment variables
load_dotenv()

# Import modules
from database import Database
from marzban_client import MarzbanClient, AuthenticationError
from handlers_user import user_router
from handlers_admin import admin_router, is_admin
from background_tasks import start_background_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8")
    ]
)

# Create logs directory
Path("logs").mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


class Config:
    """Bot configuration"""
    
    def __init__(self):
        # Bot configuration
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        
        # Admin configuration
        self.ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")
        
        # Marzban configuration
        self.MARZBAN_PANEL_URL = os.getenv("MARZBAN_PANEL_URL", "")
        self.MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "")
        self.MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "")
        self.MARZBAN_SUBSCRIPTION_URL_PREFIX = os.getenv(
            "MARZBAN_SUBSCRIPTION_URL_PREFIX", 
            self.MARZBAN_PANEL_URL
        )
        
        # Payment configuration
        self.PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
        self.PAYMENT_CARD_HOLDER = os.getenv("PAYMENT_CARD_HOLDER", "")
        
        # Optional configuration
        self.SITE_URL = os.getenv("SITE_URL", "")
        self.TG_CHANNEL = os.getenv("TG_CHANNEL", "")
        self.SUPPORT_URL = os.getenv("SUPPORT_URL", "")
        self.REF_BONUS_DAYS = int(os.getenv("REF_BONUS_DAYS", "7"))
        self.VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"
        
        # Notification settings
        notify_hours = os.getenv("NOTIFY_BEFORE_EXPIRE_HOURS", "24,48,72")
        self.NOTIFY_BEFORE_EXPIRE_HOURS = [int(h) for h in notify_hours.split(",")]

    def to_dict(self) -> dict:
        """Convert config to dictionary"""
        return {
            "BOT_TOKEN": self.BOT_TOKEN,
            "ADMIN_USER_IDS": self.ADMIN_USER_IDS,
            "MARZBAN_PANEL_URL": self.MARZBAN_PANEL_URL,
            "MARZBAN_USERNAME": self.MARZBAN_USERNAME,
            "MARZBAN_PASSWORD": self.MARZBAN_PASSWORD,
            "MARZBAN_SUBSCRIPTION_URL_PREFIX": self.MARZBAN_SUBSCRIPTION_URL_PREFIX,
            "PAYMENT_CARD_NUMBER": self.PAYMENT_CARD_NUMBER,
            "PAYMENT_CARD_HOLDER": self.PAYMENT_CARD_HOLDER,
            "SITE_URL": self.SITE_URL,
            "TG_CHANNEL": self.TG_CHANNEL,
            "SUPPORT_URL": self.SUPPORT_URL,
            "REF_BONUS_DAYS": self.REF_BONUS_DAYS,
            "VERIFY_SSL": self.VERIFY_SSL,
            "NOTIFY_BEFORE_EXPIRE_HOURS": self.NOTIFY_BEFORE_EXPIRE_HOURS,
        }

    def validate(self) -> bool:
        """Validate required configuration"""
        required = ["BOT_TOKEN", "MARZBAN_PANEL_URL", "MARZBAN_USERNAME", "MARZBAN_PASSWORD"]
        missing = [key for key in required if not getattr(self, key)]
        
        if missing:
            logger.error(f"Missing required configuration: {missing}")
            return False
        
        if not self.ADMIN_USER_IDS or self.ADMIN_USER_IDS[0] == "":
            logger.error("No admin user IDs configured")
            return False
        
        return True


async def on_startup(bot: Bot, db: Database, marzban_client: MarzbanClient, config: Config):
    """Bot startup handler"""
    logger.info("Bot starting up...")
    
    # Test Marzban connection
    try:
        await marzban_client.get_system_stats()
        logger.info("Connected to Marzban panel successfully")
    except AuthenticationError as e:
        logger.error(f"Marzban authentication failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to connect to Marzban: {e}")
        sys.exit(1)
    
    # Initialize database
    await db.connect()
    logger.info("Database initialized")

    # Start background tasks
    await start_background_tasks(db, marzban_client, bot, config)
    
    # Set bot commands
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="admin", description="Админ панель"),
    ])
    
    logger.info("Bot startup completed")


async def on_shutdown(bot: Bot, db: Database, marzban_client: MarzbanClient):
    """Bot shutdown handler"""
    logger.info("Bot shutting down...")
    
    await marzban_client.close()
    await db.close()
    await bot.session.close()
    
    logger.info("Bot shutdown completed")


async def error_handler(error: ErrorEvent, bot: Bot):
    """Global error handler"""
    logger.error(f"Global error: {error}", exc_info=error.exception)
    
    # Notify admins
    config = Config()
    for admin_id in config.ADMIN_USER_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⚠️ Ошибка в боте:\n\n"
                f"```\n{str(error.exception)}\n```",
                parse_mode="Markdown"
            )
        except Exception:
            pass


def create_dispatcher(config: Config, db: Database, marzban_client: MarzbanClient) -> Dispatcher:
    """Create and configure dispatcher"""
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include routers
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    # Add middleware for config and database
    @dp.update.middleware()
    async def config_middleware(handler, event, data):
        data["config"] = config
        data["db"] = db
        data["marzban_client"] = marzban_client
        return await handler(event, data)

    # Admin filter
    @dp.message(F.from_user.id.map(lambda x: str(x) in config.ADMIN_USER_IDS))
    async def admin_only(message: types.Message):
        pass
    
    # Error handler
    dp.errors.register(error_handler)
    
    # Startup/Shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    return dp


async def main():
    """Main function"""
    # Load configuration
    config = Config()
    
    if not config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    logger.info("Configuration loaded successfully")
    
    # Create bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Create database and Marzban client
    db = Database()
    marzban_client = MarzbanClient(
        panel_url=config.MARZBAN_PANEL_URL,
        username=config.MARZBAN_USERNAME,
        password=config.MARZBAN_PASSWORD,
        subscription_prefix=config.MARZBAN_SUBSCRIPTION_URL_PREFIX,
        verify_ssl=config.VERIFY_SSL
    )
    
    # Store config in bot for access in handlers
    bot.config = config
    bot.marzban_client = marzban_client

    # Create dispatcher
    dp = create_dispatcher(config, db, marzban_client)

    # Store additional data in bot for handlers
    dp["config"] = config
    dp["db"] = db
    dp["marzban_client"] = marzban_client
    
    try:
        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await on_shutdown(bot, db, marzban_client)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
