import os
from dataclasses import dataclass

@dataclass
class Config:
    bot_token: str = os.environ.get("BOT_TOKEN", "")
    openai_key: str = os.environ.get("OPENAI_API_KEY", "")
    db_password: str = os.environ.get("DB_PASSWORD", "")
    admin_chat_id: str = os.environ.get("ADMIN_CHAT_ID", "")
    db_host: str = "eco-scan-ecobot.e.aivencloud.com"
    db_port: str = "10408"
    db_name: str = "defaultdb"
    db_user: str = "avnadmin"

config = Config()