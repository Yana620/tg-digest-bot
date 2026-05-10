"""
Telegram Claude Agent Bot
Claude-агент з повним доступом до Telegram через Telethon tools.
Пишеш будь-яку задачу → Claude сам вирішує що робити → виконує → відповідає.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Credentials ───────────────────────────────────────────────────────────────
API_ID       = int(os.environ["TELEGRAM_API_ID"])
API_HASH     = os.environ["TELEGRAM_API_HASH"]
SESSION      = os.environ["TELEGRAM_SESSION_STRING"]
BOT_TOKEN    = os.environ["TELEGRAM_AGENT_BOT_TOKEN"]   # окремий бот!
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
MY_CHAT_ID   = int(os.environ["MY_TELEGRAM_CHAT_ID"])

# ── Clients ───────────────────────────────────────────────────────────────────
ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
tg = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# Conversation history (зберігає контекст розмови з кожним юзером)
histories: dict[int, list] = {}

# Очікують підтвердження відправки (chat_id: pending action)
pending_sends: dict[int, dict] = {}

# ── Tool definitions (що Claude може робити) ──────────────────────────────────
TOOLS = [
    {
        "name": "list_chats",
        "description": (
            "Отримати список Telegram чатів юзера. "
            "Повертає: назву, ID, тип (особистий/група/канал), "
            "кількість непрочитаних, час останнього повідомлення."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Кількість чатів (за замовчуванням 40)",
                    "default": 40,
                },
                "only_groups": {
                    "type": "boolean",
                    "description": "Тільки групи і канали",
                    "default": False,
                },
                "only_unread": {
                    "type": "boolean",
                    "description": "Тільки чати з непрочитаними",
                    "default": False,
                },
            },
        },
    },
    {
        "name": "get_messages",
        "description": (
            "Отримати останні повідомлення з конкретного чату. "
            "Використовуй chat_id з list_chats."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "integer",
                    "description": "ID чату (з list_chats)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Кількість повідомлень (за замовчуванням 30)",
                    "default": 30,
                },
                "hours_back": {
                    "type": "integer",
                    "description": "Тільки повідомлення за останні N годин (опційно)",
                },
            },
            "required": ["chat_id"],
        },
    },
    {
        "name": "search_messages",
        "description": (
            "Пошук повідомлень по тексту — в усіх чатах або в конкретному. "
            "Корисно для пошуку згадок теми, людини, проекту."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Текст для пошуку",
                },
                "chat_id": {
                    "type": "integer",
                    "description": "Шукати в конкретному чаті (опційно)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Максимум результатів (за замовчуванням 20)",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_unread",
        "description": (
            "Отримати всі непрочитані повідомлення згруповані по чатах. "
            "Повертає кількість і прев'ю останнього повідомлення."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "send_message",
        "description": (
            "Відправити повідомлення в Telegram чат від імені юзера. "
            "ВАЖЛИВО: завжди питай підтвердження у юзера перед відправкою. "
            "Покажи текст який збираєшся відправити і в який чат."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "integer",
                    "description": "ID чату куди відправляти",
                },
                "chat_name": {
                    "type": "string",
                    "description": "Назва чату (для показу юзеру)",
                },
                "text": {
                    "type": "string",
                    "description": "Текст повідомлення",
                },
            },
            "required": ["chat_id", "chat_name", "text"],
        },
    },
    {
        "name": "get_chat_info",
        "description": "Отримати детальну інформацію про конкретний чат або юзера.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "integer",
                    "description": "ID чату або юзера",
                },
            },
            "required": ["chat_id"],
        },
    },
]

# ── Tool implementations (Telethon) ───────────────────────────────────────────

async def tool_list_chats(limit=40, only_groups=False, only_unread=False) -> str:
    if not tg.is_connected():
        await tg.connect()
    result = []
    async for dialog in tg.iter_dialogs(limit=limit):
        if only_groups and not (dialog.is_group or dialog.is_channel):
            continue
        if only_unread and not dialog.unread_count:
            continue
        chat_type = (
            "канал" if dialog.is_channel
            else "група" if dialog.is_group
            else "особистий"
        )
        last_msg_time = dialog.date.strftime("%d.%m %H:%M") if dialog.date else "—"
        result.append({
            "id": dialog.id,
            "name": dialog.name or "Без назви",
            "type": chat_type,
            "unread": dialog.unread_count or 0,
            "last_message": last_msg_time,
        })
    return json.dumps(result, ensure_ascii=False, indent=2)


async def tool_get_messages(chat_id: int, limit=30, hours_back=None) -> str:
    if not tg.is_connected():
        await tg.connect()
    cutoff = None
    if hours_back:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    messages = []
    async for msg in tg.iter_messages(chat_id, limit=limit):
        if cutoff and msg.date and msg.date.replace(tzinfo=timezone.utc) < cutoff:
            break
        if not msg.text:
            continue
        who = "я" if msg.out else (
            getattr(msg.sender, "first_name", None)
            or getattr(msg.sender, "username", None)
            or "хтось"
        ) if msg.sender else "хтось"
        messages.append({
            "id": msg.id,
            "from": who,
            "text": msg.text[:500],
            "time": msg.date.strftime("%d.%m %H:%M") if msg.date else "—",
            "is_mine": msg.out,
        })
    messages.reverse()  # хронологічний порядок
    return json.dumps(messages, ensure_ascii=False, indent=2)


async def tool_search_messages(query: str, chat_id=None, limit=20) -> str:
    if not tg.is_connected():
        await tg.connect()
    results = []
    try:
        if chat_id:
            async for msg in tg.iter_messages(chat_id, search=query, limit=limit):
                if msg.text:
                    results.append({
                        "chat": str(chat_id),
                        "from": getattr(msg.sender, "first_name", "?") if msg.sender else "?",
                        "text": msg.text[:400],
                        "time": msg.date.strftime("%d.%m %H:%M") if msg.date else "—",
                    })
        else:
            async for msg in tg.iter_messages(None, search=query, limit=limit):
                if msg.text:
                    chat = await msg.get_chat()
                    results.append({
                        "chat": getattr(chat, "title", None) or getattr(chat, "first_name", str(chat.id)),
                        "from": getattr(msg.sender, "first_name", "?") if msg.sender else "?",
                        "text": msg.text[:400],
                        "time": msg.date.strftime("%d.%m %H:%M") if msg.date else "—",
                    })
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps(results, ensure_ascii=False, indent=2)


async def tool_get_unread() -> str:
    if not tg.is_connected():
        await tg.connect()
    result = []
    async for dialog in tg.iter_dialogs(limit=60):
        if dialog.unread_count and dialog.unread_count > 0:
            chat_type = "канал" if dialog.is_channel else "група" if dialog.is_group else "особистий"
            # Отримуємо останнє повідомлення
            last_text = ""
            async for msg in tg.iter_messages(dialog, limit=1):
                if msg.text:
                    last_text = msg.text[:200]
            result.append({
                "id": dialog.id,
                "name": dialog.name or "Без назви",
                "type": chat_type,
                "unread_count": dialog.unread_count,
                "last_message": last_text,
            })
    return json.dumps(result, ensure_ascii=False, indent=2)


async def tool_send_message(chat_id: int, chat_name: str, text: str) -> str:
    """Повертає pending — бот запитає підтвердження у юзера."""
    return json.dumps({
        "status": "pending_confirmation",
        "chat_id": chat_id,
        "chat_name": chat_name,
        "text": text,
        "message": "Повідомлення готове. Потрібне підтвердження від юзера.",
    })


async def tool_get_chat_info(chat_id: int) -> str:
    if not tg.is_connected():
        await tg.connect()
    try:
        entity = await tg.get_entity(chat_id)
        info = {
            "id": chat_id,
            "type": type(entity).__name__,
        }
        if hasattr(entity, "title"):
            info["name"] = entity.title
        if hasattr(entity, "first_name"):
            info["name"] = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
        if hasattr(entity, "username") and entity.username:
            info["username"] = f"@{entity.username}"
        if hasattr(entity, "participants_count"):
            info["members"] = entity.participants_count
        return json.dumps(info, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── Tool dispatcher ───────────────────────────────────────────────────────────

async def run_tool(name: str, inputs: dict) -> str:
    try:
        if name == "list_chats":
            return await tool_list_chats(**inputs)
        elif name == "get_messages":
            return await tool_get_messages(**inputs)
        elif name == "search_messages":
            return await tool_search_messages(**inputs)
        elif name == "get_unread":
            return await tool_get_unread()
        elif name == "send_message":
            return await tool_send_message(**inputs)
        elif name == "get_chat_info":
            return await tool_get_chat_info(**inputs)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return json.dumps({"error": str(e)})


# ── Agentic loop ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Ти — персональний AI-асистент з повним доступом до Telegram юзера через tools.

Твої можливості:
- Читати будь-які чати, групи, канали
- Шукати повідомлення по тексту
- Аналізувати переписки і давати підсумки
- Готувати і відправляти повідомлення (з підтвердженням юзера)

Як поводитись:
- Відповідай на мові юзера (зазвичай українська або російська)
- Будь конкретним і структурованим
- Перед відправкою повідомлень ЗАВЖДИ показуй текст і питай підтвердження
- Якщо не зрозуміло — уточни задачу
- Використовуй tools послідовно: спочатку list_chats щоб знайти потрібний чат, потім get_messages

Сьогодні: """ + datetime.now().strftime("%d.%m.%Y %H:%M")


