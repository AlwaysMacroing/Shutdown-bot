# Shutdown-bot
Schedule a pc shutdown with a discord command. Made for unattending while macroing.
Everything is vibecoded in python with claude.



Shutdown Bot — Setup Guide
How it works
Multiple PCs can run the exact same file and connect to Discord with the same token simultaneously.
Each PC only executes commands that match its own prefix — all others are ignored.
You type:  !n shutdown 22.30
PC-N sees it → matches "n" → schedules shutdown
PC-V sees it → not "v"    → ignores it
No VPS, no HTTP server, no open ports needed.

1. Create the Discord Bot

Go to https://discord.com/developers/applications → New Application
Bot tab → Add Bot → click Reset Token and copy it
Enable Message Content Intent under Privileged Gateway Intents
OAuth2 → URL Generator → scope bot, permissions Send Messages + Read Message History → copy the URL and open it in your browser to invite the bot to your server


2. Configure shutdown_bot.py
Open the file and edit the config section at the top:
pythonDISCORD_TOKEN   = "paste-your-token-here"   # same on all PCs
MY_PREFIX       = "n"                        # unique per PC — e.g. "n", "v", "m"
ALLOWED_CHANNEL = None                       # set to a channel ID to restrict, or leave as None
BLACKLISTED_USERS: list[int] = [
    # 123456789012345678,                    # add user IDs to block here
]
The only line that differs between PCs is MY_PREFIX.
Finding IDs

Bot token — Discord Developer Portal → your app → Bot tab → Reset Token
Channel ID — Enable Developer Mode in Discord settings, then right-click a channel → Copy Channel ID
User ID — Enable Developer Mode, then right-click a username → Copy User ID


3. Install & Run (on each PC)
Install the required library:
pip install discord.py
Run the bot:
python shutdown_bot.py
The bot will show as online in your server once the script is running.

4. Autostart on Windows (optional)
Create a start_bot.bat file:
bat@echo off
start pythonw C:\path\to\shutdown_bot.py
Then press Win + R, type shell:startup, hit Enter, and paste the .bat file into that folder.
The bot will now start automatically every time you log in.

5. Commands
CommandWhat it does!n shutdown 22.30Schedule PC-N to shut down at 22:30!n cancelCancel PC-N's scheduled shutdown!n statusShow time remaining until PC-N shuts down!n helpShow the help message

Replace n with whatever prefix the PC is configured to use.

Time formats accepted: 22.30 · 22:30 · 2230 · 22 30

6. Notes

The bot token must be kept secret — anyone with it can control your bot
The bot does not persist shutdown schedules across restarts — if the script stops, the scheduled time is lost
If !n status shows a shutdown but there isn't one, run !n cancel to resync
