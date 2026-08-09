import os
import discord
from discord.ext import commands
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==========================================
# 1. إعداد السيرفر الوهمي (Render Web Server)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online and running!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# ==========================================
# 2. إعدادات البوت والصلاحيات (Intents)
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

WELCOME_CHANNEL_ID = 1533462690595606583
GOODBYE_CHANNEL_ID = 1533462691933585530
IMAGE_URL = "https://i.imgur.com/Jccjg91.png"

@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول بنجاح باسم: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="🔴⚪ CR Belouizdad"))

# ==========================================
# 3. نظام الترحيب والتوديع التلقائي
# ==========================================
@bot.event
async def on_member_join(member):
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            description=f"مرحبا بك في بيتك {member.mention}",
            color=discord.Color.red()
        )
        embed.set_image(url=IMAGE_URL)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            description=f"اخرج قود {member.mention}",
            color=discord.Color.red()
        )
        embed.set_image(url=IMAGE_URL)
        await channel.send(embed=embed)

# ==========================================
# 4. نظام التيكت (التذاكر) التفاعلي
# ==========================================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 إغلاق التيكت", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚠️ سيتم حذف القناة خلال 5 ثوانٍ...", ephemeral=True)
        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=5))
        try:
            await interaction.channel.delete()
        except:
            pass

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 فتح تيكت", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        category = interaction.channel.category
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 تيكت جديدة",
            description=f"مرحباً بك {user.mention}\nيرجى كتابة مشكلتك أو استفسارك هنا وسنتولى الرد عليك قريباً.",
            color=discord.Color.red()
        )
        
        await ticket_channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ تم فتح التيكت بنجاح: {ticket_channel.mention}", ephemeral=True)

@bot.command(name="setup_ticket")
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="🔴⚪ دعم نادي شباب بلوزداد",
        description="إذا كنت تحتاج إلى مساعدة أو استفسار، اضغط على الزر أدناه لفتح تيكت خاصة.",
        color=discord.Color.red()
    )
    embed.set_image(url=IMAGE_URL)
    await ctx.send(embed=embed, view=TicketSetupView())

# ==========================================
# 5. نظام التدريبات والحضور التفاعلي
# ==========================================
class AttendanceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.attending = []
        self.absent = []

    @discord.ui.button(label="سأحضر 🟩", style=discord.ButtonStyle.green)
    async def attend(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if user not in self.attending:
            self.attending.append(user)
            if user in self.absent:
                self.absent.remove(user)
            await interaction.response.send_message("✅ تم تسجيل حضورك بنجاح!", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ أنت مسجل مسبقاً في قائمة الحاضرين.", ephemeral=True)

    @discord.ui.button(label="أعتذر 🟥", style=discord.ButtonStyle.red)
    async def absent_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if user not in self.absent:
            self.absent.append(user)
            if user in self.attending:
                self.attending.remove(user)
            await interaction.response.send_message("❌ تم تسجيل اعتذارك.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ أنت مسجل مسبقاً في قائمة الغياب.", ephemeral=True)

@bot.command(name="training")
@commands.has_permissions(manage_messages=True)
async def training(ctx, *, time_info="قريباً"):
    embed = discord.Embed(
        title="🔔 موعد تدريب جديد للفريق",
        description=f"التفاصيل/التوقيت: **{time_info}**\nالرجاء تأكيد الحضور عبر الأزرار أدناه:",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=AttendanceView())

# ==========================================
# 6. الأوامر الإدارية والعقوبات
# ==========================================
@bot.command(name="card")
@commands.has_permissions(moderate_members=True)
async def card(ctx, member: discord.Member, card_type: str, *, reason="بدون سبب"):
    if card_type.lower() in ["اصفر", "yellow"]:
        embed = discord.Embed(title="🟨 إنذار (كارت أصفر)", description=f"للاعب {member.mention}", color=discord.Color.gold())
        embed.add_field(name="السبب", value=reason)
        await ctx.send(embed=embed)
    elif card_type.lower() in ["احمر", "red"]:
        embed = discord.Embed(title="🟥 طرد (كارت أحمر)", description=f"تم طرد اللاعب {member.mention}", color=discord.Color.red())
        embed.add_field(name="السبب", value=reason)
        await ctx.send(embed=embed)
        try:
            await member.timeout(timedelta(minutes=30), reason=reason)
        except:
            pass
    else:
        await ctx.send("❌ يرجى تحديد نوع الكارت بشكل صحيح: (اصفر / احمر)")

@bot.command(name="sign")
@commands.has_permissions(administrator=True)
async def sign(ctx, member: discord.Member, price: str, *, position: str):
    embed = discord.Embed(title="✍️ عقد رسمي جديد", description="إعلان عن صفقة جديدة للفريق 🤝", color=discord.Color.red())
    embed.add_field(name="👤 اللاعب", value=member.mention, inline=True)
    embed.add_field(name="📍 المركز", value=position, inline=True)
    embed.add_field(name="💰 القيمة / الراتب", value=price, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="مباراة")
async def match_info(ctx, *, info="قريباً"):
    embed = discord.Embed(title="⚽ موعد المباراة القادمة", description=info, color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="بدون سبب"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 تم حظر اللاعب {member.mention}. السبب: {reason}")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="بدون سبب"):
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"⏳ تم إسكات اللاعب {member.mention} لمدة {minutes} دقيقة.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف **{len(deleted) - 1}** رسالة.")
    await msg.delete(delay=3)

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 تم إغلاق القناة بنجاح.")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 تم فتح القناة بنجاح.")

# ==========================================
# 7. تشغيل البوت
# ==========================================
bot.run(TOKEN)
