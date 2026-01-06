import discord
from discord.ext import commands
import edge_tts
from langdetect import detect
from dotenv import load_dotenv
import asyncio, os, re
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

voice_mode = "female"  # female | chipmunk | drunk
audio_queue = asyncio.Queue()
is_playing = False

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== THAI DIGITS =====
THAI_DIGITS = {
    "0": "ศูนย์","1": "หนึ่ง","2": "สอง","3": "สาม","4": "สี่",
    "5": "ห้า","6": "หก","7": "เจ็ด","8": "แปด","9": "เก้า"
}

# ===== UTILS =====
def clean_text(text):
    text = text.strip()
    if text.startswith("!"):
        return None
    if text.isdigit():
        return " ".join(THAI_DIGITS.get(ch, ch) for ch in text[:MAX_LEN])
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
    return lang if lang in ["th", "en"] else "th"

# ===== EDGE TTS =====
VOICE_MAP = {
    "female": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "0%",
        "pitch": "+0Hz"
    },
    "male": {
        "voice": "th-TH-NiwatNeural",
        "rate": "-10%",
        "pitch": "-2Hz"
    },
    "chipmunk": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "+20%",
        "pitch": "+6Hz"
    },
    "drunk": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "-25%",
        "pitch": "+0Hz"
    }
}


async def tts_edge(text):
    cfg = VOICE_MAP[voice_mode]
    communicate = edge_tts.Communicate(
        text=text,
        voice=cfg["voice"],
        rate=cfg["rate"],
        pitch=cfg["pitch"]
    )
    await communicate.save("voice.mp3")

async def play_queue(vc):
    global is_playing
    if is_playing:
        return
    is_playing = True

    while not audio_queue.empty():
        text = await audio_queue.get()
        await tts_edge(text)

        vc.play(discord.FFmpegPCMAudio("voice.mp3"))
        while vc.is_playing():
            await asyncio.sleep(0.3)

        os.remove("voice.mp3")

    is_playing = False

# ===== PANEL =====
def voice_label():
    return {
        "female": "🟣 เสียงสิริ",
        "male": "🔵 เสียงผู้ชาย",
        "chipmunk": "🐿 เสียงน้อน",
        "drunk": "🥴 เสียงเมา"
    }[voice_mode]


class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def update(self, interaction):
        await interaction.message.edit(
            content=f"🎛️ **ปุ่มควบคุมน้องหริ**\n🎤 เสียงปัจจุบัน: **{voice_label()}**",
            view=self
        )

    @ui.button(label="สิริ", emoji="🟣", style=discord.ButtonStyle.secondary, custom_id="female")
    async def female(self, i: Interaction, b: ui.Button):
        global voice_mode
        voice_mode = "female"
        await i.response.defer()
        await self.update(i)

@ui.button(label="ผู้ชาย", emoji="🔵", style=discord.ButtonStyle.primary, custom_id="male")
async def male(self, i: Interaction, b: ui.Button):
    global voice_mode
    voice_mode = "male"
    await i.response.defer()
    await self.update(i)


    @ui.button(label="น้อน", emoji="🐿", style=discord.ButtonStyle.success, custom_id="chip")
    async def chip(self, i: Interaction, b: ui.Button):
        global voice_mode
        voice_mode = "chipmunk"
        await i.response.defer()
        await self.update(i)

    @ui.button(label="เมา", emoji="🥴", style=discord.ButtonStyle.primary, custom_id="drunk")
    async def drunk(self, i: Interaction, b: ui.Button):
        global voice_mode
        voice_mode = "drunk"
        await i.response.defer()
        await self.update(i)
        

    @ui.button(label="Join", emoji="🔊", row=1, custom_id="join")
    async def join(self, i: Interaction, b: ui.Button):
        if i.user.voice:
            await i.user.voice.channel.connect()
        await i.response.send_message("🔊 เข้าห้องเสียงแล้ว", ephemeral=True)

    @ui.button(label="Leave", emoji="🚪", style=discord.ButtonStyle.danger, row=1, custom_id="leave")
    async def leave(self, i: Interaction, b: ui.Button):
        if i.guild.voice_client:
            await i.guild.voice_client.disconnect()
        await i.response.send_message("🚪 ออกจากห้องเสียงแล้ว", ephemeral=True)

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
    print("✅ Bot ready + Edge TTS + panel")

bot.run(TOKEN)
