# Telegram Claude Agent

Персональный AI-ассистент, подключённый к твоему Telegram. Общаешься с ним как с Claude напрямую — он читает твои чаты, делает сводки, ищет сообщения, помогает с ответами.

**Примеры запросов:**
- *"Что важного пропустил за последние 3 дня?"*
- *"Сделай саммари непрочитанных в рабочих чатах"*
- *"Найди все сообщения про проект X"*
- *"Напиши Даниилу что буду через 10 минут"*

---

## Что понадобится

- Python 3.10+ (проверь: `python --version` или `python3 --version`)
- Аккаунт на [railway.app](https://railway.app) (бесплатно)
- Личный аккаунт Telegram
- Личный аккаунт Anthropic ([console.anthropic.com](https://console.anthropic.com))

---

## Установка — пошагово

### Шаг 1 — Скачай репозиторий

```bash
# Mac / Linux
git clone https://github.com/Yana620/tg-digest-bot.git
cd tg-digest-bot

# Или просто скачай ZIP через кнопку Code → Download ZIP на GitHub
```

### Шаг 2 — Получи Telegram API ключи

1. Открой [my.telegram.org](https://my.telegram.org) в браузере
2. Войди через свой номер телефона (придёт код в Telegram)
3. Нажми **API development tools**
4. Заполни форму (название и платформа — любые, например "My Agent" / "Desktop")
5. Нажми **Create application**
6. Скопируй и сохрани:
   - `App api_id` — число, например `12345678`
   - `App api_hash` — строка, например `abc123def456...`

### Шаг 3 — Создай Telegram бота

1. Открой Telegram, найди [@BotFather](https://t.me/BotFather)
2. Напиши `/newbot`
3. Придумай **название** бота (например: `My Claude Agent`)
4. Придумай **username** — должен заканчиваться на `_bot` (например: `my_claude_agent_bot`)
5. BotFather пришлёт **токен** — длинная строка вида `8619134257:AAE3b7t2f60x...`
6. Сохрани этот токен

### Шаг 4 — Получи Anthropic API ключ

1. Зарегистрируйся на [console.anthropic.com](https://console.anthropic.com)
2. Перейди в **Settings → API Keys → Create Key**
3. Скопируй ключ (начинается с `sk-ant-...`)
4. Пополни баланс на $5 — этого хватит примерно на 500 запросов

### Шаг 5 — Запусти setup.py

Установи зависимость и запусти скрипт:

**Mac:**
```bash
pip3 install telethon
python3 setup.py
```

**Windows:**
```bash
pip install telethon
python setup.py
```

Скрипт спросит:
- `API_ID` и `API_HASH` — из Шага 2
- Номер телефона Telegram — придёт код подтверждения
- Код из Telegram
- Если есть 2FA — пароль

В конце скрипт выдаст:
1. **Переменные для Railway** — скопируй их, они нужны в Шаге 6
2. **Конфиг для Claude Desktop** — если хочешь подключить MCP (Шаг 8)

### Шаг 6 — Задеплой на Railway

1. Зайди на [railway.app](https://railway.app) → войди через GitHub
2. Нажми **New Project → Deploy from GitHub repo**
3. Выбери репозиторий `tg-digest-bot`
4. Перейди в **Variables** и добавь 6 переменных (значения берёшь из вывода setup.py):

| Переменная | Описание |
|---|---|
| `TELEGRAM_API_ID` | Из my.telegram.org |
| `TELEGRAM_API_HASH` | Из my.telegram.org |
| `TELEGRAM_SESSION_STRING` | Генерирует setup.py |
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `ANTHROPIC_API_KEY` | Ключ от Anthropic |
| `MY_TELEGRAM_CHAT_ID` | Генерирует setup.py |

5. Railway автоматически задеплоит — подожди 2 минуты

### Шаг 7 — Проверь что работает

Открой Telegram, найди своего бота по username и напиши `/start` — он должен ответить.

Попробуй написать: *"Покажи мои последние чаты"* — бот обратится к Claude и прочитает твой Telegram.

---

## Шаг 8 (опционально) — MCP-коннектор для Claude Desktop

Если хочешь управлять Telegram прямо из Claude Desktop (без отдельного бота):

**1. Установи telegram-mcp:**

```bash
pip3 install telegram-mcp   # Mac
pip install telegram-mcp    # Windows
```

**2. Найди файл конфига Claude Desktop:**
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**3. Вставь конфиг** (setup.py сгенерировал его автоматически с твоими данными):

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

**4. Перезапусти Claude Desktop** — в боковой панели появится иконка Telegram.

Шаблон конфига также лежит в файле `mcp_config_template.json` в этом репозитории.

---

## Безопасность

- `TELEGRAM_SESSION_STRING` — **никому не передавай**, это полный доступ к твоему Telegram аккаунту
- Бот отвечает **только тебе** — защита по Telegram ID, посторонние не смогут им пользоваться
- Если что-то пошло не так или хочешь отозвать доступ: Telegram → Настройки → Конфиденциальность → Активные сеансы → завершить нужный сеанс

---

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие и список возможностей |
| `/clear` | Сбросить контекст разговора |
| `/help` | Примеры запросов |

Всё остальное — просто пиши на естественном языке.
