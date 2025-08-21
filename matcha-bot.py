import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
import difflib
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

#needs to be replaced with actual product pages
#like each product
urls = {
    "Yugen Matcha #0": "https://www.yugen-kyoto.com/en-us/products/matcha0-yugen-original-blend",
    "Yugen Matcha #1": "https://www.yugen-kyoto.com/en-us/products/matcha1-yugen-original-blend",
    "Yugen Matcha #2": "https://www.yugen-kyoto.com/en-us/products/matcha2-yugen-original-blend",
    "Ippodo Matcha Sayaka 40g": "https://ippodotea.com/collections/matcha/products/sayaka-no-mukashi",
    "Ippodo Matcha Ikuyo 30g": "https://ippodotea.com/collections/matcha/products/ikuyo"
}

last_status = {name: None for name in urls.keys()}

async def check_stock(name, url, send_to_channel=True, message=None, force=False):
    try:
        #headers to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64, x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/114.0.0.0 Safari/537.36"

        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        #right click on website, "inspect", find out how "sold out" is displayed
        sold_out = soup.find(string=lambda t: "Sold Out" in t or "Out of Stock" in t or "currently unavailable" in t)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #determines the new status of a product
        new_status = "in stock" if not sold_out else "sold out"

        global last_status
        result = None

        if force or last_status[name] != new_status:
            if new_status == "in stock":
                result = f"[{now}] {name} is in stock! {url}"
            else:
                result = f"[{now}] {name} is now sold out."
            last_status[name] = new_status #update status
        
        if result:
            if send_to_channel:
                channel = client.get_channel(CHANNEL_ID)
                await channel.send(result)
            elif message:
                await message.channel.send(result)

    except Exception as e:
        error_msg = f"Error checking {name}: {e}"
        if message:
            await message.channel.send(error_msg)
        else:
            print(error_msg)

async def stock_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    await channel.send("Stock checker bot is online!")
    while not client.is_closed():
        for name, url in urls.items():
            await check_stock(name, url)
        await asyncio.sleep(60 * 5) #check every 5 min

def find_product(query):
    #fuzzy matching
    query_lower = query.lower()
    partial_matches = [name for name in urls.keys() if query_lower in name.lower()]
    if partial_matches:
        return partial_matches


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    asyncio.create_task(stock_loop()) #start background loop

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.lower().startswith("!check"):
        query = message.content[len("!check"):].strip()
        matches = find_product(query)

        if matches:
            await check_stock(matches[0], urls[matches[0]], send_to_channel=False, message=message, force=True)

            if len(matches) > 1:
                await message.channel.send(
                    "Other possible matches:\n" + "\n".join(matches[1:])
                )
        else:
            await message.channel.send(
                "I couldn't find any product matching that. Try one of these:\n"
            )


client.run(TOKEN)
