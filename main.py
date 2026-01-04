import discord
from discord.ext import commands
from gtts import gTTS
from langdetect import detect
from dotenv import load_dotenv
import asyncio, os, re, subprocess

# ===== ENV =====
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found")

# ===== CONFIG =====
MAX_LEN = 180
allowed_text_channel_id = None
auto_read = True

voice_mode = "female"  # female | male
audio_queue = asyncio.Queue()
is_playing = False

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

THAI_DIGITS = {
    "0": "ศูนย์",
    "1": "หนึ่ง",
    "2": "สอง",
    "3": "สาม",
    "4": "สี่",
    "5": "ห้า",
    "6": "หก",
    "7": "เจ็ด",
    "8": "แปด",
    "9": "เก้า",
    "10": "สิบ"
}

# ===== UTILS =====
def clean_text(text):
    text = text.strip()

    # ไม่อ่านคำสั่ง
    if text.startswith("!"):
        return None

    # กรณีเป็นตัวเลขล้วน
    if text.isdigit():
        # จำกัดความยาว
        text = text[:MAX_LEN]
        return " ".join(THAI_DIGITS.get(ch, ch) for ch in text)

    # กรณีเป็นข้อความทั่วไป
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


def tts(text):
    # สร้างเสียงพื้นฐาน
    gTTS(text=text, lang=detect_lang(text)).save("base.mp3")

    # ปรับเสียงด้วย ffmpeg
    if voice_mode == "male":
        # pitch ต่ำ = เสียงผู้ชาย
        subprocess.run([
            "ffmpeg", "-y", "-i", "base.mp3",
            "-filter:a", "asetrate=44100*0.88,atempo=1.0",
            "voice.mp3"
        ])
    else:
        # เสียงผู้หญิง (ปกติ)
        subprocess.run([
            "ffmpeg", "-y", "-i", "base.mp3",
            "voice.mp3"
        ])

    os.remove("base.mp3")


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
    await ctx.send("✅ ตั้งห้องอ่านเสียงแล้ว")


@bot.command()
async def male(ctx):
    global voice_mode
    voice_mode = "male"
    await ctx.send("🔵 เปลี่ยนเป็นเสียงผู้ชาย (ค้างค่า)")


@bot.command()
async def female(ctx):
    global voice_mode
    voice_mode = "female"
    await ctx.send("🟣 เปลี่ยนเป็นเสียงผู้หญิง (ค้างค่า)")

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
