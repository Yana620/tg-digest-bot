# 🤖 Telegram Digest Bot

Персональный AI-ассистент для анализа переписок в Telegram.
Читает твои чаты и каждый вечер в 20:00 присылает умный дайджест.

## Команды

| Команда | Что делает |
|---|---|
| `/digest` | Полный дайджест за 24ч с AI анализом |
| `/urgent` | Только срочное за 4ч |
| `/work` | Итоги рабочих чатов |
| `/unread` | Список непрочитанных (без AI, быстро) |
| `/help` | Справка |

⏰ Автоматический дайджест каждый день в **20:00**

---

## 🚀 Деплой за 10 минут

### Шаг 1 — Запусти setup.py

```bash
pip install telethon
python setup.py
```

Скрипт попросит номер телефона Telegram, отправит код, и в конце выдаст **все переменные** готовые к вставке в Railway.

### Шаг 2 — Создай Telegram бота

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → придумай название → придумай username (оканчивается на `_bot`)
3. Скопируй **BOT_TOKEN** (формат `1234567890:ABC...`)

### Шаг 3 — Получи Anthropic API ключ

1. Зарегистрируйся на [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → **Create Key**
3. Пополни баланс на $5 (хватит на ~200 дайджестов)

### Шаг 4 — Деплой на Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/tg-digest)

1. Нажми кнопку выше → войди через GitHub
2. Перейди в **Variables** → добавь 7 переменных из setup.py
3. Нажми **Deploy** → через 2 минуты бот живой ✅

### Шаг 5 — Проверка

Напиши своему боту `/start` — он должен ответить.

---

## 🔒 Безопасность

- `TELEGRAM_SESSION_STRING` — никому не передавай, это полный доступ к твоему Telegram
- Если что-то пошло не так: Telegram → Настройки → Устройства → Завершить все сеансы
- Бот отвечает **только тебе** (защита по chat_id)

---

## Переменные окружения

| Variable | Описание |
|---|---|
| `TELEGRAM_API_ID` | API ID (общий для всех) |
| `TELEGRAM_API_HASH` | API Hash (общий для всех) |
| `TELEGRAM_SESSION_STRING` | Твоя личная сессия (генерирует setup.py) |
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `ANTHROPIC_API_KEY` | Ключ от Anthropic |
| `MY_TELEGRAM_CHAT_ID` | Твой личный Telegram ID (генерирует setup.py) |
| `BOT_TIMEZONE` | Часовой пояс (по умолчанию `Europe/Kiev`) |
