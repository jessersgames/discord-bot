from flask import Flask
import threading
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot is online!"

def run():
    # Use PORT environment variable for Render, fallback to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Start Flask in a separate thread
threading.Thread(target=run).start()

import discord
from discord.ext import commands
import json

# Bot setup - Need message content intent for commands to work
intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True  # Required for commands

bot = commands.Bot(command_prefix='?', intents=intents)

# Configuration storage
config = {}

def load_config():
    global config
    try:
        with open('bot_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

def save_config():
    with open('bot_config.json', 'w') as f:
        json.dump(config, f, indent=2)

def get_guild_config(guild_id):
    return config.get(str(guild_id), {})

def set_guild_config(guild_id, key, value):
    if str(guild_id) not in config:
        config[str(guild_id)] = {}
    config[str(guild_id)][key] = value
    save_config()

def check_permissions(interaction):
    guild_id = str(interaction.guild.id)
    command_name = interaction.command.name
    guild_config = get_guild_config(guild_id)

    # Only apply restrictions to new slash commands (vouch, configure)
    restricted_commands = ["vouch", "configure"]
    if command_name not in restricted_commands:
        return True  # Old commands have no restrictions

    # For vouch command, only check role restrictions (not channel)
    if command_name == "vouch":
        # Check if command has been configured at all
        if command_name not in guild_config:
            return False  # No configuration = no access
        
        cmd_config = guild_config[command_name]
        
        # Check role restriction if configured
        if 'allowed_roles' in cmd_config and cmd_config['allowed_roles']:
            user_role_ids = [role.id for role in interaction.user.roles]
            if not any(role_id in cmd_config['allowed_roles'] for role_id in user_role_ids):
                return False
    
    # For configure command (admins only)
    elif command_name == "configure":
        return True  # Already checked in the command itself

    return True

@bot.event
async def on_ready():
    load_config()
    print(f'{bot.user} has logged in!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Old prefix commands (no restrictions)
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
        await ctx.send(f"✅ Message sent to {user.display_name}!")

    except ValueError:
        await ctx.send("❌ Please provide a valid user ID!")
    except discord.NotFound:
        await ctx.send("❌ User not found!")
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot send DM to {user.display_name}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ Error sending message: {str(e)}")

# Modal for vouch submission
class VouchModal(discord.ui.Modal, title='Submit Your Vouch'):
    def __init__(self):
        super().__init__()

    purchase = discord.ui.TextInput(
        label='What did you purchase?',
        placeholder='Tell us what service/product you bought...',
        required=True,
        max_length=200
    )

    rating = discord.ui.TextInput(
        label='Rate the service (1-5 stars)',
        placeholder='Choose between 1 and 5 stars...',
        required=True,
        max_length=1
    )

    reason = discord.ui.TextInput(
        label='Reason for your rating',
        style=discord.TextStyle.paragraph,
        placeholder='Tell us why you gave this rating...',
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rating_value = int(self.rating.value)
            if rating_value < 1 or rating_value > 5:
                await interaction.response.send_message("❌ Rating must be between 1 and 5 stars!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for rating!", ephemeral=True)
            return

        embed = discord.Embed(
            title="⭐ New Vouch Submitted",
            color=0x8b5cf6,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Rating", value=f"{'⭐' * rating_value} ({rating_value}/5)", inline=True)
        embed.add_field(name="Purchase", value=self.purchase.value, inline=False)
        embed.add_field(name="Reason", value=self.reason.value, inline=False)
        embed.set_footer(text=f"Submitted by {interaction.user.display_name}")

        await interaction.response.send_message("✅ Your vouch has been submitted!", ephemeral=True)
        
        # Get the configured vouch channel and post there
        guild_id = str(interaction.guild.id)
        guild_config = get_guild_config(guild_id)
        
        if 'vouch' in guild_config and 'allowed_channels' in guild_config['vouch'] and guild_config['vouch']['allowed_channels']:
            vouch_channel_id = guild_config['vouch']['allowed_channels'][0]  # Use first configured channel
            vouch_channel = interaction.guild.get_channel(vouch_channel_id)
            
            if vouch_channel:
                await vouch_channel.send(embed=embed)
            else:
                # Fallback: send in current channel if configured channel not found
                await interaction.followup.send(embed=embed)
        else:
            # Fallback: send in current channel if no channel configured
            await interaction.followup.send(embed=embed)

# View with button for vouch
class VouchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Submit A Vouch', style=discord.ButtonStyle.success, emoji='⭐')
    async def submit_vouch(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VouchModal())

@bot.tree.command(name="vouch", description="Submit a vouch with star rating")
async def vouch_command(interaction: discord.Interaction):
    if not check_permissions(interaction):
        await interaction.response.send_message("❌ You don't have the required role to use this command! Ask an admin to configure your role access.", ephemeral=True)
        return

    embed = discord.Embed(
        title="⭐ Submit Your Vouch",
        description="Rate our service from 1 to 5 stars and tell us your reason. We highly value your feedback!",
        color=0x8b5cf6
    )
    embed.add_field(
        name="📝 Request Information",
        value=f"Request created at: {discord.utils.format_dt(discord.utils.utcnow(), 'f')} • All rights reserved to VouchHub",
        inline=False
    )

    view = VouchView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="configure", description="Configure command permissions (Admin only)")
async def configure_command(interaction: discord.Interaction, command: str, channel: discord.TextChannel = None, role: discord.Role = None):
    # Check if user has administrator permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return

    # Only new commands can be configured
    valid_commands = ["vouch"]
    if command not in valid_commands:
        await interaction.response.send_message(f"❌ Invalid command! Available commands to configure: {', '.join(valid_commands)}", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)

    # Initialize command config if it doesn't exist
    if guild_id not in config:
        config[guild_id] = {}
    if command not in config[guild_id]:
        config[guild_id][command] = {}

    embed = discord.Embed(title=f"⚙️ Configuration for /{command}", color=0x5865f2)

    # Configure channel restriction
    if channel:
        if 'allowed_channels' not in config[guild_id][command]:
            config[guild_id][command]['allowed_channels'] = []
        if channel.id not in config[guild_id][command]['allowed_channels']:
            config[guild_id][command]['allowed_channels'].append(channel.id)
            embed.add_field(name="✅ Channel Added", value=f"Command can now be used in {channel.mention}", inline=False)
        else:
            embed.add_field(name="ℹ️ Channel Already Configured", value=f"Command was already allowed in {channel.mention}", inline=False)

    # Configure role restriction
    if role:
        if 'allowed_roles' not in config[guild_id][command]:
            config[guild_id][command]['allowed_roles'] = []
        if role.id not in config[guild_id][command]['allowed_roles']:
            config[guild_id][command]['allowed_roles'].append(role.id)
            embed.add_field(name="✅ Role Added", value=f"Command can now be used by {role.mention}", inline=False)
        else:
            embed.add_field(name="ℹ️ Role Already Configured", value=f"Command was already allowed for {role.mention}", inline=False)

    # Show current configuration
    cmd_config = config[guild_id][command]

    if 'allowed_channels' in cmd_config and cmd_config['allowed_channels']:
        channels = [f"<#{ch_id}>" for ch_id in cmd_config['allowed_channels']]
        embed.add_field(name="📋 Allowed Channels", value="\n".join(channels), inline=True)
    else:
        embed.add_field(name="📋 Allowed Channels", value="All channels", inline=True)

    if 'allowed_roles' in cmd_config and cmd_config['allowed_roles']:
        roles = [f"<@&{role_id}>" for role_id in cmd_config['allowed_roles']]
        embed.add_field(name="👥 Allowed Roles", value="\n".join(roles), inline=True)
    else:
        embed.add_field(name="👥 Allowed Roles", value="All roles", inline=True)

    save_config()
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reset_config", description="Reset command configuration (Admin only)")
async def reset_config_command(interaction: discord.Interaction, command: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permissions to use this command!", ephemeral=True)
        return

    # Only new commands can be reset
    valid_commands = ["vouch"]
    if command not in valid_commands:
        await interaction.response.send_message(f"❌ Invalid command! Available commands to reset: {', '.join(valid_commands)}", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id in config and command in config[guild_id]:
        del config[guild_id][command]
        save_config()
        await interaction.response.send_message(f"✅ Configuration for /{command} has been reset!")
    else:
        await interaction.response.send_message(f"ℹ️ No configuration found for /{command}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command.name == 'message':
            await ctx.send("❌ Usage: `?message <user_id> <message>`")
    elif isinstance(error, commands.BadArgument):
        if ctx.command.name == 'message':
            await ctx.send("❌ Please provide a valid user ID!")
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
