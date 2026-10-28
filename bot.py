import json
import logging
from datetime import datetime
from pathlib import Path

from google_play_scraper import app as gp_app
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== CONFIG ==================
BOT_TOKEN = "9248027011:AAHIm12H1_NRc-g4Bbs1C8405BCIL1TSiZM"
CHAT_ID = 6873189530

CHECK_INTERVAL = 25 * 60

GAMES = {
    "Homescapes": "com.playrix.homescapes",
    "Gardenscapes": "com.playrix.gardenscapes",
    "Township": "com.playrix.township",
    "Fishdom": "com.playrix.fishdomdd.gplay",
    "Mystery Matters": "com.playrix.mysterymatters",
    "Manor Matters": "com.playrix.manormatters",
    "Disney Solitaire": "com.superplaystudios.disneysolitairedreams",
}

STATE_FILE = Path("last_state.json")
# ============================================

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def get_play_info(package: str):
    try:
        result = gp_app(package, lang="en", country="us")
        version = result.get("version") or "Unknown"
        updated_ts = result.get("updated")
        if updated_ts:
            updated_date = datetime.fromtimestamp(updated_ts).strftime("%Y-%m-%d")
        else:
            updated_date = "Unknown"
        return version, updated_date
    except Exception as e:
        logger.error(f"Error with {package}: {e}")
        return None, None

async def check_all(context: ContextTypes.DEFAULT_TYPE, force: bool = False):
    state = load_state()
    messages = []

    for name, package in GAMES.items():
        version, updated = get_play_info(package)
        if version is None:
            continue

        old = state.get(package, {})
        old_version = old.get("version")
        old_updated = old.get("updated")

        if old_version != version or old_updated != updated:
            msg = (
                f"🔔 **{name}** changed!\n"
                f"• Version: `{version}`\n"
                f"• Last Updated: `{updated}`"
            )
            messages.append(msg)

            state[package] = {
                "name": name,
                "version": version,
                "updated": updated,
                "checked_at": datetime.now().isoformat()
            }

    save_state(state)

    if messages:
        full = "\n\n".join(messages)
        await context.bot.send_message(chat_id=CHAT_ID, text=full, parse_mode="Markdown")
    elif force:
        lines = ["📋 Current status:\n"]
        for name, package in GAMES.items():
            info = state.get(package, {})
            lines.append(f"• **{name}**: `{info.get('version', '?')}`  ({info.get('updated', '?')})")
        await context.bot.send_message(chat_id=CHAT_ID, text="\n".join(lines), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot is running!\n\n"
        "Commands:\n"
        "/scan – Check all games now\n"
        "/status – Show last known data"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning Play Store...")
    await check_all(context, force=True)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    if not state:
        await update.message.reply_text("No data yet. Use /scan first.")
        return
    lines = ["📋 Last known data:\n"]
    for package, info in state.items():
        lines.append(f"• **{info.get('name')}**: `{info.get('version')}`  ({info.get('updated')})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    await check_all(context, force=False)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("status", status))

    app.job_queue.run_repeating(auto_check, interval=CHECK_INTERVAL, first=10)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
