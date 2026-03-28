"""
shutdown_bot.py — Able to run on multiple PCs with the same Discord bot token.

Multiple PCs can connect to Discord simultaneously using the same bot.
Each PC only executes commands that match its own prefix.

    PC-N: set MY_PREFIX = "n"  →  reacts to !n commands

Setup:
    pip install discord.py
    Fill in the config below, then run: python shutdown_bot.py
"""

# ═══════════════════════════════════════════════════════════════════════
#  CONFIG — edit this section, everything else is automatic
# ═══════════════════════════════════════════════════════════════════════

DISCORD_TOKEN   = "YOUR BOT TOKEN"  # Replace with your bot token
MY_PREFIX       = "n"                        # Select what prefix you want
ALLOWED_CHANNEL   = None                     # int channel ID to restrict, or None

# Users blocked from using any commands. Add their Discord user IDs here.
# Right-click a username in Discord (with Developer Mode on) → Copy User ID.
BLACKLISTED_USERS: list[int] = [
    123456789012345678,   # If you want to blacklist a user from using the bot
]

# ═══════════════════════════════════════════════════════════════════════

import re
import subprocess
import time
import threading
from datetime import datetime, timedelta

import discord
from discord.ext import commands

# ── local shutdown state ───────────────────────────────────────────────────────
_scheduled_epoch: float | None = None
_state_lock = threading.Lock()

# ── OS helpers ─────────────────────────────────────────────────────────────────

def _schedule_os(seconds: int) -> None:
    subprocess.run(f"shutdown /s /t {seconds}", shell=True)

def _cancel_os() -> None:
    subprocess.run("shutdown /a", shell=True)

# ── formatting ─────────────────────────────────────────────────────────────────

def fmt_countdown(secs: int) -> str:
    secs = max(0, secs)
    h, rem = divmod(secs, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def seconds_until(epoch: float) -> int:
    return max(0, int(epoch - time.time()))

# ── time parser ────────────────────────────────────────────────────────────────

def parse_time(raw: str) -> tuple[int, int] | None:
    """
    Accepts:  22.30  |  22:30  |  2230  |  22 30
    Returns (hour, minute) or None on failure.
    """
    raw = raw.strip()
    m = re.fullmatch(r"(\d{1,2})[.:](\d{2})", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(\d{3,4})", raw)
    if m:
        s = m.group(1).zfill(4)
        return int(s[:2]), int(s[2:])
    m = re.fullmatch(r"(\d{1,2})\s+(\d{2})", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

# ── bot setup ──────────────────────────────────────────────────────────────────
# Use "!" as the Discord prefix so commands look like  !n shutdown 22.30
# MY_PREFIX is checked manually inside each command handler.

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ── guards ────────────────────────────────────────────────────────────────────

def channel_ok(ctx) -> bool:
    return ALLOWED_CHANNEL is None or ctx.channel.id == ALLOWED_CHANNEL

# ── sub-command logic ──────────────────────────────────────────────────────────

async def do_schedule(ctx, time_str: str) -> None:
    global _scheduled_epoch

    parsed = parse_time(time_str)
    if parsed is None:
        await ctx.send("❌ Couldn't parse that time. Use `HH.MM`, `HH:MM`, or `HHMM`.")
        return

    hour, minute = parsed
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await ctx.send("❌ Invalid time — hour must be 0-23, minute 0-59.")
        return

    now    = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)   # next occurrence

    wait_sec = int((target - now).total_seconds())

    with _state_lock:
        _scheduled_epoch = target.timestamp()
        _schedule_os(wait_sec)

    await ctx.send(
        f"✅ **PC-{MY_PREFIX.upper()}** shutdown scheduled at "
        f"**{target.strftime('%H:%M')}** "
        f"(in {fmt_countdown(wait_sec)})"
    )


async def do_cancel(ctx) -> None:
    global _scheduled_epoch

    with _state_lock:
        if _scheduled_epoch is None:
            await ctx.send(f"⚠️ **PC-{MY_PREFIX.upper()}** has no scheduled shutdown.")
            return
        _cancel_os()
        _scheduled_epoch = None

    await ctx.send(f"✅ **PC-{MY_PREFIX.upper()}** shutdown cancelled.")


async def do_status(ctx) -> None:
    with _state_lock:
        ep = _scheduled_epoch

    if ep is None:
        await ctx.send(f"ℹ️ **PC-{MY_PREFIX.upper()}** — no shutdown scheduled.")
        return

    remaining = seconds_until(ep)
    if remaining == 0:
        await ctx.send(f"ℹ️ **PC-{MY_PREFIX.upper()}** — shutdown time has already passed.")
        return

    at = datetime.fromtimestamp(ep).strftime("%H:%M")
    await ctx.send(
        f"⏳ **PC-{MY_PREFIX.upper()}** shuts down at **{at}** "
        f"— `{fmt_countdown(remaining)}` remaining."
    )

# ── help text ──────────────────────────────────────────────────────────────────

def build_help(p: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"🖥️ PC-{p.upper()} — Shutdown Bot",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name=f"`!{p} shutdown <time>`",
        value="Schedule a shutdown at a given 24h time.\n"
              f"e.g. `!{p} shutdown 22.30`",
        inline=False,
    )
    embed.add_field(
        name=f"`!{p} cancel`",
        value="Cancel the currently scheduled shutdown.",
        inline=False,
    )
    embed.add_field(
        name=f"`!{p} status`",
        value="Show how long until the next shutdown.",
        inline=False,
    )
    embed.add_field(
        name=f"`!{p} help`",
        value="Show this help message.",
        inline=False,
    )
    embed.set_footer(text="Time formats: 22.30 · 22:30 · 2230 · 22 30")
    return embed

# ── single on_message handler (avoids duplicate command registration) ──────────

@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if message.author.id in BLACKLISTED_USERS:
        return
    if ALLOWED_CHANNEL is not None and message.channel.id != ALLOWED_CHANNEL:
        return

    content = message.content.strip()

    # Match  !<prefix> <subcommand> [args...]   case-insensitively
    pattern = re.compile(
        rf"^!{re.escape(MY_PREFIX)}\s+(\S+)(?:\s+(.+))?$",
        re.IGNORECASE,
    )
    m = pattern.match(content)
    if not m:
        # Not our prefix — let the other PC handle it (or ignore)
        return

    # ── dispatch ──────────────────────────────────────────────────────────────
    sub  = m.group(1).lower()
    args = (m.group(2) or "").strip()
    ctx  = await bot.get_context(message)
    if sub == "shutdown":
        if not args:
            await message.channel.send(
                f"❌ Provide a time — e.g. `!{MY_PREFIX} shutdown 22.30`"
            )
        else:
            await do_schedule(ctx, args)

    elif sub == "cancel":
        await do_cancel(ctx)

    elif sub == "status":
        await do_status(ctx)

    elif sub in ("help", "?"):
        await message.channel.send(embed=build_help(MY_PREFIX))

    else:
        await message.channel.send(
            f"❌ Unknown command `{sub}`. "
            f"Try `!{MY_PREFIX} help` for a list of commands."
        )

# ── lifecycle ──────────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    print(f"[shutdown_bot] Logged in as {bot.user}  |  prefix: !{MY_PREFIX}")

bot.run(DISCORD_TOKEN)