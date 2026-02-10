import logging
import os
from pathlib import Path

# nvidia cublas DLL を PATH に追加 — ctranslate2 import より前に実行
try:
    import nvidia.cublas as _cublas
    _bin = str(Path(_cublas.__path__[0]) / "bin")
    os.environ["PATH"] = _bin + os.pathsep + os.environ["PATH"]
except ImportError:
    pass

import ctranslate2
from faster_whisper import WhisperModel

log = logging.getLogger(__name__)


def _init_model() -> WhisperModel:
    if ctranslate2.get_cuda_device_count() > 0:
        log.info("CUDA GPU 検出 — GPU モードで起動")
        try:
            return WhisperModel("small", device="cuda", compute_type="float16")
        except Exception:
            log.warning("GPU 初期化失敗 — CPU にフォールバック", exc_info=True)
    else:
        log.info("CUDA GPU 未検出 — CPU モードで起動")
    return WhisperModel("small", device="cpu", compute_type="int8")


log.info("Whisper モデルを読み込み中...")
_model = _init_model()
log.info("Whisper モデル読み込み完了")

_NG_WORDS = ["ご視聴", "ありがとうございました", "チャンネル登録", "字幕"]


def transcribe(filename: str) -> str | None:
    segments, _ = _model.transcribe(
        filename,
        language="ja",
        beam_size=1,
        vad_filter=True,
    )
    text = "".join(s.text for s in segments).strip()

    if len(text) <= 1:
        log.debug("文字起こし結果が短すぎるためスキップ: %r", text)
        return None
    if any(w in text for w in _NG_WORDS):
        log.debug("NGワード検出 - スキップ: %r", text)
        return None

    log.debug("文字起こし完了: %s", text)
    return text
