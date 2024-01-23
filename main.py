#welcome to spaghetti junction
import random
import os
import io
import textwrap
import asyncio
import datetime
from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands

TOKEN = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
PREFIX = '!'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

all_text_per_channel = {}  # Dictionary to store all_text for each channel
READ_CHANNEL_ID_1 = 1196514534039486465
READ_CHANNEL_ID_2 = 1198231774761844837
READ_CHANNEL_ID_3 = 1198283062996377600

# Specify the ID of the channel where you want users to send commands
COMMAND_CHANNEL_ID_1 = 1196514584241119232  # Replace with the ID of command channel 1
COMMAND_CHANNEL_ID_2 = 1198290101457920060  # Replace with the ID of command channel 2

COMMAND_CHANNEL_IDS = [COMMAND_CHANNEL_ID_1, COMMAND_CHANNEL_ID_2]

@bot.event
async def on_disconnect():
    print("Bot disconnected. Reconnecting...")
    await asyncio.sleep(5)  # Add a delay to avoid rapid reconnection attempts
    await bot.start(TOKEN)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.event
async def on_message(message):
    # Check if the message is from the designated read channels
    if message.channel.id in [READ_CHANNEL_ID_1, READ_CHANNEL_ID_2, READ_CHANNEL_ID_3]:
        # Process messages from the read channels as needed
        print(f"Message in read channel: {message.content}")

        # Check if the channel ID is already in the dictionary
        if message.channel.id not in all_text_per_channel:
            all_text_per_channel[message.channel.id] = []

        all_text_per_channel[message.channel.id].append(message.content)

    # Check if the message is from any of the command channels
    if message.channel.id in COMMAND_CHANNEL_IDS:
        # Allow commands to be processed in the specified command channels
        await bot.process_commands(message)

def process_all_text(all_text):
    # Join all messages into a single string
    combined_text = " ".join(msg.strip() for msg in all_text if msg.strip())

    # Split the combined text into words
    words = combined_text.split()

    # Randomly select between 1 to 5 words
    num_selected_words = random.randint(1, min(5, len(words)))
    selected_words = random.sample(words, k=num_selected_words)

    # Combine the selected words back into a string
    meme_text = " ".join(selected_words)

    return meme_text

async def make_meme(ctx, channel_id):
    try:
        all_text = all_text_per_channel.get(channel_id, [])

        # Get all messages in the read channel
        read_channel = bot.get_channel(channel_id)
        messages = [message async for message in read_channel.history(limit=None)]

        # Print messages in the read channel
        print("Messages in the read channel:")
        for message in messages:
            print(f"Message: {message.content}, Attachments: {message.attachments}")

        # Process each message
        for message in messages:
            if message.content.strip():  # Ignore messages that are empty or contain only whitespace
                all_text.append(message.content)

        # Get all attachments in the server
        attachments = [attachment for msg in messages for attachment in msg.attachments]

        # Choose a random attachment from the server's uploaded files
        if attachments:
            random_attachment = random.choice(attachments)

            # Print the chosen attachment
            print(f"Chosen Attachment: {random_attachment}")

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
                await ctx.send("No meaningful text found in the read channel.")
        else:
            await ctx.send("No attachments found in the read channel.")
    except Exception as e:
        print(f"Error: {e}")

def command_channel(channel_id):
    async def predicate(ctx):
        if ctx.message.channel.id != channel_id:
            # Send a message saying "Wrong channel" and return False
            await ctx.send("Wrong channel for this command.")
            return False
        return True
    return commands.check(predicate)

@bot.command(name='mma')
@command_channel(COMMAND_CHANNEL_ID_1)
async def make_meme_channel1(ctx):
    await make_meme(ctx, READ_CHANNEL_ID_1)

@bot.command(name='mm')
@command_channel(COMMAND_CHANNEL_ID_1)
async def make_meme_channel2(ctx):
    await make_meme(ctx, READ_CHANNEL_ID_2)

@bot.command(name='meme')
@command_channel(COMMAND_CHANNEL_ID_2)
async def make_meme_channel3(ctx):
    await make_meme(ctx, READ_CHANNEL_ID_3)

async def save_attachment(attachment, command_name):
    # Ensure the "attachments" folder exists
    if not os.path.exists('attachments'):
        os.makedirs('attachments')

    # Generate a unique filename based on the command and timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{command_name}_{timestamp}_{attachment.filename}"

    # Save the attachment to a file
    attachment_path = os.path.join('attachments', filename)
    with open(attachment_path, 'wb') as f:
        await attachment.save(f)

    return attachment_path

def create_meme(text_content, image_path, margin_percent=20):
    # Load the image
    meme_image = Image.open(image_path)

    # Create a drawing object
    draw = ImageDraw.Draw(meme_image)

    # Set font and size (adjust the font_size as needed)
    font_size = int(meme_image.height * 0.07)
    font = ImageFont.truetype("lemon.ttf", font_size)

    # Set text color and outline color
    text_color = "white"
    outline_color = "black"

    # Word wrap the text
    max_line_length = 15  # Adjust as needed
    wrapped_text = "\n".join(textwrap.wrap(text_content, width=max_line_length))

    # Customize how the text appears
    meme_text = f"{wrapped_text}"

    # Calculate text position to center the text vertically within the image
    text_width, text_height = draw.textbbox((0, 0), meme_text, font=font)[2:4]  

    # Calculate the margin dynamically based on text width
    margin = max((meme_image.width - text_width) * margin_percent // 100, 20)

    # Adjust text position to ensure it's not cut off
    text_position = ((meme_image.width - text_width) // 2, meme_image.height - text_height - margin)


    # Draw the text with a black outline on the image
    outline_width = 1
    for x in range(-outline_width, outline_width + 1):
        for y in range(-outline_width, outline_width + 1):
            draw.text((text_position[0] + x, text_position[1] + y), meme_text, font=font, fill=outline_color)
    draw.text(text_position, meme_text, font=font, fill=text_color)

    # Save the modified image to a BytesIO object
    image_bytes = io.BytesIO()
    meme_image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return image_bytes

bot.run(TOKEN)