async def agent_loop(user_id: int, user_message: str) -> tuple[str, dict | None]:
    """
    Запускає agentic loop з Claude.
    Повертає (текст_відповіді, pending_send або None).
    """
    # Ініціалізуємо або продовжуємо розмову
    if user_id not in histories:
        histories[user_id] = []

    histories[user_id].append({"role": "user", "content": user_message})

    # Обмежуємо контекст (останні 20 повідомлень)
    history = histories[user_id][-20:]

    pending_send = None

    # Agentic loop — Claude може робити кілька tool calls підряд
    for iteration in range(10):  # максимум 10 ітерацій
        response = ai.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history,
        )

        # Якщо Claude закінчив — повертаємо відповідь
        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "Готово.",
            )
            histories[user_id].append({"role": "assistant", "content": response.content})
            return text, pending_send

        # Claude хоче викликати tools
        if response.stop_reason == "tool_use":
            assistant_msg = {"role": "assistant", "content": response.content}
            histories[user_id].append(assistant_msg)
            history.append(assistant_msg)

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                logger.info(f"Tool call: {block.name}({block.input})")
                result = await run_tool(block.name, block.input)

                # Перевіряємо чи це pending send
                try:
                    result_data = json.loads(result)
                    if result_data.get("status") == "pending_confirmation":
                        pending_send = result_data
                except Exception:
                    pass

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            history.append({"role": "user", "content": tool_results})
            histories[user_id].append({"role": "user", "content": tool_results})
            continue

        # Інший stop reason
        break

    return "Не вдалося завершити задачу. Спробуй ще раз.", None


