import discord
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime
from dotenv import load_dotenv
import os
import threading
from server import app
from db import add_product, update_stock, get_products, get_product_by_name

load_dotenv()
TOKEN = os.environ['DISCORD_TOKEN']
CHANNEL_ID = int(os.environ['CHANNEL_ID'])

intents = discord.Intents.default()
intents.message_content = True 
client = discord.Client(intents=intents)

#store last known stock status
last_status = {}

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


async def check_stock(product, send_to_channel=True, message=None, force=False):
    try:
        product_id, name, url, in_stock, _ = product
        new_status, image_url = scrape_product_info(url)

        last = last_status.get(name)
        if force or last != new_status:
            #update database if status changed
            update_stock(product_id, new_status == "in stock")
            last_status[name] = new_status

            if new_status == "in stock":
                title = f"{name} is in stock!"
                description = f"@here purchase here: <{url}>"
                color = discord.Color.green()
            else:
                title = f"{name} is sold out."
                description = f"Last checked: <{url}>"
                color = discord.Color.red()
            
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
    
    #instructions for user
    instructions = ("**Hi! I'm Matcha Bot.**\n"
                    "Here are my commands:\n"
                    "~ `!add <name> <url>` -> add a new product to track.\n"
                    "~ `!check <name> -> check the stock status of a product.\n"
                    "~ `!list` -> show all tracked products.\n"
                    "\n I will also notify you when stock changes!")
    
    while not client.is_closed():
        products = get_products()
        for product in products:
            await check_stock(product)
        await asyncio.sleep(60 * 5) #check every five minutes

def find_product(query):
    #fuzzy matching
    query_lower = query.lower()
    products = get_products()
    return [p for p in products if query_lower in p[1].lower()]


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    asyncio.create_task(stock_loop()) #start background loop

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    content = message.content.strip()

    #add product command
    if content.lower().startswith("!add "):
        try:
            parts = content.split(" ", 2)
            if len(parts) < 3:
                await send_embed(message.channel, "Usage", "!add <Product Name> <URL>", discord.Color.orange())
                return
            
            name = parts[1].strip()
            url = parts[2].strip()

            status, image_url = scrape_product_info(url)

            add_product(name, url, status == "in stock")

            await send_embed(
                message.channel,
                "Product has been added.",
                f" **{name}** has been added.\nStatus: {status}\nURL: <{url}>",
                discord.Color.green(),
                image_url
            )
        except Exception as e:
            await send_embed(message.channel, "Error", f"Could not add product: {e}", discord.Color.red())
        return

    #check command
    if content.lower().startswith("!check"):
        query = content[len("!check"):].strip()
        matches = find_product(query)

        if matches:
            await check_stock(matches[0], send_to_channel=False, message=message, force=True)
            if len(matches) > 1:
                await send_embed(
                    message.channel,
                    "Other possible matches",
                    "\n".join(m[1] for m in matches[1:]),
                    discord.Color.dark_blue()
                )
        else:
            all_names = [p[1] for p in get_products()]
            await send_embed(
                message.channel,
                "No matches found",
                "Try one of these:\n" + "\n".join(all_names),
                discord.Color.orange()
            )
        return
    
    #list command
    if content.lower().startswith("!list"):
        products = get_products()
        if products:
            product_lines = [
                f"~ **{p[1]}** - {'In stock' if p[3] else 'Sold Out'}\n<{p[2]}>"
                for p in products
            ]
            await send_embed(
                message.channel,
                "Tracked Products",
                "\n".join(product_lines),
                discord.Color.purple()
            )
        else:
            await send_embed(
                message.channel,
                "Tracked Products",
                "No products are being tracked yet. Use `!add <name> <url>` to add a product.",
                discord.Color.orange()
            )
        return

@client.event
async def on_message_edit(before, after):
    pass


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()
client.run(TOKEN)
