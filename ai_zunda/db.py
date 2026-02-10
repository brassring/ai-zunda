import logging
import os

import aiosqlite

from .config import DB_NAME

log = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def init_db():
    global _db
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        log.info("既存 DB ファイルを削除: %s", DB_NAME)
    _db = await aiosqlite.connect(DB_NAME)
    await _db.execute("""
        CREATE TABLE IF NOT EXISTS voice_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await _db.commit()
    log.info("DB 初期化完了 (%s)", DB_NAME)


async def save_log(user_id: int, user_name: str, text: str):
    if _db is None:
        log.warning("DB 未初期化のため保存スキップ")
        return
    try:
        await _db.execute(
            "INSERT INTO voice_logs (user_id, user_name, text) VALUES (?, ?, ?)",
            (user_id, user_name, text),
        )
        await _db.commit()
        log.debug("DB 保存: user_id=%s, user_name=%s", user_id, user_name)
    except Exception:
        log.exception("DB 保存エラー")


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        log.info("DB 接続を閉じました")