# ── Telegram bot handlers ─────────────────────────────────────────────────────

def only_me(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != MY_CHAT_ID:
            await update.message.reply_text("⛔ Нет доступа.")
            return
        return await func(update, context)
    return wrapper


@only_me
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привіт! Я твій Claude-агент з доступом до Telegram.\n\n"
        "Пиши мені будь-яку задачу природньою мовою:\n\n"
        "• *Що важливого пропустила за сьогодні?*\n"
        "• *Знайди всі повідомлення про проект X*\n"
        "• *Підготуй відповідь Іванові і надішли*\n"
        "• *Що обговорювали в робочих чатах за тиждень?*\n"
        "• *Хто давно не писав?*\n\n"
        "/clear — очистити контекст розмови\n"
        "/help — підказки",
        parse_mode="Markdown",
    )


@only_me
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories.pop(update.effective_user.id, None)
    await update.message.reply_text("🗑 Контекст очищено. Починаємо заново.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Claude Agent — приклади задач:*\n\n"
        "📊 *Аналіз:*\n"
        "— Що важливого сталось сьогодні?\n"
        "— Підсумуй переписку з @username за тиждень\n"
        "— Які відкриті питання в робочих чатах?\n\n"
        "🔍 *Пошук:*\n"
        "— Знайди всі повідомлення про дедлайн\n"
        "— Коли востаннє писав Михайло?\n"
        "— В яких чатах згадували 'договір'?\n\n"
        "✍️ *Відправка:*\n"
        "— Напиши Іванові що завтра не зможу\n"
        "— Відповіт в чат 'Проект' що все OK\n\n"
        "/clear — скинути контекст розмови",
        parse_mode="Markdown",
    )


