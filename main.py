import discord
from discord.ext import commands
from gtts import gTTS
from langdetect import detect
from dotenv import load_dotenv
import asyncio, os, re, subprocess
from discord import ui, Interaction

# ===== ENV =====
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found")

# ===== CONFIG =====
MAX_LEN = 180
allowed_text_channel_id = None
auto_read = True

voice_mode = "female"  # female | chipmunk
audio_queue = asyncio.Queue()
is_playing = False

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== THAI DIGITS =====
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
    "9": "เก้า"
}

# ===== UTILS =====
def clean_text(text):
    text = text.strip()

    if text.startswith("!"):
        return None

    if text.isdigit():
        text = text[:MAX_LEN]
        return " ".join(THAI_DIGITS.get(ch, ch) for ch in text)

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
    gTTS(text=text, lang=detect_lang(text)).save("base.mp3")

    if voice_mode == "chipmunk":
        subprocess.run([
            "ffmpeg", "-y", "-i", "base.mp3",
            "-filter:a", "asetrate=44100*0.95,atempo=0.85",
            "voice.mp3"
        ])
    else:
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

# ===== CONTROL PANEL UI =====

def voice_label():
    return "🟣 เสียงสิริ" if voice_mode == "female" else "🐿 เสียงน้อน"

class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def update_panel(self, interaction: Interaction):
        await interaction.message.edit(
            content=f"🎛️ **ปุ่มควบคุมน้องหริ**\n🎤 เสียงปัจจุบัน: **{voice_label()}**",
            view=self
        )

    @ui.button(label="เสียงสิริ", style=discord.ButtonStyle.secondary, emoji="🟣")
    async def female(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "female"
        await interaction.response.defer()
        await self.update_panel(interaction)

    @ui.button(label="เสียงน้อน", style=discord.ButtonStyle.success, emoji="🐿")
    async def chip(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "chipmunk"
        await interaction.response.defer()
        await self.update_panel(interaction)

    @ui.button(label="Join", style=discord.ButtonStyle.success, emoji="🔊", row=1)
    async def join(self, interaction: Interaction, button: ui.Button):
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            await interaction.response.send_message(
                "🔊 เข้าห้องเสียงแล้ว", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ คุณยังไม่อยู่ในห้องเสียง", ephemeral=True
            )

    @ui.button(label="Leave", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def leave(self, interaction: Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(
            "🚪 ออกจากห้องเสียงแล้ว", ephemeral=True
        )

# ===== COMMANDS =====
@bot.command()
async def setchat(ctx):
    global allowed_text_channel_id
    allowed_text_channel_id = ctx.channel.id
    await ctx.send("✅ ตั้งห้องอ่านเสียงแล้ว")

@bot.command()
async def panel(ctx):
    await ctx.send(
        f"🎛️ **ปุ่มควบคุมน้องหริ**\n🎤 เสียงปัจจุบัน: **{voice_label()}**",
        view=ControlPanel()
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
async def on_ready():
    bot.add_view(ControlPanel())
    print("✅ Bot ready + Control Panel persistent")

bot.run(TOKEN)
