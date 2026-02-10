# ai-zunda

Discord ボイスチャットに常駐し、ユーザーの発話を聞き取って「ずんだもん」として音声で返答する Bot。

## 構成

| コンポーネント | 役割 |
|---|---|
| [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) | 音声認識 (STT) — GPU 自動検出対応 |
| [Ollama](https://ollama.com/) | LLM による応答生成 |
| [VOICEVOX](https://voicevox.hiroshiba.jp/) | 音声合成 (TTS) — ずんだもんボイス |
| [discord.py](https://discordpy.readthedocs.io/) + [voice-recv](https://github.com/imayhaveborkedit/discord-ext-voice-recv) | VC 録音・再生 |

## 必要なもの

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [FFmpeg](https://ffmpeg.org/) (PATH に追加済みであること)
- Ollama (起動済み)
- VOICEVOX ENGINE (起動済み)
- Discord Bot トークン

## セットアップ

```bash
git clone <repository-url>
cd ai-zunda
```

`.env` ファイルをプロジェクトルートに作成:

```
DISCORD_TOKEN=your-discord-bot-token
VOICEVOX_URL=http://127.0.0.1:50021
MODEL_NAME=llama3:8b
```

## 起動

`start.bat` をダブルクリック、または:

```bash
uv run python -m ai_zunda
```

NVIDIA GPU 搭載の場合、`start.bat` が自動検出して GPU モードで起動する。
手動で GPU 依存を含めて起動する場合:

```bash
uv run --extra gpu python -m ai_zunda
```

## Bot コマンド

| コマンド | 説明 |
|---|---|
| `!join` | Bot を VC に参加させる |
| `!start` | 聞き取りを開始する |
| `!stop` | 聞き取りを停止する |
| `!leave` | Bot を VC から退出させる |

## プロジェクト構成

```
ai_zunda/
  __main__.py   # エントリポイント・Bot セットアップ
  config.py     # 環境変数・ロギング設定
  stt.py        # Faster Whisper による音声認識
  tts.py        # VOICEVOX による音声合成
  llm.py        # Ollama によるストリーミング応答生成
  db.py         # SQLite ログ管理
  cogs/
    voice.py    # VC 録音・再生・パイプライン制御
```
