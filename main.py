from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is online!"

def run():
    app.run(host='0.0.0.0', port=5000)

threading.Thread(target=run).start()
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

@bot.command(name='payment')
async def payment_info(ctx):
    """Shows payment methods"""
    message = """## You can pay with the following payment methods.
### <:emojigg_LTC:1378403932585590876> LTC<:ArrowRightAlt:1364294003129847838>  Lb6eLbdsX3YteKhkEMiZfm4qnsMGJ8o57y
### <:Paypal:1364302241913114775> Paypal F&F<:ArrowRightAlt:1364294003129847838>  hidrihdro@outlook.com"""
    
    await ctx.send(message)

@bot.command(name='message')
async def send_dm(ctx, user_id: str, *, message):
    """Send a DM to a user by ID"""
    try:
        # Get user by ID to avoid needing member intents
        user = await bot.fetch_user(int(user_id))
        
        # Send DM to the user
        await user.send(f"Message from {ctx.author.display_name}: {message}")
        
    except ValueError:
        await ctx.send("âŒ Please provide a valid user ID!")
    except discord.NotFound:
        await ctx.send("âŒ User not found!")
    except discord.Forbidden:
        await ctx.send(f"âŒ Cannot send DM to {user.display_name}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"âŒ Error sending message: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command.name == 'message':
            await ctx.send("âŒ Usage: `?message <user_id> <message>`")
    elif isinstance(error, commands.BadArgument):
        if ctx.command.name == 'message':
            await ctx.send("âŒ Please provide a valid user ID!")
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
            print(f"Privileged intents error: {e}")
            print("Please enable the required intents in Discord Developer Portal:")
            print("1. Go to https://discord.com/developers/applications/")
            print("2. Select your bot")
            print("3. Go to Bot section")
            print("4. Enable 'Message Content Intent'")
        except Exception as e:
            print(f"Other error: {e}")
    else:
        print("Please set your DISCORD_BOT_TOKEN in the Secrets tab!")
