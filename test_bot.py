import asyncio
import logging
import os
from telethon import TelegramClient
from dotenv import load_dotenv
from mistral_filter import filter_argentina_content
from mistral_api import process_content_with_mistral
from bot import process_message, get_entity_safely

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("test_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Учетные данные API Telegram
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
TARGET_GROUP = os.getenv('TARGET_GROUP')

# Тестовые сообщения
TEST_MESSAGES = [
    {
        "title": "Тестовое сообщение об Аргентине",
        "text": """Аргентина сегодня объявила о новых экономических реформах. 
                  Президент Хавьер Милей представил план по сокращению государственных расходов 
                  и борьбе с инфляцией. Эксперты оценивают эти меры как необходимые, 
                  но предупреждают о возможных социальных последствиях."""
    },
    {
        "title": "Сообщение не об Аргентине",
        "text": """Франция и Германия подписали новое соглашение о сотрудничестве 
                  в области энергетики. Документ предусматривает совместные проекты 
                  по развитию возобновляемых источников энергии."""
    }
]

# Дополнительные тестовые новости для публикации
PUBLICATION_TEST_NEWS = [
    {
        "title": "Экономические реформы в Аргентине",
        "text": """Аргентина запускает новый пакет экономических реформ, направленных на стабилизацию национальной валюты.
                  Центральный банк Аргентины объявил о повышении ключевой ставки до 60% годовых в попытке сдержать инфляцию,
                  которая в прошлом месяце достигла 287%. Президент Хавьер Милей заявил, что эти меры необходимы для
                  восстановления доверия инвесторов и возвращения страны к экономическому росту. Международный валютный фонд
                  приветствовал эти шаги, но отметил, что для полного восстановления экономики потребуется время."""
    },
    {
        "title": "Туристический бум в Буэнос-Айресе",
        "text": """Буэнос-Айрес переживает настоящий туристический бум после девальвации песо. По данным министерства туризма,
                  количество иностранных туристов выросло на 35% по сравнению с прошлым годом. Особенно заметен рост числа
                  посетителей из США, Европы и соседних стран Латинской Америки. Гостиницы в центральных районах города
                  сообщают о 90% заполняемости. Эксперты отмечают, что благодаря выгодному курсу валют, Аргентина стала одним
                  из самых доступных направлений для международного туризма в регионе."""
    }
]

class MockMessage:
    """Простая имитация сообщения Telethon для тестирования"""
    def __init__(self, text, chat=None):
        self.id = 1
        self.message = text  # Текст сообщения
        self.text = text     # Дублируем для совместимости
        self.chat = chat
        self.media = None
        self.date = None

async def create_mock_message(text, client, chat=None):
    """Создает имитацию объекта сообщения для тестирования"""
    return MockMessage(text, chat)

async def test_filter_function():
    """Тестирование функции фильтрации контента по Аргентине"""
    logger.info("=== Тестирование функции фильтрации ===")
    
    for msg in TEST_MESSAGES:
        logger.info(f"Тестирование сообщения: {msg['title']}")
        result = await filter_argentina_content(msg['text'])
        logger.info(f"Результат фильтрации: {result}")

async def test_process_content():
    """Тестирование функции обработки контента через Mistral API"""
    logger.info("=== Тестирование обработки контента ===")
    
    for msg in TEST_MESSAGES:
        logger.info(f"Тестирование обработки: {msg['title']}")
        try:
            result = await process_content_with_mistral(msg['title'], msg['text'])
            logger.info(f"Результат обработки: {result[:100]}...")
        except Exception as e:
            logger.error(f"Ошибка при обработке: {e}")

async def test_full_pipeline():
    """Тестирование полного процесса обработки сообщения"""
    logger.info("=== Тестирование полного процесса обработки ===")
    
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    # Получаем целевую группу для отправки
    target_entity = await get_entity_safely(client, TARGET_GROUP)
    if not target_entity:
        logger.error(f"Не удалось получить целевую группу {TARGET_GROUP}")
        await client.disconnect()
        return
    
    for msg in TEST_MESSAGES:
        logger.info(f"Тестирование полного процесса для: {msg['title']}")
        
        # Создаем имитацию сообщения
        mock_message = await create_mock_message(msg['text'], client)
        
        # Обрабатываем сообщение
        content, media_path, source_info = await process_message(mock_message)
        
        if content:
            logger.info(f"Сообщение успешно обработано. Контент: {content[:100]}...")
            
            # Опционально: отправка в целевую группу для проверки
            send_to_group = input(f"Отправить обработанное сообщение в {TARGET_GROUP}? (y/n): ").lower() == 'y'
            if send_to_group:
                await client.send_message(
                    target_entity,
                    content,
                    parse_mode='md'
                )
                logger.info(f"Сообщение отправлено в {TARGET_GROUP}")
        else:
            logger.info("Сообщение не прошло обработку")
    
    await client.disconnect()

async def test_publish_news():
    """Тестирование публикации новостей в целевую группу"""
    logger.info("=== Тестирование публикации новостей в целевую группу ===")
    
    client = TelegramClient('test_session', API_ID, API_HASH)
    await client.start()
    
    # Получаем целевую группу для отправки
    target_entity = await get_entity_safely(client, TARGET_GROUP)
    if not target_entity:
        logger.error(f"Не удалось получить целевую группу {TARGET_GROUP}")
        await client.disconnect()
        return
    
    # Выводим список доступных новостей
    print("\nДоступные новости для публикации:")
    for i, news in enumerate(PUBLICATION_TEST_NEWS, 1):
        print(f"{i}. {news['title']}")
    
    try:
        choice = int(input("\nВыберите номер новости для публикации (0 для выхода): "))
        if choice == 0:
            logger.info("Публикация отменена пользователем")
            await client.disconnect()
            return
        
        if 1 <= choice <= len(PUBLICATION_TEST_NEWS):
            selected_news = PUBLICATION_TEST_NEWS[choice-1]
            logger.info(f"Выбрана новость: {selected_news['title']}")
            
            # Обработка новости через Mistral API
            logger.info("Обработка новости через Mistral API...")
            processed_content = await process_content_with_mistral(selected_news['title'], selected_news['text'])
            
            # Форматируем контент с использованием Markdown
            lines = processed_content.split('\n')
            if lines and lines[0]:
                # Удаляем символы ### из заголовка, если они есть
                if lines[0].startswith('###'):
                    lines[0] = lines[0].replace('###', '').strip()
                
                # Делаем заголовок полужирным, если он еще не такой
                if not (lines[0].startswith('**') and lines[0].endswith('**')):
                    lines[0] = f"**{lines[0]}**"
                
                formatted_content = '\n'.join(lines)
            else:
                formatted_content = processed_content
            
            # Показываем предварительный просмотр
            print("\n=== Предварительный просмотр новости ===")
            print(formatted_content)
            print("=======================================\n")
            
            # Подтверждение публикации
            confirm = input("Опубликовать эту новость? (y/n): ").lower() == 'y'
            if confirm:
                # Публикация в целевую группу
                await client.send_message(
                    target_entity,
                    formatted_content,
                    parse_mode='md'
                )
                logger.info(f"Новость успешно опубликована в {TARGET_GROUP}")
            else:
                logger.info("Публикация отменена пользователем")
        else:
            logger.error("Неверный номер новости")
    except ValueError:
        logger.error("Введите корректный номер")
    except Exception as e:
        logger.error(f"Ошибка при публикации новости: {e}")
    
    await client.disconnect()

async def main():
    """Основная функция для запуска тестов"""
    logger.info("Начало тестирования бота")
    
    # Выбор теста для запуска
    print("Выберите тест для запуска:")
    print("1. Тест функции фильтрации")
    print("2. Тест обработки контента")
    print("3. Тест полного процесса")
    print("4. Тест публикации новости в целевую группу")
    print("5. Запустить все тесты")
    
    choice = input("Введите номер теста (1-5): ")
    
    if choice == '1':
        await test_filter_function()
    elif choice == '2':
        await test_process_content()
    elif choice == '3':
        await test_full_pipeline()
    elif choice == '4':
        await test_publish_news()
    elif choice == '5':
        await test_filter_function()
        await test_process_content()
        await test_full_pipeline()
        await test_publish_news()
    else:
        logger.error("Неверный выбор")
    
    logger.info("Тестирование завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Тестирование остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
