import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_user_ids: frozenset[int]
    ovpn_script_path: Path
    output_dir: Path
    cert_days: int = 365
    log_level: str = "INFO"
    log_file: str = "/var/log/ecos-tg-bot-ovpn/bot.log"


def load_config(env_path: str = ".env") -> Config:
    load_dotenv(env_path)

    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")

    raw_ids = os.environ.get("ALLOWED_USER_IDS", "")
    allowed_user_ids = frozenset(
        int(uid.strip()) for uid in raw_ids.split(",") if uid.strip()
    )
    if not allowed_user_ids:
        raise ValueError("ALLOWED_USER_IDS must contain at least one ID")

    ovpn_script_path = Path(
        os.environ.get(
            "OVPN_SCRIPT_PATH",
            "/u01/ovpn/openvpn-install/openvpn-install.sh",
        )
    )

    output_dir = Path(os.environ.get("OUTPUT_DIR", "/tmp/ovpn_configs"))
    cert_days = int(os.environ.get("CERT_DAYS", "365"))
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_file = os.environ.get("LOG_FILE", "/var/log/ecos-tg-bot-ovpn/bot.log")

    return Config(
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
        ovpn_script_path=ovpn_script_path,
        output_dir=output_dir,
        cert_days=cert_days,
        log_level=log_level,
        log_file=log_file,
    )
