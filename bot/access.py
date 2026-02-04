import functools
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def restricted(allowed_user_ids: frozenset[int]):
    """Decorator that restricts handler to whitelisted Telegram user IDs."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            user = update.effective_user
            if user is None or user.id not in allowed_user_ids:
                uid = user.id if user else "unknown"
                uname = user.username if user else "unknown"
                logger.warning(
                    "Unauthorized access attempt: user_id=%s username=%s", uid, uname
                )
                if update.message:
                    await update.message.reply_text("Доступ запрещён.")
                return
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
