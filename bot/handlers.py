import logging

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

import bot.ovpn_manager as ovpn_manager
from bot.access import restricted
from bot.config import Config

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "OpenVPN Management Bot\n\n"
    "Команды:\n"
    "/create <username> — Создать VPN-клиента\n"
    "/revoke <username> — Отозвать сертификат клиента\n"
    "/list — Список активных клиентов\n"
    "/help — Показать справку"
)


def register_handlers(application, config: Config):
    r = restricted(config.allowed_user_ids)
    application.add_handler(CommandHandler("start", r(cmd_start)))
    application.add_handler(CommandHandler("help", r(cmd_help)))
    application.add_handler(CommandHandler("create", r(cmd_create)))
    application.add_handler(CommandHandler("revoke", r(cmd_revoke)))
    application.add_handler(CommandHandler("list", r(cmd_list)))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT)


async def cmd_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config: Config = context.bot_data["config"]

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Использование: /create <username>")
        return

    client_name = context.args[0]

    if not ovpn_manager.validate_client_name(client_name):
        await update.message.reply_text(
            "Некорректное имя. Допустимы буквы, цифры, дефис, подчёркивание (1-63 символа)."
        )
        return

    await update.message.reply_text(f"Создаю клиента '{client_name}'...")

    success, ovpn_path, message = await ovpn_manager.create_client(
        script_path=config.ovpn_script_path,
        client_name=client_name,
        output_dir=config.output_dir,
        cert_days=config.cert_days,
    )

    if success and ovpn_path and ovpn_path.exists():
        try:
            with open(ovpn_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"{client_name}.ovpn",
                    caption=f"Конфиг для '{client_name}' (срок: {config.cert_days} дней)",
                )
        except Exception as e:
            logger.exception("Failed to send .ovpn file")
            await update.message.reply_text(
                f"Клиент создан, но не удалось отправить файл: {e}"
            )
        finally:
            try:
                ovpn_path.unlink(missing_ok=True)
            except OSError as e:
                logger.warning("Failed to clean up %s: %s", ovpn_path, e)
    else:
        await update.message.reply_text(message)


async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config: Config = context.bot_data["config"]

    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Использование: /revoke <username>")
        return

    client_name = context.args[0]

    if not ovpn_manager.validate_client_name(client_name):
        await update.message.reply_text("Некорректное имя клиента.")
        return

    await update.message.reply_text(f"Отзываю клиента '{client_name}'...")

    success, message = await ovpn_manager.revoke_client(
        script_path=config.ovpn_script_path,
        client_name=client_name,
    )
    await update.message.reply_text(message)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config: Config = context.bot_data["config"]

    success, output = await ovpn_manager.list_clients(
        script_path=config.ovpn_script_path,
    )

    if success:
        await update.message.reply_text(f"Активные клиенты:\n\n{output}")
    else:
        await update.message.reply_text(output)
