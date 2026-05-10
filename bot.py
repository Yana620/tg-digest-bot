"""
Telegram Digest Bot
Reads your Telegram chats via Telethon (user session) and analyzes them with Claude AI.
Commands: /digest /urgent /work /unread /help
Auto-sends digest every day at 20:00 (your timezone).
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Credentials from environment variables ──────────────────────────────────
API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
SESSION_STRING = os.environ["TELEGRAM_SESSION_STRING"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MY_CHAT_ID = int(os.environ["MY_TELEGRAM_CHAT_ID"])  # твій особистий Telegram ID
TIMEZONE = os.environ.get("BOT_TIMEZONE", "Europe/Kiev")
ALLOWED_USER_ID = int(os.environ["MY_TELEGRAM_CHAT_ID"])  # тільки ти можеш юзати бота

# ── Clients ──────────────────────────────────────────────────────────────────
ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
tg = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)


# ── Security: ignore anyone who isn't you ───────────────────────────────────
def only_me(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ALLOWED_USER_ID:
            await update.message.reply_text("⛔ Нет доступа.")
            return
        return await func(update, context)
    return wrapper


# ── Telethon: fetch messages ─────────────────────────────────────────────────
async def fetch_messages(hours: int = 24, only_groups: bool = False) -> str:
    """Pull messages from all dialogs for the last N hours."""
    if not tg.is_connected():
        await tg.connect()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    chunks = []

    async for dialog in tg.iter_dialogs(limit=60):
        # фільтр по типу чату
        if only_groups and not (dialog.is_group or dialog.is_channel):
            continue
        # пропускаємо архівовані і мутовані канали без активності
        if dialog.archived:
            continue

        lines = []
        async for msg in tg.iter_messages(dialog, limit=30):
            if not msg.date or msg.date.replace(tzinfo=timezone.utc) < cutoff:
                break
            if not msg.text:
                continue
            who = "я" if msg.out else (
                getattr(msg.sender, "first_name", None)
                or getattr(msg.sender, "username", None)
                or "кто-то"
            ) if msg.sender else "кто-то"
            lines.append(f"  [{who}]: {msg.text[:300]}")

        if lines:
            tag = "👥 группа" if dialog.is_group or dialog.is_channel else "👤 личное"
            chunks.append(f"\n[{tag}] {dialog.name}:\n" + "\n".join(reversed(lines)))

    return "\n".join(chunks) if chunks else "Новых сообщений нет."


# ── Claude AI analysis ───────────────────────────────────────────────────────
PROMPTS = {
    "digest": """\
Ты — персональный ассистент по анализу переписок в Telegram.
Проанализируй переписки за последние 24 часа и выдай чёткий дайджест.

ПЕРЕПИСКИ:
{text}

Ответ строго в таком формате (используй эмодзи, будь краткой):

🔴 СРОЧНО — требует ответа сегодня:
• ...

📌 ВАЖНОЕ — решения, новости, результаты:
• ...

💼 РАБОЧИЕ ИТОГИ:
• [чат]: что происходит, action items

📬 ЖДУТ ОТВЕТА:
• [от кого] — суть — черновик ответа в 1 строку

🗑 МОЖНО ИГНОРИРОВАТЬ:
• ...

Пиши по-русски, коротко и конкретно.""",

    "urgent": """\
Проанализируй переписки за последние 4 часа.
Найди ТОЛЬКО то, что требует реакции сегодня — срочные вопросы, дедлайны, важные новости.

ПЕРЕПИСКИ:
{text}

Формат:
🔴 СРОЧНО:
• [от кого в каком чате] — суть — что ответить

Если ничего срочного — так и напиши одной строкой.""",

    "work": """\
Проанализируй ТОЛЬКО рабочие групповые чаты.
Дай структурированные итоги — что обсуждали, какие решения, что от тебя ждут.

ПЕРЕПИСКИ:
{text}

Формат:
💼 [Название чата]:
  — Темы: ...
  — Решения: ...
  — От тебя ждут: ...

Пиши по-русски, коротко.""",
}


async def ask_claude(text: str, mode: str) -> str:
    prompt = PROMPTS[mode].format(text=text)
    resp = ai.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


# ── Bot command handlers ─────────────────────────────────────────────────────
@only_me
async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Собираю сообщения за 24ч…")
    try:
        text = await fetch_messages(hours=24)
        result = await ask_claude(text, "digest")
        await msg.edit_text(f"📊 *Дайджест за 24 часа*\n\n{result}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


@only_me
async def cmd_urgent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Проверяю срочное за 4ч…")
    try:
        text = await fetch_messages(hours=4)
        result = await ask_claude(text, "urgent")
        await msg.edit_text(f"🔴 *Срочное (4ч)*\n\n{result}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


@only_me
async def cmd_work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Анализирую рабочие чаты…")
    try:
        text = await fetch_messages(hours=24, only_groups=True)
        result = await ask_claude(text, "work")
        await msg.edit_text(f"💼 *Рабочие чаты*\n\n{result}", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


@only_me
async def cmd_unread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Получаю непрочитанные…")
    try:
        if not tg.is_connected():
            await tg.connect()
        lines = []
        async for dialog in tg.iter_dialogs(limit=60):
            if dialog.unread_count and dialog.unread_count > 0:
                icon = "👥" if dialog.is_group or dialog.is_channel else "👤"
                lines.append(f"{icon} *{dialog.name}* — {dialog.unread_count} сообщ.")
        text = ("📬 *Непрочитанные:*\n\n" + "\n".join(lines)) if lines else "✅ Всё прочитано!"
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


@only_me
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Показуємо chat_id для налаштування (корисно при першому запуску)
    cid = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Привет! Твой chat\\_id: `{cid}`\n\n"
        "/digest — дайджест 24ч\n"
        "/urgent — срочное 4ч\n"
        "/work — рабочие чаты\n"
        "/unread — непрочитанные\n"
        "/help — справка",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Telegram Digest Bot*\n\n"
        "/digest — полный дайджест за 24ч с AI\n"
        "/urgent — срочное за 4ч\n"
        "/work — итоги рабочих чатов\n"
        "/unread — список непрочитанных (без AI)\n"
        "/help — эта справка\n\n"
        "⏰ Автодайджест каждый день в 20:00",
        parse_mode="Markdown",
    )


# ── Scheduled daily digest ───────────────────────────────────────────────────
async def send_evening_digest(app: Application):
    logger.info("Sending scheduled evening digest…")
    try:
        text = await fetch_messages(hours=24)
        result = await ask_claude(text, "digest")
        await app.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=f"🌙 *Вечерний дайджест*\n\n{result}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Scheduled digest error: {e}")
        await app.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=f"❌ Ошибка вечернего дайджеста: {e}",
        )


# ── Main ─────────────────────────────────────────────────────────────────────
async def post_init(app: Application):
    """Called after bot starts — connect Telethon and set up scheduler."""
    await tg.start()
    logger.info("Telethon connected.")

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_evening_digest,
        trigger="cron",
        hour=20,
        minute=0,
        args=[app],
    )
    scheduler.start()
    logger.info(f"Scheduler started. Daily digest at 20:00 {TIMEZONE}.")


async def post_shutdown(app: Application):
    await tg.disconnect()
    logger.info("Telethon disconnected.")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("urgent", cmd_urgent))
    app.add_handler(CommandHandler("work", cmd_work))
    app.add_handler(CommandHandler("unread", cmd_unread))

    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
