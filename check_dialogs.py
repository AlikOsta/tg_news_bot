from telethon import TelegramClient
import os
from dotenv import load_dotenv
import asyncio
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

async def main():
    client = TelegramClient('argentina_news_bot', API_ID, API_HASH)
    await client.start()
    
    print("Доступные диалоги:")
    async for dialog in client.iter_dialogs():
        print(f"ID: {dialog.id}, Название: {dialog.title}, Тип: {dialog.entity.__class__.__name__}")
    
    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}")
