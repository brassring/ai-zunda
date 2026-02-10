import logging
import re
from collections.abc import AsyncGenerator

from ollama import AsyncClient as OllamaClient

from .config import MODEL_NAME, ZUNDAMON_SYSTEM_PROMPT

log = logging.getLogger(__name__)

_SENTENCE_END = re.compile(r"[。！？!?]")


async def stream_sentences(
    client: OllamaClient, text: str, name: str
) -> AsyncGenerator[str]:
    prompt = f"【相手の名前: {name}】\n発言内容: {text}"

    log.debug("LLM リクエスト開始: model=%s, name=%s", MODEL_NAME, name)

    buffer = ""
    stream = await client.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": ZUNDAMON_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.7},
        stream=True,
    )

    async for chunk in stream:
        token = chunk["message"]["content"]
        buffer += token

        while True:
            match = _SENTENCE_END.search(buffer)
            if not match:
                break
            sentence = buffer[: match.end()].strip()
            buffer = buffer[match.end() :]
            if sentence:
                log.debug("LLM 文生成: %s", sentence)
                yield sentence

    if buffer.strip():
        log.debug("LLM 文生成 (残余): %s", buffer.strip())
        yield buffer.strip()

    log.debug("LLM ストリーム完了")
