import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
import difflib
from dotenv import load_dotenv
import os
import threading
from server import app

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

async def send_embed(channel, title, description, color=discord.Color.green(), image_url=None):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Checked at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if image_url:
        embed.set_thumbnail(url=image_url)
    await channel.send(embed=embed)
           


def scrape_product_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    #sold out detection
    sold_out_phrases = [
        "sold out",
        "out of stock",
        "currently unavailable",
        "new restock scheduled"
    ]
    text = soup.get_text(" ", strip=True).lower()
    sold_out = any(phrase in text for phrase in sold_out_phrases)
    status = "in stock" if not sold_out else "sold out"

    #grabbing product image
    image_url = None
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        image_url = og_image["content"]
    else:
        img_tag = soup.find("img")
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
            if image_url.startswith("//"):
                image_url = "https:" + image_url
    return status, image_url


async def check_stock(name, url, send_to_channel=True, message=None, force=False):
    try:
        new_status, image_url = scrape_product_info(url)
        global last_status

        if force or last_status[name] != new_status:
            if new_status == "in stock":
                title = f" {name} is in stock!"
                description = f"@here purchase here: <{url}>"
                color = discord.Color.green()
            
            else:
                title = f" {name} is sold out."
                description = f"last checked: <{url}>"
                color = discord.Color.red()
 
            
            last_status[name] = new_status

            if send_to_channel or message:
                target_channel = message.channel if message else client.get_channel(CHANNEL_ID)
                await send_embed(target_channel, title, description, color, image_url)
        
        

    except Exception as e:
        error_msg = f"Error checking {name}: {e}"
        if message:
            await send_embed(message.channel, "Error", error_msg, discord.Color.orange())
        else:
            print(error_msg)

async def stock_loop():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)


    await send_embed(channel, "Matcha Bot is online!", "I will notify you when matcha is in stock :3\nType !nameofproduct to check it status!", color=discord.Color.blue())
    
    while not client.is_closed():
        for name, url in urls.items():
            await check_stock(name, url)
        await asyncio.sleep(60 * 5) #check every 5 min

def find_product(query):
    #fuzzy matching
    query_lower = query.lower()
    return [name for name in urls.keys() if query_lower in name.lower()]


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
                await send_embed(
                    message.channel,
                    "Other possible matches",
                    "\n".join(matches[1:]),
                    discord.Color.dark_blue()
                )
        else:
            await send_embed(
                message.channel,
                "No matches found",
                "try one of these:\n" + "\n".join(urls.keys()),
                discord.Color.orange()
            )

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

client.run(TOKEN)
