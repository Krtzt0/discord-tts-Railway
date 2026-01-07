import discord
from discord.ext import commands
from discord import ui, Interaction
import edge_tts
import asyncio, os, re
from dotenv import load_dotenv
from langdetect import detect

# ===== ENV =====
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found")

# ===== CONFIG =====
MAX_LEN = 180
allowed_text_channel_id = None
auto_read = True
audio_queue = asyncio.Queue()
is_playing = False

# ===== FUNNY DIGITS =====
THAI_DIGITS = {
    "0": "ศูนย์","1": "หนึ๋ง","2": "ส๋อง","3": "ส๋าม","4": "สี๋",
    "5": "ฮ้า","6": "ห๊ก","7": "เจ๊ด","8": "แป๊ด","9": "เกา"
}
MATH_SYMBOLS = {
    "+": "บวก", "-": "ลบ", "*": "คูณ", "/": "หาร"
}

# ===== VOICE STATE =====
voice_mode = "female"

VOICE_COLORS = {
    "female": 0x9B59B6,
    "drunk":  0xE67E22,
    "chip":   0x2ECC71,
    "male":   0x3498DB,
}

VOICE_PROFILES = {
    "female": {
        "th": ("th-TH-PremwadeeNeural", "+0%", "+20Hz"),
        "zh": ("zh-CN-XiaoxiaoNeural", "+0%", "+20Hz"),
        "en": ("en-US-JennyNeural", "+0%", "+20Hz"),
    },
    "drunk": {
        "th": ("th-TH-PremwadeeNeural", "-25%", "-2Hz"),
        "zh": ("zh-CN-XiaoxiaoNeural", "-25%", "-2Hz"),
        "en": ("en-US-JennyNeural", "-25%", "-2Hz"),
    },
    "chip": {
        "th": ("th-TH-PremwadeeNeural", "+25%", "+30Hz"),
        "zh": ("zh-CN-XiaoxiaoNeural", "+25%", "+30Hz"),
        "en": ("en-US-JennyNeural", "+25%", "+30Hz"),
    },
    "male": {
        "th": ("th-TH-NiwatNeural", "-5%", "-6Hz"),
        "zh": ("zh-CN-YunxiNeural", "-5%", "-6Hz"),
        "en": ("en-US-GuyNeural", "-5%", "-6Hz"),
    }
}

def voice_label():
    return {
        "female": "🟣 สิริ (ปกติ)",
        "drunk": "🥴 สิริเมา",
        "chip": "🐿 น้อน",
        "male": "🔵 เสียงชาย",
    }[voice_mode]

# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== UTILS =====
def read_numbers_funny(text):
    out = []
    for ch in text:
        if ch in THAI_DIGITS:
            out.append(THAI_DIGITS[ch])
        elif ch in MATH_SYMBOLS:
            out.append(MATH_SYMBOLS[ch])
        else:
            out.append(ch)
    return " ".join(out)

def clean_text(text):
    text = text.strip()
    if text.startswith("!"):
        return None

    if re.search(r"\d", text):
        return read_numbers_funny(text)[:MAX_LEN]

    if not re.search(r"[ก-๙a-zA-Z\u4e00-\u9fff]", text):
        return None

    return text[:MAX_LEN]

def detect_lang(text):
    try:
        lang = detect(text)
    except:
        return "th"

    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("en"):
        return "en"
    return "th"

# ===== TTS =====
async def tts(text):
    lang = detect_lang(text)
    voice, rate, pitch = VOICE_PROFILES[voice_mode][lang]

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch
    )
    await communicate.save("voice.mp3")

async def play_queue(vc):
    global is_playing
    if is_playing:
        return
    is_playing = True

    while not audio_queue.empty():
        text = await audio_queue.get()
        await tts(text)
        vc.play(discord.FFmpegPCMAudio("voice.mp3"))
        while vc.is_playing():
            await asyncio.sleep(0.25)
        os.remove("voice.mp3")

    is_playing = False

# ===== EMBED =====
def panel_embed(status="พร้อมใช้งาน"):
    embed = discord.Embed(
        title="🎧 SIRI VOICE CONTROL",
        description="ระบบอ่านแชทอัตโนมัติด้วยเสียง\nเลือกโหมดเสียงด้านล่าง 👇",
        color=VOICE_COLORS[voice_mode]
    )
    embed.add_field(
        name="🗣 โหมดเสียงปัจจุบัน",
        value=f"> **{voice_label()}**",
        inline=False
    )
    embed.add_field(
        name="📡 สถานะ",
        value=f"```{status}```",
        inline=False
    )
    embed.set_footer(text="Edge TTS • Discord Bot")
    return embed

# ===== CONTROL PANEL =====
class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh(self, interaction, status):
        await interaction.message.edit(
            embed=panel_embed(status),
            view=self
        )

    @ui.button(label="สิริ", emoji="🟣", style=discord.ButtonStyle.secondary, custom_id="v_female")
    async def female(self, i: Interaction, _):
        global voice_mode
        voice_mode = "female"
        await i.response.defer()
        await self.refresh(i, "เปลี่ยนเสียงเป็น สิริ")

    @ui.button(label="เมา", emoji="🥴", style=discord.ButtonStyle.primary, custom_id="v_drunk")
    async def drunk(self, i: Interaction, _):
        global voice_mode
        voice_mode = "drunk"
        await i.response.defer()
        await self.refresh(i, "เปลี่ยนเสียงเป็น สิริเมา")

    @ui.button(label="น้อน", emoji="🐿", style=discord.ButtonStyle.success, custom_id="v_chip")
    async def chip(self, i: Interaction, _):
        global voice_mode
        voice_mode = "chip"
        await i.response.defer()
        await self.refresh(i, "เปลี่ยนเสียงเป็น น้อน")

    @ui.button(label="ชาย", emoji="🔵", style=discord.ButtonStyle.secondary, custom_id="v_male")
    async def male(self, i: Interaction, _):
        global voice_mode
        voice_mode = "male"
        await i.response.defer()
        await self.refresh(i, "เปลี่ยนเสียงเป็น ผู้ชาย")

    @ui.button(label="Join", emoji="🔊", style=discord.ButtonStyle.success, row=1, custom_id="vc_join")
    async def join(self, i: Interaction, _):
        if i.user.voice:
            await i.user.voice.channel.connect()
            await i.response.send_message("🔊 เข้าห้องเสียงแล้ว", ephemeral=True)
        else:
            await i.response.send_message("❌ ยังไม่อยู่ในห้องเสียง", ephemeral=True)

    @ui.button(label="Leave", emoji="🚪", style=discord.ButtonStyle.danger, row=1, custom_id="vc_leave")
    async def leave(self, i: Interaction, _):
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
    msg = await ctx.send(embed=panel_embed(), view=ControlPanel())
    try:
        await msg.pin()
    except:
        pass

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
    print("✅ Bot ready")

bot.run(TOKEN)
