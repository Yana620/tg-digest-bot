"""Run this locally to generate a new Telegram session string."""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

API_ID   = int(input("Enter TELEGRAM_API_ID: ").strip())
API_HASH = input("Enter TELEGRAM_API_HASH: ").strip()

async def main():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        print("\n✅ New session string (copy this to Railway env vars as TELEGRAM_SESSION_STRING):\n")
        print(client.session.save())
        print()

asyncio.run(main())
