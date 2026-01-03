import discord
from discord.ext import commands
from gtts import gTTS
from langdetect import detect
from dotenv import load_dotenv
import asyncio
import os
import re
import shutil

# ===== LOAD ENV =====
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not DISCORD_BOT_TOKEN:
    raise RuntimeError("❌ DISCORD_BOT_TOKEN not found")

# ===== FFMPEG =====
FFMPEG_PATH = shutil.which("ffmpeg")
print("FFMPEG PATH:", FFMPEG_PATH)

if not FFMPEG_PATH:
    raise RuntimeError("❌ ffmpeg not found in system")

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

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ===== UTILS =====
def clean_text(text: str):
    text = text.strip()
    if text.startswith("!"):
        return None
    if not re.search(r"[ก-๙a-zA-Z\u4e00-\u9fff]", text):
        return None
    return text[:MAX_LEN]


def detect_tts_lang(text: str):
    try:
        lang = detect(text)
    except:
        return "th"

    if lang.startswith("zh"):
        return "zh-CN"
    elif lang == "en":
        return "en"
    elif lang == "th":
        return "th"
    return "th"


def generate_tts(text: str, filename="voice.mp3"):
    lang = detect_tts_lang(text)
    tts = gTTS(text=text, lang=lang, slow=slow_voice)
    tts.save(filename)


async def play_queue(vc: discord.VoiceClient):
    global is_playing

    if is_playing:
        return

    is_playing = True

    while not audio_queue.empty():
        text = await audio_queue.get()
        filename = "voice.mp3"

        generate_tts(text, filename)

        vc.play(
            discord.FFmpegPCMAudio(
                source=filename,
                executable=FFMPEG_PATH,
                options="-loglevel panic"
            )
        )

        while vc.is_playing():
            await asyncio.sleep(0.3)

        if os.path.exists(filename):
            os.remove(filename)

    is_playing = False

# ===== COMMANDS =====
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        await ctx.send("🔊 เข้าห้องเสียงแล้ว")


@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@bot.command()
async def setchat(ctx):
    global allowed_text_channel_id
    allowed_text_channel_id = ctx.channel.id
    await ctx.send("✅ ตั้งห้องอ่านเสียงแล้ว")


@bot.command()
async def autoon(ctx):
    global auto_read
    auto_read = True
    await ctx.send("🔊 เปิด auto read")


@bot.command()
async def autooff(ctx):
    global auto_read
    auto_read = False
    await ctx.send("🔇 ปิด auto read")


@bot.command()
async def slow(ctx):
    global slow_voice
    slow_voice = True
    await ctx.send("🐢 ใช้เสียงช้า")


@bot.command()
async def fast(ctx):
    global slow_voice
    slow_voice = False
    await ctx.send("⚡ ใช้เสียงปกติ")


@bot.command()
async def clearqueue(ctx):
    global audio_queue
    audio_queue = asyncio.Queue()
    await ctx.send("🧹 ล้างคิวเสียงแล้ว")


@bot.command()
async def help(ctx):
    await ctx.send(
        "**🆘 คำสั่งบอท TTS**\n\n"
        "**🎧 เสียง**\n"
        "`!join` เข้าห้องเสียง\n"
        "`!leave` ออกจากห้องเสียง\n"
        "`!slow` เสียงช้า\n"
        "`!fast` เสียงปกติ\n\n"
        "**🗨️ แชท**\n"
        "`!setchat` ตั้งห้องอ่านเสียง\n"
        "`!autoon` เปิดอ่าน\n"
        "`!autooff` ปิดอ่าน\n\n"
        "**📜 อื่น ๆ**\n"
        "`!clearqueue` ล้างคิว\n"
        "`!help` ดูคำสั่ง"
    )

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


@bot.event
async def on_voice_state_update(member, before, after):
    vc = member.guild.voice_client
    if vc and len(vc.channel.members) == 1:
        await vc.disconnect()


bot.run(DISCORD_BOT_TOKEN)
