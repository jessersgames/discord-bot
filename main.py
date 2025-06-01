# --- Flask keep-alive ---
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is online!"

def run():
    app.run(host='0.0.0.0', port=5000)

threading.Thread(target=run).start()
# -------------------------

import discord
from discord.ext import commands
import os

# Bot setup - Need message content intent for commands to work
intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True  # Required for commands

bot = commands.Bot(command_prefix='?', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    print(f'Bot is in {len(bot.guilds)} guilds')

@bot.command(name='payement')
async def payment_info(ctx):
    """Shows payment methods"""
    message = (
        "You can pay with the following payment methods:\n"
        "- LTC → Lb6eLbdsX3YteKhkEMiZfm4qnsMGJ8o57y\n"
        "- Paypal Friends & Family → hidrihdro@outlook.com"
    )
    await ctx.send(message)

@bot.command(name='message')
async def send_dm(ctx, user_id: str, *, message):
    """Send a DM to a user by ID"""
    try:
        user = await bot.fetch_user(int(user_id))
        await user.send(f"Message from {ctx.author.display_name}: {message}")
    except ValueError:
        await ctx.send("Please provide a valid user ID.")
    except discord.NotFound:
        await ctx.send("User not found.")
    except discord.Forbidden:
        await ctx.send("Cannot send DM to that user. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"Error sending message: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command.name == 'message':
            await ctx.send("Usage: ?message <user_id> <message>")
    elif isinstance(error, commands.BadArgument):
        if ctx.command.name == 'message':
            await ctx.send("Please provide a valid user ID.")
    else:
        print(f"Error: {error}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        print("Starting bot with minimal intents...")
        print(f"Intents: {intents}")
        try:
            bot.run(token)
        except discord.PrivilegedIntentsRequired as e:
            print("Privileged intents error. Please enable the required intents in Discord Developer Portal.")
        except Exception as e:
            print(f"Other error: {e}")
    else:
        print("Please set your DISCORD_BOT_TOKEN in the Environment tab.")
