import discord
from discord.ext import commands, tasks
import json, asyncio, random
from datetime import datetime, timedelta

TOKEN = "MTM4ODI0OTkzNzY2NTU4OTQ0OA.G9Ov_W.SJWRqIiyw9dt1oNJm21odhcndRf_lA6LA-sXaQ"
SHOP_CHANNEL_ID = 1388256880274702336
BALANCE_CHANNEL_ID = 1388256944833167522
CASINO_CHANNEL_ID = 1388265779333431406

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
user_data = {}
voice_times = {}
cooldowns = {}
events = {"active": False}

# ===== Загрузка/Сохранение =====
def load_data():
    global user_data
    try:
        with open("data.json", "r") as f:
            user_data = json.load(f)
    except:
        user_data = {}

def save_data():
    with open("data.json", "w") as f:
        json.dump(user_data, f, indent=4)

# ===== Инициализация пользователя =====
def ensure_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "coins": 0,
            "messages": 0,
            "voice_minutes": 0,
            "purchases": 0,
            "achievements": []
        }

# ===== Событие on_ready =====
@bot.event
async def on_ready():
    load_data()
    print(f"✅ Бот {bot.user.name} успешно запущен и подключён к Discord!")

# ===== Обработчик сообщений =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    uid = str(message.author.id)
    ensure_user(uid)
    user_data[uid]["messages"] += 1
    gain = 2 if events["active"] else 1
    user_data[uid]["coins"] += gain
    save_data()
    await bot.process_commands(message)

# ===== Отслеживание времени в войсе =====
@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    ensure_user(uid)
    if after.channel and not before.channel:
        voice_times[uid] = datetime.utcnow()
    elif before.channel and not after.channel and uid in voice_times:
        minutes = int((datetime.utcnow() - voice_times[uid]).total_seconds() / 60)
        gained = minutes * 3 * (2 if events["active"] else 1)
        user_data[uid]["coins"] += gained
        user_data[uid]["voice_minutes"] += minutes
        del voice_times[uid]
        save_data()

# ===== Команды =====
@bot.command()
async def wallet(ctx):
    if ctx.channel.id != BALANCE_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    coins = user_data[uid]["coins"]
    await ctx.send(f"💰 У тебя {coins} 🧩")

@bot.command()
async def daily(ctx):
    uid = str(ctx.author.id)
    now = datetime.utcnow()
    if uid in cooldowns and now - cooldowns[uid] < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - cooldowns[uid])
        minutes = int(remaining.total_seconds() // 60)
        return await ctx.send(f"⏳ Возвращайся через {minutes} минут.")
    ensure_user(uid)
    user_data[uid]["coins"] += 200
    cooldowns[uid] = now
    save_data()
    await ctx.send("🎁 Ты получил 200 🧩 за ежедневный бонус!")

@bot.command()
async def casino(ctx, amount: int):
    if ctx.channel.id != CASINO_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    if user_data[uid]["coins"] < amount:
        return await ctx.send("❌ Недостаточно пазлов.")
    if random.random() < 0.4:
        user_data[uid]["coins"] += amount
        msg = await ctx.send(f"🎉 Ты выиграл! Теперь у тебя {user_data[uid]['coins']} 🧩")
    else:
        user_data[uid]["coins"] -= amount
        msg = await ctx.send(f"💀 Ты проиграл... Теперь у тебя {user_data[uid]['coins']} 🧩")
    save_data()
    await asyncio.sleep(30)
    await msg.delete()

@bot.command()
async def coinflip(ctx, guess):
    if ctx.channel.id != CASINO_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    guess = guess.lower()
    if guess not in ["heads", "tails"]:
        return await ctx.send("❌ Используй: !coinflip heads или tails")
    result = random.choice(["heads", "tails"])
    if guess == result:
        user_data[uid]["coins"] += 100
        msg = await ctx.send(f"🪙 Выпало {result}. Ты выиграл 100 🧩!")
    else:
        user_data[uid]["coins"] -= 100
        msg = await ctx.send(f"🪙 Выпало {result}. Ты проиграл 100 🧩.")
    save_data()
    await asyncio.sleep(30)
    await msg.delete()

@bot.command()
async def fruit(ctx, amount: int):
    if ctx.channel.id != CASINO_CHANNEL_ID:
        return
    uid = str(ctx.author.id)
    ensure_user(uid)
    if user_data[uid]["coins"] < amount:
        return await ctx.send("❌ Недостаточно пазлов.")
    symbols = ["🍒", "🍋", "🍇", "🍓", "7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    display = " | ".join(result)
    if result[0] == result[1] == result[2]:
        if random.random() < 0.1:
            winnings = amount * 15
            user_data[uid]["coins"] += winnings
            msg = await ctx.send(f"🎰 {display} — Поздравляем! x15, ты выиграл {winnings} 🧩")
        else:
            user_data[uid]["coins"] -= amount
            msg = await ctx.send(f"🎰 {display} — Не повезло! Выпало 3 одинаковых, но шанс не сработал.")
    else:
        user_data[uid]["coins"] -= amount
        msg = await ctx.send(f"🎰 {display} — Не повезло!")
    save_data()
    await asyncio.sleep(30)
    await msg.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def deletecoin(ctx, amount: int):
    uid = str(ctx.author.id)
    ensure_user(uid)
    user_data[uid]["coins"] = max(0, user_data[uid]["coins"] - amount)
    save_data()
    await ctx.send(f"🗑️ У тебя удалено {amount} 🧩")

load_data()
bot.run(TOKEN)
