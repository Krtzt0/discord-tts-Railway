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

# ===== VOICE PROFILES =====
VOICE_COLORS = {
    "female": 0x9B59B6,  # ม่วง
    "drunk":  0xE67E22,  # ส้ม
    "chip":   0x2ECC71,  # เขียว
    "male":   0x3498DB,  # ฟ้า
}

voice_mode = "female"
VOICE_PROFILES = {
    "female": ("th-TH-PremwadeeNeural", "+0%", "+0Hz"),
    "drunk":  ("th-TH-PremwadeeNeural", "-25%", "-2Hz"),
    "chip":   ("th-TH-PremwadeeNeural", "+10%", "+6Hz"),
    "male":   ("th-TH-NiwatNeural", "-5%", "-6Hz"),
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
    return "th" if lang not in ["en", "zh"] else lang

async def tts(text):
    voice, rate, pitch = VOICE_PROFILES[voice_mode]
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
            await asyncio.sleep(0.3)
        os.remove("voice.mp3")

    is_playing = False

# ===== EMBED =====
def panel_embed(status="พร้อมใช้งาน"):
    embed = discord.Embed(
        title="🎧 SIRI VOICE CONTROL",
        description=(
            "ระบบอ่านแชทด้วยเสียงอัตโนมัติ\n"
            "ควบคุมโหมดเสียงและห้องพูดผ่านปุ่มด้านล่าง 👇"
        ),
        color=VOICE_COLORS[voice_mode]
    )

    embed.add_field(
        name="🗣 โหมดเสียงปัจจุบัน",
        value=f"> **{voice_label()}**",
        inline=False
    )

    embed.add_field(
        name="🎚 ตัวเลือกเสียง",
        value=(
            "🟣 **สิริ** — เสียงปกติ\n"
            "🥴 **เมา** — พูดอ้อแอ้ ช้าลง\n"
            "🐿 **น้อน** — เสียงแหลม\n"
            "🔵 **ชาย** — เสียงผู้ชาย"
        ),
        inline=False
    )

    embed.add_field(
        name="📡 สถานะระบบ",
        value=f"```{status}```",
        inline=False
    )

    embed.set_footer(
        text="Siri TTS • Edge-TTS • Discord Bot",
        icon_url="https://cdn-icons-png.flaticon.com/512/4712/4712109.png"
    )

    return embed

# ===== CONTROL PANEL =====
class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh(self, interaction: Interaction, status: str):
        await interaction.message.edit(
            embed=panel_embed(status),
            view=self
        )

    @ui.button(label="สิริ", emoji="🟣", style=discord.ButtonStyle.secondary, custom_id="voice_female")
    async def female(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "female"
        await interaction.response.defer()
        await self.refresh(interaction, "เปลี่ยนเสียงเป็น สิริ (ปกติ) 🎤")

    @ui.button(label="น้อน", emoji="🐿", style=discord.ButtonStyle.success, custom_id="voice_chip")
    async def chip(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "chip"
        await interaction.response.defer()
        await self.refresh(interaction, "เปลี่ยนเสียงเป็น น้อน 🐿")

    @ui.button(label="เมา", emoji="🥴", style=discord.ButtonStyle.primary, custom_id="voice_drunk")
    async def drunk(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "drunk"
        await interaction.response.defer()
        await self.refresh(interaction, "เปลี่ยนเสียงเป็น สิริเมา 🥴")

    @ui.button(label="ชาย", emoji="🔵", style=discord.ButtonStyle.secondary, custom_id="voice_male")
    async def male(self, interaction: Interaction, button: ui.Button):
        global voice_mode
        voice_mode = "male"
        await interaction.response.defer()
        await self.refresh(interaction, "เปลี่ยนเสียงเป็น ผู้ชาย 🔵")

    @ui.button(label="Join", emoji="🔊", style=discord.ButtonStyle.success, row=1, custom_id="vc_join")
    async def join(self, interaction: Interaction, button: ui.Button):
        if interaction.user.voice:
            await interaction.user.voice.channel.connect()
            await interaction.response.send_message(
                "🔊 เข้าห้องเสียงแล้ว",
                ephemeral=True
            )
            await self.refresh(interaction, "เชื่อมต่อห้องเสียงแล้ว 🔊")
        else:
            await interaction.response.send_message(
                "❌ คุณยังไม่อยู่ในห้องเสียง",
                ephemeral=True
            )

    @ui.button(label="Leave", emoji="🚪", style=discord.ButtonStyle.danger, row=1, custom_id="vc_leave")
    async def leave(self, interaction: Interaction, button: ui.Button):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(
            "🚪 ออกจากห้องเสียงแล้ว",
            ephemeral=True
        )
        await self.refresh(interaction, "ออกจากห้องเสียงแล้ว 🚪")

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
    print("✅ Bot ready + Persistent Control Panel")

bot.run(TOKEN)
