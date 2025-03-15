from mistralai import Mistral
import os
import asyncio
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

async def process_content_with_mistral(title, article_content, max_retries=3, initial_delay=2):
    logger.info("Запрос к Mistral AI (обработка контента)")
    """
    Process article content with Mistral AI to create a summarized version.
    
    Args:
        title (str): The title of the article
        article_content (str): The content of the article
        max_retries (int): Maximum number of retry attempts
        initial_delay (int): Initial delay between retries in seconds
        
    Returns:
        str: Processed content
    """
    retry_count = 0
    delay = initial_delay
    
    while retry_count < max_retries:
        try:
            logger.info(f"Попытка обработки контента через Mistral API #{retry_count+1}")
            # Используем run_in_executor для выполнения блокирующего кода в отдельном потоке
            loop = asyncio.get_event_loop()
            
            def process_with_mistral():
                logger.info("Инициализация клиента Mistral API")
                client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
                
                # Получаем промпт из .env и форматируем его с заголовком и содержанием
                prompt_template = os.getenv('CONTENT_PROMPT')
                prompt = prompt_template.format(title=title, article_content=article_content)
                
                # Получаем модель и максимальное количество токенов из .env
                model = os.getenv('CONTENT_MODEL', 'mistral-large-latest')
                max_tokens = int(os.getenv('CONTENT_MAX_TOKENS', 800))
                
                logger.info("Отправка запроса к Mistral API для обработки контента")
                chat_response = client.chat.complete(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens
                )
                
                logger.info("Получен ответ от Mistral API")
                return chat_response.choices[0].message.content
            
            # Выполняем блокирующий код в отдельном потоке
            result = await loop.run_in_executor(None, process_with_mistral)
            logger.info("Контент успешно обработан через Mistral API")
            return result
            
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Ошибка при обработке контента: {e}. Повторная попытка через {delay} секунд...")
                await asyncio.sleep(delay)
                delay *= 2  # Экспоненциальная задержка
            else:
                logger.error(f"Mistral AI обработка не удалась после {max_retries} попыток: {e}")
                raise ValueError(f"Mistral AI processing failed after {max_retries} attempts: {e}")
