# Telegram Claude Agent

Персональный AI-ассистент, который подключается к твоему Telegram и отвечает на любые запросы на естественном языке через Claude.

Пишешь боту что угодно — он сам решает что делать: читает чаты, ищет сообщения, делает сводки, готовит ответы.

**Примеры:**
- *"Что важного пропустила за последние 3 дня?"*
- *"Найди все сообщения про проект X"*
- *"Сделай саммари непрочитанных в рабочих чатах"*
- *"Напиши Даниилу что буду через 10 минут"*

---

## Быстрый старт — 5 шагов (~20 минут)

### Шаг 1 — Получи Telegram API ключи

1. Открой [my.telegram.org](https://my.telegram.org) и войди через свой номер
2. → **API development tools** → создай приложение (название любое)
3. Скопируй **App api_id** и **App api_hash**

### Шаг 2 — Создай Telegram бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → придумай название → придумай username (должен заканчиваться на `_bot`)
3. Скопируй **токен** (формат `1234567890:ABCdef...`)

### Шаг 3 — Получи Anthropic API ключ

1. Зарегистрируйся на [console.anthropic.com](https://console.anthropic.com)
2. **Settings → API Keys → Create Key**
3. Пополни баланс на $5 (хватит на ~500 запросов)

### Шаг 4 — Сгенерируй сессию и переменные

Скачай репозиторий и запусти скрипт:

**Windows:**
```bash
pip install telethon
python setup.py
```

**Mac:**
```bash
pip3 install telethon
python3 setup.py
```

Скрипт спросит твои данные, подтвердит номер телефона через Telegram и выдаст **готовые переменные** для вставки в Railway.

### Шаг 5 — Деплой на Railway

1. Зарегистрируйся на [railway.app](https://railway.app) (бесплатно)
2. **New Project → Deploy from GitHub repo** → выбери этот репозиторий
3. Перейди в **Variables** и добавь 6 переменных из setup.py:

| Переменная | Откуда |
|---|---|
| `TELEGRAM_API_ID` | my.telegram.org |
| `TELEGRAM_API_HASH` | my.telegram.org |
| `TELEGRAM_SESSION_STRING` | генерирует setup.py |
| `TELEGRAM_BOT_TOKEN` | @BotFather |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `MY_TELEGRAM_CHAT_ID` | генерирует setup.py |

4. Railway автоматически задеплоит — через 2 минуты бот живой ✅

Напиши своему боту `/start` — он должен ответить.

---

## MCP-коннектор для Claude Desktop / Claude Code

Если хочешь управлять Telegram напрямую из Claude Desktop (без отдельного бота):

**Репозиторий:** [github.com/chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp)

Установка:
```bash
pip install telegram-mcp
```

Найди файл конфига Claude Desktop:
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Добавь в него:
```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["-m", "telegram_mcp"],
      "env": {
        "TELEGRAM_API_ID": "твой_api_id",
        "TELEGRAM_API_HASH": "твой_api_hash",
        "TELEGRAM_SESSION_STRING": "твоя_сессия"
      }
    }
  }
}
```

---

## Безопасность

- `TELEGRAM_SESSION_STRING` — **никому не передавай**, это полный доступ к твоему Telegram
- Бот отвечает **только тебе** (защита по Telegram ID)
- Если что-то пошло не так: Telegram → Настройки → Конфиденциальность → Активные сеансы → Завершить все

---

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие и список возможностей |
| `/clear` | Сбросить контекст разговора |
| `/help` | Примеры запросов |
