import logging
import sys
from pathlib import Path

from telegram.ext import Application

from bot.config import load_config
from bot.handlers import register_handlers


def setup_logging(log_level: str, log_file: str):
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    handlers = [
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(log_file),
    ]

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    config = load_config()
    setup_logging(config.log_level, config.log_file)

    logger = logging.getLogger(__name__)
    logger.info("Starting OpenVPN Telegram Bot")
    logger.info("Allowed user IDs: %s", config.allowed_user_ids)
    logger.info("Script path: %s", config.ovpn_script_path)
    logger.info("Output dir: %s", config.output_dir)

    app = Application.builder().token(config.bot_token).build()
    app.bot_data["config"] = config

    register_handlers(app, config)

    logger.info("Bot is polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
