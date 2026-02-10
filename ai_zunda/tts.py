import logging

import aiohttp

from .config import VOICEVOX_URL

log = logging.getLogger(__name__)

_QUERY_TIMEOUT = aiohttp.ClientTimeout(total=5)
_SYNTH_TIMEOUT = aiohttp.ClientTimeout(total=15)


async def synthesize(session: aiohttp.ClientSession, text: str) -> bytes | None:
    params = {"text": text, "speaker": 3}
    try:
        async with session.post(
            f"{VOICEVOX_URL}/audio_query",
            params=params,
            timeout=_QUERY_TIMEOUT,
        ) as r1:
            q = await r1.json()
        q["speedScale"] = 1.05
        async with session.post(
            f"{VOICEVOX_URL}/synthesis",
            params=params,
            json=q,
            timeout=_SYNTH_TIMEOUT,
        ) as r2:
            data = await r2.read()
        log.debug("音声合成完了: %d bytes (%s)", len(data), text)
        return data
    except Exception:
        log.exception("VOICEVOX エラー (text=%s)", text)
        return None
