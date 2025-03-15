from mistralai import Mistral
import os
from dotenv import load_dotenv
import asyncio
import time
import logging

load_dotenv()
logger = logging.getLogger(__name__)

async def filter_argentina_content(text, max_retries=3, initial_delay=2):
    logger.info("Запрос к Mistral AI (фильтр на релевантность к Аргентине)")
    """
    Filter content to determine if it's related to Argentina.
    Returns True if content is related to Argentina, False otherwise.
    """
    retry_count = 0
    delay = initial_delay
    
    while retry_count < max_retries:
        try:
            logger.info(f"Попытка фильтрации #{retry_count+1}")
            client = Mistral(api_key=os.getenv('MISTRAL_API_KEY_FILTER'))
            
            # Получаем промпт из .env и форматируем его с текстом
            prompt_template = os.getenv('FILTER_PROMPT')
            prompt = prompt_template.format(text=text)
            
            # Получаем модель и максимальное количество токенов из .env
            model = os.getenv('FILTER_MODEL', 'mistral-large-latest')
            max_tokens = int(os.getenv('FILTER_MAX_TOKENS', 10))
            
            # Run in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            logger.info("Отправка запроса к Mistral API для фильтрации")
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.complete(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens
                )
            )
            
            answer = response.choices[0].message.content.strip().upper()
            result = "ДА" in answer
            logger.info(f"Получен ответ от Mistral API: {answer}. Результат фильтрации: {'релевантно' if result else 'не релевантно'}")
            return result
            
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Ошибка при фильтрации контента: {e}. Повторная попытка через {delay} секунд...")
                await asyncio.sleep(delay)
                delay *= 2  # Экспоненциальная задержка
            else:
                logger.error(f"Ошибка фильтрации контента после {max_retries} попыток: {e}")
                return False
