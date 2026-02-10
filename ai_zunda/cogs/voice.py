import logging
import os
import asyncio
import tempfile

import discord
from discord.ext import commands, voice_recv

from ..stt import transcribe
from ..tts import synthesize
from ..llm import stream_sentences
from ..db import save_log

log = logging.getLogger(__name__)


class _TrackingSink(voice_recv.AudioSink):
    """WaveSink をラップし、発話者を記録するシンク。"""

    def __init__(self, filename: str):
        super().__init__()
        self._inner = voice_recv.WaveSink(filename)
        self.speakers: dict[int, discord.Member] = {}

    def write(self, user, data):
        if user is not None:
            self.speakers[user.id] = user
        self._inner.write(user, data)

    def wants_opus(self) -> bool:
        return self._inner.wants_opus()

    def cleanup(self):
        self._inner.cleanup()


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_listening = False

    async def _play_audio(self, ctx: commands.Context, audio_data: bytes):
        if not (ctx.voice_client and ctx.voice_client.is_connected()):
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        try:
            tmp.write(audio_data)
            tmp.close()
            ctx.voice_client.play(discord.FFmpegPCMAudio(tmp.name))
            while ctx.voice_client.is_playing():
                await asyncio.sleep(0.05)
        finally:
            try:
                os.remove(tmp.name)
            except OSError:
                pass

    async def _stream_ai_and_speak(
        self, ctx: commands.Context, user_text: str, user_name: str
    ):
        audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        tts_tasks: asyncio.Queue[asyncio.Task[bytes | None] | None] = asyncio.Queue()

        async def feeder():
            while True:
                task = await tts_tasks.get()
                if task is None:
                    break
                try:
                    audio_data = await task
                    if audio_data:
                        await audio_queue.put(audio_data)
                except Exception:
                    log.exception("TTS タスク失敗")
            await audio_queue.put(None)

        async def player():
            while True:
                audio_data = await audio_queue.get()
                if audio_data is None:
                    break
                await self._play_audio(ctx, audio_data)

        feeder_task = asyncio.create_task(feeder())
        player_task = asyncio.create_task(player())
        sentences: list[str] = []

        try:
            async for sentence in stream_sentences(
                self.bot.llm_client, user_text, user_name,
                backend=self.bot.llm_backend,
            ):
                sentences.append(sentence)
                task = asyncio.create_task(
                    synthesize(self.bot.http_session, sentence)
                )
                await tts_tasks.put(task)
        except Exception:
            log.exception("AI 連携エラー (user=%s)", user_name)
            error_msg = f"{user_name}さん、ごめんなのだ。エラーが発生したのだ。"
            task = asyncio.create_task(
                synthesize(self.bot.http_session, error_msg)
            )
            await tts_tasks.put(task)
            sentences = [error_msg]
        finally:
            await tts_tasks.put(None)
            await feeder_task
            await player_task

        log.info("応答: %s", "".join(sentences))

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect(cls=voice_recv.VoiceRecvClient)
            log.info("VC 参加: %s (by %s)", channel.name, ctx.author)
            await ctx.send("合流したのだ。名前を呼ぶから覚悟するのだ。")
            asyncio.create_task(self._listen_loop(ctx))

    async def _listen_loop(self, ctx: commands.Context):
        if self.is_listening:
            return
        self.is_listening = True
        log.info("聴取開始 (by %s)", ctx.author)

        while self.is_listening:
            if not ctx.voice_client:
                log.warning("voice_client が切断されたため聴取を終了")
                break

            filename = "temp_voice.wav"
            sink = _TrackingSink(filename)

            try:
                ctx.voice_client.listen(sink)
                await asyncio.sleep(3)
                ctx.voice_client.stop_listening()

                user_name = "キミ"
                user_id_val = 0

                if sink.speakers:
                    member = next(iter(sink.speakers.values()))
                    user_name = member.display_name
                    user_id_val = member.id

                if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                    loop = asyncio.get_running_loop()
                    user_text = await loop.run_in_executor(
                        None, transcribe, filename
                    )

                    if user_text:
                        log.info("発話: %s: %s", user_name, user_text)
                        asyncio.create_task(
                            save_log(user_id_val, user_name, user_text)
                        )
                        await self._stream_ai_and_speak(ctx, user_text, user_name)

            except Exception:
                log.exception("聴取ループ内エラー")
            finally:
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
            await asyncio.sleep(0.1)

    @commands.command(name="start")
    async def start(self, ctx: commands.Context):
        if self.is_listening:
            return
        await ctx.send("聞き取りを開始するのだ！")
        await self._listen_loop(ctx)

    @commands.command(name="stop")
    async def stop(self, ctx: commands.Context):
        self.is_listening = False
        log.info("聴取停止 (by %s)", ctx.author)
        await ctx.send("休憩するのだ。")

    @commands.command(name="leave")
    async def leave(self, ctx: commands.Context):
        if ctx.voice_client:
            log.info("VC 退出 (by %s)", ctx.author)
            await ctx.voice_client.disconnect()
            await ctx.send("バイバイなのだ。")


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
