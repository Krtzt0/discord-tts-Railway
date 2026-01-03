import discord
from discord.ext import commands
from gtts import gTTS
from langdetect import detect
from dotenv import load_dotenv
import asyncio
import os
import re

# ===== ENV =====
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found")

# ===== CONFIG =====
MAX_LEN = 180
allowed_text_channel_id = None
auto_read = True
slow_voice = False

audio_queue = asyncio.Queue()
is_playing = False

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== UTILS =====
def clean_text(text):
    text = text.strip()
    if text.startswith("!"):
        return None
    if not re.search(r"[ก-๙a-zA-Z\u4e00-\u9fff]", text):
        return None
    return text[:MAX_LEN]


def detect_lang(text):
    try:
        lang = detect(text)
    except:
        return "th"
    if lang.startswith("zh"):
        return "zh-CN"
    if lang == "en":
        return "en"
    return "th"


def tts(text, filename="voice.mp3"):
    gTTS(text=text, lang=detect_lang(text), slow=slow_voice).save(filename)


async def play_queue(vc):
    global is_playing
    if is_playing:
        return
    is_playing = True

    while not audio_queue.empty():
        text = await audio_queue.get()
        tts(text)

        vc.play(discord.FFmpegPCMAudio("voice.mp3"))

        while vc.is_playing():
            await asyncio.sleep(0.3)

        os.remove("voice.mp3")

    is_playing = False

# ===== COMMANDS =====
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("🔊 Joined voice")


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@bot.command()
async def setchat(ctx):
    global allowed_text_channel_id
    allowed_text_channel_id = ctx.channel.id
    await ctx.send("✅ Chat set")


# ===== EVENTS =====
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    await bot.process_commands(msg)

    if not auto_read:
        return
    if msg.channel.id != allowed_text_channel_id:
        return

    vc = msg.guild.voice_client
    if not vc:
        return

    text = clean_text(msg.content)
    if not text:
        return

    await audio_queue.put(text)
    await play_queue(vc)


bot.run(TOKEN)
