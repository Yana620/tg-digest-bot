"""
Telegram Digest Bot — Setup Wizard
Запусти этот скрипт ОДИН РАЗ чтобы получить все переменные для Railway.

Требования: Python 3.10+
Установка зависимостей: pip install telethon qrcode
"""

import asyncio
import sys

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("❌ Установи зависимости: pip install telethon qrcode")
    sys.exit(1)

# ── Credentials (каждый вводит свои с my.telegram.org) ───────────────────────
print("\n🔑 Введи свои данные с my.telegram.org (App api_id и App api_hash):")
API_ID   = int(input("  API_ID → ").strip())
API_HASH = input("  API_HASH → ").strip()

BANNER = """
╔══════════════════════════════════════════════════╗
║        Telegram Digest Bot — Setup Wizard        ║
║  Генерирует все переменные для деплоя на Railway  ║
╚══════════════════════════════════════════════════╝
"""

async def generate_session() -> str:
    """Авторизується і повертає session string."""
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    print("\n📱 Введи свой номер телефона Telegram (формат: +380961234567):")
    phone = input("  → ").strip()

    await client.send_code_request(phone)
    print("\n💬 Telegram отправил код подтверждения. Введи его:")
    code = input("  → ").strip()

    try:
        await client.sign_in(phone, code)
    except Exception as e:
        if "two-steps" in str(e).lower() or "password" in str(e).lower():
            print("\n🔐 У тебя включена 2FA. Введи пароль Telegram:")
            password = input("  → ").strip()
            await client.sign_in(password=password)
        else:
            raise

    session = client.session.save()
    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username or 'нет username'})")
    print(f"   Твой chat_id: {me.id}")

    await client.disconnect()
    return session, me.id


def print_mcp_config(api_id: int, api_hash: str, session_string: str):
    """Виводить готовий конфіг для Claude Desktop MCP."""
    print("""
╔══════════════════════════════════════════════════╗
║         MCP-коннектор для Claude Desktop          ║
╚══════════════════════════════════════════════════╝

1. Установи telegram-mcp:
   pip install telegram-mcp       (Windows)
   pip3 install telegram-mcp      (Mac)

2. Открой файл конфига Claude Desktop:
   Mac:     ~/Library/Application Support/Claude/claude_desktop_config.json
   Windows: %APPDATA%\\Claude\\claude_desktop_config.json

3. Вставь туда этот конфиг (или добавь в существующий):
""")
    import json
    config = {
        "mcpServers": {
            "telegram": {
                "command": "python",
                "args": ["-m", "telegram_mcp"],
                "env": {
                    "TELEGRAM_API_ID": str(api_id),
                    "TELEGRAM_API_HASH": api_hash,
                    "TELEGRAM_SESSION_STRING": session_string,
                }
            }
        }
    }
    print(json.dumps(config, indent=2, ensure_ascii=False))
    print("\n4. Перезапусти Claude Desktop — в боковой панели появится Telegram.")


def print_env_vars(session_string: str, chat_id: int):
    """Виводить готові змінні для Railway."""

    print("""
╔══════════════════════════════════════════════════╗
║         ГОТОВО! Скопируй в Railway Variables      ║
╚══════════════════════════════════════════════════╝

Иди на railway.app → твой проект → Variables
и добавь эти 7 переменных:
""")

    vars_to_add = [
        ("TELEGRAM_API_ID",         str(API_ID)),
        ("TELEGRAM_API_HASH",       API_HASH),
        ("TELEGRAM_SESSION_STRING", session_string),
        ("TELEGRAM_BOT_TOKEN",      "← вставь токен от @BotFather"),
        ("ANTHROPIC_API_KEY",       "← вставь ключ с console.anthropic.com"),
        ("MY_TELEGRAM_CHAT_ID",     str(chat_id)),
        ("BOT_TIMEZONE",            "Europe/Kiev"),
    ]

    for name, value in vars_to_add:
        print(f"  {name}")
        print(f"  {value}")
        print()

    print("─" * 52)
    print("""
⚠️  ВАЖНО:
  • TELEGRAM_BOT_TOKEN  — создай бота через @BotFather → /newbot
  • ANTHROPIC_API_KEY   — получи на console.anthropic.com (Settings → API Keys)
  • BOT_TIMEZONE        — измени если не Киев (например Europe/Warsaw)

🔒 БЕЗОПАСНОСТЬ:
  • Никому не передавай TELEGRAM_SESSION_STRING — это полный доступ к твоему Telegram
  • Если что-то пошло не так: Telegram → Настройки → Устройства → Завершить все сеансы
""")


async def main():
    print(BANNER)
    print("Этот скрипт поможет тебе получить все данные для деплоя бота.")
    print("Ничего не устанавливается на сервер — просто генерируем строку сессии.\n")

    input("Нажми Enter чтобы начать → ")

    try:
        session_string, chat_id = await generate_session()
        print_env_vars(session_string, chat_id)
        print_mcp_config(API_ID, API_HASH, session_string)
    except KeyboardInterrupt:
        print("\n\n⛔ Отменено.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("Попробуй снова или напиши организатору.")


if __name__ == "__main__":
    asyncio.run(main())
