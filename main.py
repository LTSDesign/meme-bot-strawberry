import discord
from discord.ext import commands
import random
import os
import io
import textwrap
import asyncio
import datetime
import sqlite3
from PIL import Image, ImageDraw, ImageFont

TOKEN = '1234567890abcdefghijklmnopqrstuvwxyz'
PREFIX = '!'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# SQLite database setup
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

def init_database():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_configs (
            server_id INTEGER,
            corpus_name TEXT,
            read_channel_id INTEGER,
            PRIMARY KEY (server_id, corpus_name)
        )
    ''')
    conn.commit()

all_text_per_corpus = {}

@bot.event
async def on_disconnect():
    print("Bot disconnected. Reconnecting...")
    await bot.connect(reconnect=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    init_database()

@bot.event
async def on_message(message):
    await bot.process_commands(message)

@bot.command(name='memehelp')
async def help_command(ctx):
    embed = discord.Embed(
        title='Bot Commands',
        description='List of available commands:',
        color=discord.Color.blue()
    )
    embed.add_field(name='!meme', value='Generate a meme', inline=False)
    embed.add_field(name='!memehelp', value='Show this help message', inline=False)
    embed.add_field(name='!setcorpus', value='Set channels for corpus, use !setcorpus [CHANNEL ID]', inline=False)
    await ctx.send(embed=embed)


def save_channel_config(server_id, corpus_name, read_channel_ids):
    values = [(server_id, corpus_name.lower(), channel_id) for channel_id in read_channel_ids]
    cursor.executemany("""
        INSERT OR REPLACE INTO server_configs (server_id, corpus_name, read_channel_id)
        VALUES (?, ?, ?)
    """, values)
    conn.commit()


@bot.command(name='setcorpus')
@commands.has_permissions(administrator=True)
async def set_channels(ctx, corpus_name: str, *read_channel_ids: int):
    if corpus_name.lower() in ["corpus1", "corpus2", "corpus3"]:
        # Save the provided channel IDs to the server's configuration
        save_channel_config(ctx.guild.id, corpus_name.lower(), read_channel_ids)
        await ctx.send(f"Channels set successfully for {corpus_name}. Read Channel IDs: {', '.join(map(str, read_channel_ids))}")
    else:
        await ctx.send("Invalid corpus name. Available corpuses: corpus1, corpus2, ...")



def load_channel_config(server_id, corpus_name):
    cursor.execute("""
        SELECT read_channel_id
        FROM server_configs
        WHERE server_id = ? AND corpus_name = ?
    """, (server_id, corpus_name))
    result = cursor.fetchall()

    if result:
        return [entry[0] for entry in result]

    return None




async def make_meme(ctx, corpus_name):
    try:
        # Load the channel configuration for the given corpus
        channel_config = load_channel_config(ctx.guild.id, corpus_name.lower())

        if channel_config:
            read_channel_ids = load_channel_config(ctx.guild.id, corpus_name.lower())

            all_text = all_text_per_corpus.get(corpus_name, [])

            for read_channel_id in read_channel_ids:
                # Get all messages in the read channel
                read_channel = bot.get_channel(int(read_channel_id))
                messages = [message async for message in read_channel.history(limit=None)]

                # Process each message
                for message in messages:
                    if message.content.strip():  # Ignore messages that are empty or contain only whitespace
                        all_text.append(message.content)

            # Get all attachments in the server
            attachments = [attachment for msg in messages for attachment in msg.attachments]

            # Choose a random attachment from the server's uploaded files
            if attachments:
                random_attachment = random.choice(attachments)

                # Save the chosen attachment to a file
                attachment_path = await save_attachment(random_attachment, 'meme')

                # Process all_text to create a meme
                meme_text = process_all_text(all_text)

                # Check if there's meaningful text
                if meme_text.strip():
                    # Create a meme using the random text and image
                    meme_image = create_meme(meme_text, attachment_path)

                    # Send the meme image back to the command channel
                    await ctx.send(file=discord.File(meme_image, 'meme.png'))

                    # Delete the user's command message
                    await ctx.message.delete()

                else:
                    await ctx.send("No meaningful text found in the read channels.")
            else:
                await ctx.send("No attachments found in the read channels.")
        else:
            await ctx.send(f"No channel configuration found for {corpus_name}. Use !setchannels to set it up.")

    except Exception as e:
        print(f"Error: {e}")



@bot.command(name='meme')
async def meme_command(ctx, corpus_name: str):
    await make_meme(ctx, corpus_name)


def process_all_text(all_text):
    # Join all messages into a single string
    combined_text = " ".join(msg.strip() for msg in all_text if msg.strip())

    # Split the combined text into words
    words = combined_text.split()

    if len(words) > 5:
        # If the number of words is more than 5, randomly select a substring of 1 to 5 words
        start_index = random.randint(0, len(words) - 5)
        selected_words = words[start_index:start_index + random.randint(1, 5)]
        meme_text = " ".join(selected_words)
    else:
        # If the number of words is 5 or fewer, join them randomly
        selected_words = random.sample(words, k=min(5, len(words)))
        meme_text = " ".join(selected_words)

    return meme_text


async def save_attachment(attachment, command_name):
    if not os.path.exists('attachments'):
        os.makedirs('attachments')

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{command_name}_{timestamp}_{attachment.filename}"

    attachment_path = os.path.join('attachments', filename)
    with open(attachment_path, 'wb') as f:
        await attachment.save(f)

    return attachment_path

def create_meme(text_content, image_path, margin_percent=20):
    meme_image = Image.open(image_path)
    draw = ImageDraw.Draw(meme_image)
    font_size = int(meme_image.height * 0.07)
    font = ImageFont.truetype("lemon.ttf", font_size)
    text_color = "white"
    outline_color = "black"
    max_line_length = 15
    wrapped_text = "\n".join(textwrap.wrap(text_content, width=max_line_length))
    meme_text = f"{wrapped_text}"
    text_width, text_height = draw.textbbox((0, 0), meme_text, font=font)[2:4]
    margin = max((meme_image.width - text_width) * margin_percent // 100, 20)
    text_position = ((meme_image.width - text_width) // 2, meme_image.height - text_height - margin)

    outline_width = 1
    for x in range(-outline_width, outline_width + 1):
        for y in range(-outline_width, outline_width + 1):
            draw.text((text_position[0] + x, text_position[1] + y), meme_text, font=font, fill=outline_color)
    draw.text(text_position, meme_text, font=font, fill=text_color)

    image_bytes = io.BytesIO()
    meme_image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return image_bytes

bot.run(TOKEN)