@only_me
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Показуємо що думаємо
    thinking_msg = await update.message.reply_text("🤔 Думаю...")

    try:
        answer, pending_send = await agent_loop(user_id, text)

        # Якщо є pending send — показуємо кнопки підтвердження
        if pending_send:
            pending_sends[user_id] = pending_send
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Відправити", callback_data="send_confirm"),
                    InlineKeyboardButton("❌ Скасувати", callback_data="send_cancel"),
                ]
            ])
            await thinking_msg.edit_text(
                f"{answer}\n\n"
                f"📤 *Готове повідомлення для відправки:*\n"
                f"*Чат:* {pending_send['chat_name']}\n"
                f"*Текст:* {pending_send['text']}\n\n"
                f"Відправляємо?",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            # Обрізаємо якщо задовго (Telegram ліміт 4096)
            if len(answer) > 4000:
                chunks = [answer[i:i+4000] for i in range(0, len(answer), 4000)]
                await thinking_msg.edit_text(chunks[0])
                for chunk in chunks[1:]:
                    await update.message.reply_text(chunk)
            else:
                await thinking_msg.edit_text(answer)

    except Exception as e:
        logger.error(f"Agent error: {e}")
        await thinking_msg.edit_text(f"❌ Помилка: {e}\n\nСпробуй ще раз або /clear")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != MY_CHAT_ID:
        await query.answer("⛔ Нет доступа.")
        return

    await query.answer()

    if query.data == "send_confirm":
        pending = pending_sends.pop(user_id, None)
        if not pending:
            await query.edit_message_text("❌ Дія протерміна. Спробуй знову.")
            return
        try:
            if not tg.is_connected():
                await tg.connect()
            await tg.send_message(pending["chat_id"], pending["text"])
            await query.edit_message_text(
                f"✅ Повідомлення відправлено в *{pending['chat_name']}*!",
                parse_mode="Markdown",
            )
            # Додаємо в контекст що відправили
            histories[user_id].append({
                "role": "user",
                "content": f"[Підтверджено] Повідомлення успішно відправлено в {pending['chat_name']}."
            })
        except Exception as e:
            await query.edit_message_text(f"❌ Помилка відправки: {e}")

    elif query.data == "send_cancel":
        pending_sends.pop(user_id, None)
        await query.edit_message_text("❌ Відправку скасовано.")
        histories[user_id].append({
            "role": "user",
            "content": "[Скасовано] Юзер скасував відправку повідомлення."
        })


# ── Main ──────────────────────────────────────────────────────────────────────

async def post_init(app: Application):
    await tg.start()
    logger.info("Telethon connected for agent bot.")


async def post_shutdown(app: Application):
    await tg.disconnect()


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
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Agent bot started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
