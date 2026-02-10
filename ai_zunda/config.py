import logging
import logging.handlers
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

TOKEN = os.getenv("DISCORD_TOKEN", "")
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3:8b")
DB_NAME = os.getenv("DB_NAME", "zundamon_history.db")
LOG_FILE = os.getenv("LOG_FILE", "ai_zunda.log")

ZUNDAMON_SYSTEM_PROMPT = (
    "あなたは東北ずん子公式マスコット『ずんだもん』なのだ。"
    "一人称は必ず『ぼく』を使うのだ。"
    "語尾は必ず『〜なのだ。』で終わらせること。"
    "相手の名前を使って、親しみやすく1〜2文で短く話すのだ。"
)


def setup_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, encoding="utf-8", maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger("ai_zunda")
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
