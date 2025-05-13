import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import os
import asyncio
from dotenv import load_dotenv
import subprocess
import sys
import shlex

from akari_agent import agent_executor, memory, SearchAnnounceHandler, refiner

# Constants
OUTPUT_WAV = "output.wav"
CHECK_INTERVAL = 0.2

# Environment Setup
load_dotenv()
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

# Globals
latest_mtime = 0
transcribe_proc = None

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.loop.create_task(monitor_wav_changes())


@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send(f"🔊 あかりが `{ctx.author.voice.channel.name}` にログインしたよ！")
    else:
        await ctx.send("VCに入ってからコマンドを実行してね。")


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@bot.command()
async def play(ctx, filename: str = OUTPUT_WAV):
    if ctx.voice_client:
        source = FFmpegPCMAudio(filename)
        ctx.voice_client.play(source)
    else:
        await ctx.send("VCに入ってないよ。まず `!join` してね。")


@bot.command()
async def say(ctx, *, args: str):
    if not ctx.voice_client:
        await ctx.send("まず `!join` でVCに入ってね。")
        return

    try:
        parsed = shlex.split(args)
        speed = 1.0
        text_parts = []

        if "--" in parsed:
            opt_part, text_parts = parsed[:parsed.index("--")], parsed[parsed.index("--") + 1:]
        else:
            opt_part = parsed

        i = 0
        while i < len(opt_part):
            if opt_part[i] in ("-s", "--speed") and i + 1 < len(opt_part):
                try:
                    speed = float(opt_part[i + 1])
                    i += 2
                except ValueError:
                    await ctx.send("⚠️ 話速は数値で指定してね！")
                    return
            else:
                i += 1

        if not text_parts:
            await ctx.send("⚠️ 読み上げるテキストがないよ！")
            return

        subprocess.run([
            sys.executable, "seikasay2.py", "-s", str(speed), "--", *text_parts
        ], check=True)

        vc = ctx.voice_client
        if not vc.is_playing():
            vc.play(FFmpegPCMAudio(OUTPUT_WAV))
        else:
            await ctx.send("⚠️ 現在再生中です。")
    except Exception as e:
        await ctx.send(f"❌ エラーが発生しました：{e}")


@bot.command()
async def chat(ctx, *, message: str):
    try:
        callback = SearchAnnounceHandler(ctx)

        history_text = "\n".join([
            f"マスター: {m.content}" if m.type == "human" else f"あかり: {m.content}"
            for m in memory.chat_memory.messages
        ])
        full_input = f"{history_text}\nマスター: {message}"
        result = await agent_executor.ainvoke(
            {"input": full_input},
            config={"callbacks": [callback]}
        )

        tool_output = result["output"]
        intermediate = result.get("intermediate_steps", [])
        used_tool = bool(intermediate)

        if used_tool:
            refined = await refiner.ainvoke({
                "input": (
                    f"マスター: {message}"
                    f"ツールの結果: {tool_output}\n"
                    "あかりらしい文章でこの結果をマスターに伝えてね"
                ),
                "chat_history": memory.chat_memory.messages
            })
            reply = refined.content

        else:
            refined = await refiner.ainvoke({
                "input": (
                    f"マスター: {message}\n"
                ),
                "chat_history": memory.chat_memory.messages
            })
            reply = refined.content
            
        memory.chat_memory.add_user_message(message)
        if used_tool:
            memory.chat_memory.add_ai_message(f"[toolの結果]: {tool_output}")
        memory.chat_memory.add_ai_message(reply)

        await ctx.send(f"💬 あかり: {reply}")

        subprocess.run([sys.executable, "seikasay2.py", "--", reply], check=True)
        vc = ctx.voice_client
        if vc and not vc.is_playing():
            vc.play(FFmpegPCMAudio(OUTPUT_WAV))
    except Exception as e:
        await ctx.send(f"❌ エージェントエラー：{e}")


@bot.command()
async def forget(ctx):
    memory.clear()
    await ctx.send("🧠 あかりちゃんの記憶をリセットしたよ。")


@bot.command()
async def listen(ctx):
    global transcribe_proc
    if transcribe_proc is not None:
        await ctx.send("⚠️ すでに通話中です。")
        return

    await ctx.send("🎤 通話モードを開始します… お待ちください")
    transcribe_proc = await asyncio.create_subprocess_exec(
        sys.executable, "live_transcribe.py", stdout=asyncio.subprocess.PIPE
    )
    bot.loop.create_task(read_transcriptions(transcribe_proc.stdout, ctx.channel))


async def read_transcriptions(stdout, channel):
    while True:
        line = await stdout.readline()
        if not line:
            break
        try:
            text = line.decode("utf-8", errors="ignore").strip()
            if "ERROR" in text.upper():
                await channel.send(f"⚠️ 音声認識でエラーが発生しました: `{text}`")
                continue
            if text == "READY":
                await channel.send("✅ モデルの初期化が完了しました！話しかけてみてね。")
                continue
            if text:
                ctx = await bot.get_context(await channel.fetch_message(channel.last_message_id))
                await ctx.send(f"マスター: {text}")
                await chat(ctx, message=text)
        except Exception as e:
            print(f"[read_transcriptions エラー] {e}")


async def monitor_wav_changes():
    global latest_mtime
    print("[監視] output.wav の変更を監視中")
    while True:
        try:
            if os.path.exists(OUTPUT_WAV):
                mtime = os.path.getmtime(OUTPUT_WAV)
                if mtime != latest_mtime:
                    latest_mtime = mtime
                    print("[検知] WAVファイルが更新されました")
                    vc = discord.utils.get(bot.voice_clients)
                    if vc and not vc.is_playing():
                        print("[再生] output.wav の更新を検知、再生します")
                        vc.play(FFmpegPCMAudio(OUTPUT_WAV))
        except Exception as e:
            print(f"[エラー] {e}")
        await asyncio.sleep(CHECK_INTERVAL)


@bot.command()
async def stop(ctx):
    global transcribe_proc
    if transcribe_proc:
        transcribe_proc.terminate()
        transcribe_proc = None
        await ctx.send("🛑 通話モードを停止しました。")
    else:
        await ctx.send("⚠️ 現在は通話しておりません。")


bot.run(DISCORD_TOKEN)
