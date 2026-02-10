import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

from ollama import AsyncClient as OllamaClient

from .config import MODEL_NAME, ZUNDAMON_SYSTEM_PROMPT

log = logging.getLogger(__name__)

_SENTENCE_END = re.compile(r"[。！？!?]")


async def _stream_tokens_ollama(client: OllamaClient, prompt: str) -> AsyncGenerator[str]:
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
        yield chunk["message"]["content"]


async def _stream_tokens_claude(prompt: str) -> AsyncGenerator[str]:
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--system-prompt", ZUNDAMON_SYSTEM_PROMPT,
        "--tools", "",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdout is not None
    yielded = False
    async for raw_line in proc.stdout:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type")

        if etype == "assistant" and not yielded:
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text"):
                    yielded = True
                    yield block["text"]

        elif etype == "result" and not yielded:
            result_text = event.get("result", "")
            if result_text:
                yield result_text

    if proc.stderr:
        stderr_data = await proc.stderr.read()
        if stderr_data:
            log.warning("Claude CLI stderr: %s", stderr_data.decode("utf-8", errors="replace")[:500])

    exit_code = await proc.wait()
    if exit_code != 0:
        log.error("Claude CLI 終了コード: %d", exit_code)


async def stream_sentences(
    client, text: str, name: str, *, backend: str = "ollama"
) -> AsyncGenerator[str]:
    prompt = f"【相手の名前: {name}】\n発言内容: {text}"

    log.debug("LLM リクエスト開始: backend=%s, name=%s", backend, name)

    if backend == "claude":
        token_stream = _stream_tokens_claude(prompt)
    else:
        token_stream = _stream_tokens_ollama(client, prompt)

    buffer = ""
    async for token in token_stream:
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
