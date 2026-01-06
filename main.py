import discord
from discord.ext import commands
from discord import ui, Interaction
import edge_tts
from dotenv import load_dotenv
from langdetect import detect
import asyncio, os, re

# ================= ENV =================
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not found")

# ================= CONFIG =================
MAX_LEN = 180
allowed_text_channel_id = None

audio_queue = asyncio.Queue()
is_playing = False

# ================= VOICE PROFILE =================
voice_profile = {
    "voice": "female",   # female | male
    "rate": "0%",        # ความเร็ว
    "pitch": "+0Hz"      # pitch
}

VOICE_BASE = {
    "female": "th-TH-PremwadeeNeural",
    "male": "th-TH-NiwatNeural"
}

# ================= BOT =================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= THAI DIGITS =================
THAI_DIGITS = {
    "0": "ศูนย์","1": "หนึ่ง","2": "สอง","3": "สาม","4": "สี่",
    "5": "ห้า","6": "หก","7": "เจ็ด","8": "แปด","9": "เก้า"
}

# ================= UTILS =================
def clean_text(text: str):
    text = text.strip()
    if text.startswith("!"):
        return None

    if text.isdigit():
        return " ".join(THAI_DIGITS.get(c, c) for c in text[:MAX_LEN])

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
    if lang in ["th", "en"]:
        return lang
    return "th"


async def tts(text):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE_BASE[voice_profile["voice"]],
        rate=voice_profile["rate"],
        pitch=voice_profile["pitch"]
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


# ================= EMBED =================
def panel_embed():
    embed = discord.Embed(
        title="🎛️ แผงควบคุมเสียงบอท",
        description="ปรับเสียงได้ทันทีแบบไม่ต้องพิมพ์คำสั่ง",
        color=0x9B59B6
    )

    embed.add_field(
        name="🎤 เสียง",
        value="หญิง 🟣" if voice_profile["voice"] == "female" else "ชาย 🔵",
        inline=True
    )
    embed.add_field(
        name="🐢 ความเร็ว",
        value=voice_profile["rate"],
        inline=True
    )
    embed.add_field(
        name="🎵 Pitch",
        value=voice_profile["pitch"],
        inline=True
    )

    embed.set_footer(text="Panel นี้ถูกปักหมุดไว้ | รีสตาร์ทบอทไม่หาย")
    return embed


# ================= CONTROL PANEL =================
class ControlPanel(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def refresh(self, i: Interaction):
        await i.message.edit(embed=panel_embed(), view=self)

    # ----- VOICE -----
    @ui.button(label="หญิง", emoji="🟣", row=0, custom_id="voice_female")
    async def female(self, i: Interaction, _):
        voice_profile["voice"] = "female"
        await i.response.defer()
        await self.refresh(i)

    @ui.button(label="ชาย", emoji="🔵", row=0, custom_id="voice_male")
    async def male(self, i: Interaction, _):
        voice_profile["voice"] = "male"
        await i.response.defer()
        await self.refresh(i)

    # ----- RATE -----
    @ui.button(label="ปกติ", emoji="▶️", row=1, custom_id="rate_normal")
    async def rate_normal(self, i: Interaction, _):
        voice_profile["rate"] = "0%"
        await i.response.defer()
        await self.refresh(i)

    @ui.button(label="ช้า", emoji="🐢", row=1, custom_id="rate_slow")
    async def rate_slow(self, i: Interaction, _):
        voice_profile["rate"] = "-25%"
        await i.response.defer()
        await self.refresh(i)

    # ----- PITCH -----
    @ui.button(label="ทุ้ม", emoji="🎶", row=2, custom_id="pitch_low")
    async def pitch_low(self, i: Interaction, _):
        voice_profile["pitch"] = "-4Hz"
        await i.response.defer()
        await self.refresh(i)

    @ui.button(label="แหลม", emoji="🎵", row=2, custom_id="pitch_high")
    async def pitch_high(self, i: Interaction, _):
        voice_profile["pitch"] = "+6Hz"
        await i.response.defer()
        await self.refresh(i)

    # ----- VOICE CHANNEL -----
    @ui.button(label="Join", emoji="🔊", row=3, custom_id="join")
    async def join(self, i: Interaction, _):
        if i.user.voice:
            await i.user.voice.channel.connect()
            await i.response.send_message("🔊 เข้าห้องเสียงแล้ว", ephemeral=True)
        else:
            await i.response.send_message("❌ คุณยังไม่อยู่ในห้องเสียง", ephemeral=True)

    @ui.button(label="Leave", emoji="🚪", style=discord.ButtonStyle.danger, row=3, custom_id="leave")
    async def leave(self, i: Interaction, _):
        if i.guild.voice_client:
            await i.guild.voice_client.disconnect()
        await i.response.send_message("🚪 ออกจากห้องเสียงแล้ว", ephemeral=True)


# ================= COMMANDS =================
@bot.command()
async def setchat(ctx):
    global allowed_text_channel_id
    allowed_text_channel_id = ctx.channel.id
    await ctx.send("✅ ตั้งห้องอ่านเสียงแล้ว")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def panel(ctx):
    msg = await ctx.send(embed=panel_embed(), view=ControlPanel())
    try:
        await msg.pin()
        await ctx.send("📌 ปักหมุดแผงควบคุมแล้ว", delete_after=5)
    except discord.Forbidden:
        await ctx.send("❌ บอทไม่มีสิทธิ์ปักหมุด", delete_after=5)


# ================= EVENTS =================
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
    print("✅ Bot ready | Panel persistent | Edge TTS active")


bot.run(TOKEN)
