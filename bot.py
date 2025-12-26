# bot.py
import discord
from discord.ext import tasks
import requests
from flask import Flask
from threading import Thread
import os

# ===== CONFIGURATION =====
CHANNEL_ID = 1450212923296452678  # <-- REPLACE WITH YOUR DISCORD CHANNEL ID
CHECK_INTERVAL = 60  # minutes between checks
STEAM_DISCOUNT_THRESHOLD = 50  # notify only if game has this % off or more
# =========================

# Get token from environment variable
TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Keep track of posted deals to avoid duplicates
posted_epic = set()
posted_steam = set()

# ===== EPIC GAMES CHECK =====
def check_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    try:
        data = requests.get(url).json()
    except:
        return []

    deals = []
    for game in data["data"]["Catalog"]["searchStore"]["elements"]:
        promos = game.get("promotions")
        if not promos:
            continue
        for promo in promos.get("promotionalOffers", []):
            for offer in promo["promotionalOffers"]:
                if offer["discountSetting"]["discountPercentage"] == 0:
                    slug = game["productSlug"]
                    if slug not in posted_epic:
                        posted_epic.add(slug)
                        deals.append({
                            "title": game["title"],
                            "url": f"https://store.epicgames.com/p/{slug}"
                        })
    return deals

# ===== STEAM DISCOUNTS CHECK =====
def check_steam_discounts():
    # Example: using Steam featured specials page
    url = "https://store.steampowered.com/api/featuredcategories/"
    try:
        data = requests.get(url).json()
    except:
        return []

    deals = []
    for game in data.get("specials", {}).get("items", []):
        discount = game.get("discount_percent", 0)
        appid = game.get("id")
        if discount >= STEAM_DISCOUNT_THRESHOLD and appid not in posted_steam:
            posted_steam.add(appid)
            deals.append({
                "title": game.get("name"),
                "discount": discount,
                "url": f"https://store.steampowered.com/app/{appid}"
            })
    return deals

# ===== DISCORD EVENTS =====
@client.event
async def on_ready():
    print(f"{client.user} is online!")
    deal_checker.start()

# ===== BACKGROUND TASK =====
@tasks.loop(minutes=CHECK_INTERVAL)
async def deal_checker():
    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print("Channel not found. Check CHANNEL_ID.")
        return

    # Epic games
    epic_deals = check_epic_free_games()
    for deal in epic_deals:
        await channel.send(
            f"🎮 **FREE ON EPIC GAMES!**\n"
            f"**{deal['title']}**\n"
            f"{deal['url']}"
        )

    # Steam deals
    steam_deals = check_steam_discounts()
    for deal in steam_deals:
        await channel.send(
            f"🔥 **STEAM DISCOUNT!**\n"
            f"**{deal['title']}** - {deal['discount']}% OFF\n"
            f"{deal['url']}"
        )

# ===== FLASK SERVER FOR UPTIMEROBOT =====
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

t = Thread(target=run)
t.start()

# ===== RUN THE BOT =====
client.run(TOKEN)

