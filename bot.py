import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import datetime

# تحميل المتغيرات من ملف .env (للتشغيل المحلي)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# التأكد من وجود التوكن
if not TOKEN:
    raise ValueError("يجب وضع التوكن في متغير DISCORD_TOKEN")

# إعداد الصلاحيات (Intents)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ----------------------------------------
# 1. حدث تشغيل البوت
# ----------------------------------------
@bot.event
async def on_ready():
    print(f'✅ تم تسجيل الدخول باسم {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم تحميل {len(synced)} أمر (Slash Command)")
    except Exception as e:
        print(f"⚠️ خطأ في تحميل الأوامر: {e}")

# ----------------------------------------
# 2. نظام التذاكر (الأزرار والنوافذ)
# ----------------------------------------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 فتح تذكرة جديدة", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # البحث عن فئة التذاكر (سنأخذها من متغيرات البيئة)
        category_id = int(os.getenv('TICKET_CATEGORY_ID', 0))
        support_role_id = int(os.getenv('SUPPORT_ROLE_ID', 0))
        
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        if not category:
            await interaction.response.send_message("❌ لم يتم إعداد فئة التذاكر بشكل صحيح.", ephemeral=True)
            return

        # صلاحيات القناة
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.get_role(support_role_id): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # إنشاء القناة
        ticket_number = len([ch for ch in category.channels]) + 1
        channel_name = f"تذكرة-{interaction.user.name}-{ticket_number}"
        channel = await interaction.guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

        # إرسال رسالة الترحيب في التذكرة مع أزرار التحكم
        embed = discord.Embed(
            title="🎟️ تذكرتك قد فُتحت",
            description=f"مرحباً {interaction.user.mention}!\nفريق الدعم سيتواصل معك قريباً.",
            color=discord.Color.green()
        )
        embed.add_field(name="📌 مهم", value="استخدم الأزرار بالأسفل للتحكم بالتذكرة.", inline=False)

        control_view = TicketControlView(channel_id=channel.id)
        await channel.send(embed=embed, view=control_view)
        
        # رد للمستخدم
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {channel.mention}", ephemeral=True)


# ----------------------------------------
# 3. أزرار التحكم داخل التذكرة (إغلاق - حذف - نسخ)
# ----------------------------------------
class TicketControlView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="🔒 إغلاق التذكرة", style=discord.ButtonStyle.secondary, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("⚠️ القناة غير موجودة.", ephemeral=True)
            return

        # جمع المحادثة (Transcript) وإرسالها
        messages = []
        async for msg in channel.history(limit=200, oldest_first=True):
            messages.append(f"{msg.author.name} | {msg.created_at.strftime('%H:%M')}: {msg.content}")
        
        transcript = "\n".join(messages) if messages else "لا توجد رسائل."
        
        # إنشاء ملف نصي
        file = discord.File(
            fp=bytes(transcript, 'utf-8'),
            filename=f"transcript-{channel.name}.txt"
        )

        # إرسال الملف لقناة الـ Logs (إذا وجدت)
        log_channel_id = int(os.getenv('LOG_CHANNEL_ID', 0))
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"📄 نسخة محادثة تذكرة {channel.name}", file=file)

        # تغيير الصلاحيات بحيث لا يرى الأعضاء القناة (إغلاق)
        await channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await channel.send("🔒 تم إغلاق هذه التذكرة بواسطة فريق الدعم.")
        await interaction.response.send_message("✅ تم إغلاق التذكرة.", ephemeral=True)

    @discord.ui.button(label="🗑️ حذف التذكرة", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.delete()
        await interaction.response.send_message("🗑️ تم حذف التذكرة.", ephemeral=True)

    @discord.ui.button(label="📋 نسخ المحادثة", style=discord.ButtonStyle.blurple, custom_id="transcript_ticket")
    async def transcript_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("⚠️ القناة غير موجودة.", ephemeral=True)
            return

        messages = []
        async for msg in channel.history(limit=200, oldest_first=True):
            messages.append(f"{msg.author.name} | {msg.created_at.strftime('%H:%M')}: {msg.content}")
        
        transcript = "\n".join(messages) if messages else "لا توجد رسائل."
        file = discord.File(
            fp=bytes(transcript, 'utf-8'),
            filename=f"transcript-{channel.name}.txt"
        )
        await interaction.response.send_message("📋 ها هي نسخة المحادثة:", file=file, ephemeral=True)


# ----------------------------------------
# 4. أوامر البوت (Slash Commands)
# ----------------------------------------
@bot.tree.command(name="ticket_panel", description="إنشاء لوحة التذاكر (للمشرفين فقط)")
@app_commands.default_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 نظام التذاكر",
        description="اضغط على الزر بالأسفل لفتح تذكرة جديدة وسيتواصل معك فريق الدعم.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())


@bot.tree.command(name="clear", description="مسح عدد معين من الرسائل")
@app_commands.describe(amount="عدد الرسائل للمسح (1-100)")
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("⚠️ الرجاء إدخال رقم بين 1 و 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 تم مسح {len(deleted)} رسالة.", ephemeral=True)


@bot.tree.command(name="lock", description="قفل القناة الحالية (منع الكتابة للأعضاء)")
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f"🔒 تم قفل القناة {interaction.channel.mention}.")


@bot.tree.command(name="unlock", description="فتح القناة الحالية (السماح بالكتابة للأعضاء)")
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f"🔓 تم فتح القناة {interaction.channel.mention}.")


# ----------------------------------------
# 5. تشغيل البوت
# ----------------------------------------
if __name__ == "__main__":
    bot.run(TOKEN)
