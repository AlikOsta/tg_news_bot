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
                
                prompt = f"""Представь, что ты опытный новостной редактор. Твоя задача – на основе предоставленной статьи создать краткую, но информативную версию (до 1000 символов) на русском языке. 
                Текст должен быть четким, интересным и передавать суть оригинальной статьи.

        Требования:
        Добавь к тексту заголовок статьи.
        Сохрани ключевые факты и основную мысль.
        Перевести текст на русский язык.
        Убери лишние детали, делая текст лаконичным.
        Текс сатьи не должен содержать какой-либо рекламы на сервисы, продукты, аккаунты или людей.
        НЕ ИСПОЬЗУЙ ссылки на сайты или другие статьи.(ВАЖНО!!!)
        Длина итогового текста не должна превышать 800 символов.(ВАЖНО!!!)
        В СТАТЬЕ НЕ ДОЛЖНО БЫТЬ ССЫЛОК на источник.

        Исходная статья:
        Заголовок: {title}
        Текст статьи: {article_content}
                """
                
                logger.info("Отправка запроса к Mistral API для обработки контента")
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800
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
