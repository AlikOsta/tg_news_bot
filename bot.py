import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto, User, Chat, Channel
from dotenv import load_dotenv
from mistral_filter import filter_argentina_content
from mistral_api import process_content_with_mistral
from collections import deque

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Учетные данные API Telegram
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
SOURCE_GROUPS = os.getenv('SOURCE_GROUPS').split(',')
TARGET_GROUP = os.getenv('TARGET_GROUP')

# Создаем папку для временного хранения медиа файлов
MEDIA_FOLDER = "temp_media"
if not os.path.exists(MEDIA_FOLDER):
    os.makedirs(MEDIA_FOLDER)
    logger.info(f"Создана папка для временного хранения медиа: {MEDIA_FOLDER}")

# Инициализация клиента Telegram
client = TelegramClient('argentina_news_bot', API_ID, API_HASH)

# Отслеживание обработанных сообщений для избежания дубликатов (ограничение до 1000 сообщений)
processed_messages = deque(maxlen=1000)

async def download_media(message):
    """Загрузка медиа из сообщения и возврат пути к файлу."""
    if message.media:
        logger.info(f"Загрузка медиа из сообщения ID: {message.id}")
        # Сохраняем в папку MEDIA_FOLDER
        path = await client.download_media(message, file=MEDIA_FOLDER)
        logger.info(f"Медиа успешно загружено: {path}")
        return path
    return None

async def process_message(message):
    """Обработка сообщения для определения его релевантности и переформатирования."""
    # Получаем информацию об источнике сообщения
    source_info = ""
    if message.chat:
        if isinstance(message.chat, User):
            chat_name = f"{message.chat.first_name} {message.chat.last_name if message.chat.last_name else ''}".strip()
            source_info = f"пользователя {chat_name}"
        else:
            source_info = f"группы/канала {message.chat.title}"
    
    logger.info(f"Начало обработки сообщения ID: {message.id} из {source_info}")
    
    if message.id in processed_messages:
        logger.info(f"Сообщение ID: {message.id} уже было обработано ранее. Пропускаем.")
        return None, None, None
    
    # Извлечение текстового содержимого
    if not message.text:
        logger.info(f"Сообщение ID: {message.id} не содержит текста. Пропускаем.")
        return None, None, None
    
    logger.info(f"Проверка релевантности сообщения ID: {message.id} для Аргентины")
    # Первый фильтр: проверка, связано ли содержимое с Аргентиной
    is_relevant = await filter_argentina_content(message.text)
    if not is_relevant:
        logger.info(f"Сообщение ID: {message.id} из {source_info} отфильтровано - не связано с Аргентиной")
        return None, None, None
    
    logger.info(f"Сообщение ID: {message.id} признано релевантным для Аргентины. Продолжаем обработку.")
    
    # Добавляем паузу в 2 секунды между запросами к Mistral API
    logger.info(f"Пауза 2 секунды перед обработкой контента через Mistral API")
    await asyncio.sleep(2)
    
    # Второй фильтр: обработка содержимого с помощью Mistral для создания чистого резюме
    try:
        # Проверяем тип сущности чата
        if message.chat:
            if isinstance(message.chat, User):
                chat_name = f"{message.chat.first_name} {message.chat.last_name if message.chat.last_name else ''}".strip()
                title = f"News from {chat_name}"
            else:
                title = f"News from {message.chat.title}"
        else:
            title = "News Update"
        
        logger.info(f"Отправка сообщения ID: {message.id} на обработку в Mistral API")
        processed_content = await process_content_with_mistral(title, message.text)
        logger.info(f"Сообщение ID: {message.id} успешно обработано Mistral API")
        
        # Загрузка медиа, если доступно
        media_path = await download_media(message)
        
        # Отметка как обработанное
        processed_messages.append(message.id)
        logger.info(f"Сообщение ID: {message.id} добавлено в список обработанных")
        
        # Форматируем контент с использованием Markdown
        lines = processed_content.split('\n')
        if lines and lines[0]:
            # Удаляем символы ### из заголовка, если они есть
            if lines[0].startswith('###'):
                lines[0] = lines[0].replace('###', '').strip()
            
            # Проверяем, не содержит ли первая строка уже форматирование жирным шрифтом
            if not (lines[0].startswith('**') and lines[0].endswith('**')):
                lines[0] = f"**{lines[0]}**"
            formatted_content = '\n'.join(lines)
        else:
            formatted_content = processed_content
            
        logger.info(f"Контент отформатирован с использованием Markdown")
        
        return formatted_content, media_path, source_info
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения ID: {message.id} из {source_info}: {e}")
        return None, None, None

async def get_entity_safely(client, entity_id):
    """Безопасное получение сущности по ID или имени пользователя."""
    logger.info(f"Попытка получения сущности: {entity_id}")
    try:
        # Если это ID (начинается с - или является числом)
        if entity_id.startswith('-') or entity_id.isdigit():
            try:
                entity = await client.get_entity(int(entity_id))
                logger.info(f"Успешно получена сущность по ID: {entity_id}")
                return entity
            except ValueError:
                logger.warning(f"Не удалось найти сущность с ID: {entity_id}")
                return None
        # Если это юзернейм (начинается с @ или без него)
        else:
            username = entity_id.lstrip('@')
            try:
                entity = await client.get_entity(username)
                logger.info(f"Успешно получена сущность по имени пользователя: {username}")
                return entity
            except ValueError:
                logger.warning(f"Не удалось найти сущность с именем пользователя: {username}")
                return None
    except Exception as e:
        logger.error(f"Ошибка при получении сущности {entity_id}: {e}")
        return None

async def main():
    """Основная функция для запуска бота."""
    logger.info("Запуск бота...")
    await client.start()
    logger.info("Бот успешно запущен!")
    
    # Получаем сущности для исходных групп
    source_entities = []
    for group_id in SOURCE_GROUPS:
        logger.info(f"Подключение к исходной группе: {group_id}")
        entity = await get_entity_safely(client, group_id)
        if entity:
            source_entities.append(entity)
            # Проверяем тип сущности и используем соответствующие атрибуты
            if isinstance(entity, User):
                name = f"{entity.first_name} {entity.last_name if entity.last_name else ''}"
                logger.info(f"Успешно подключен к исходному пользователю: {name.strip()}")
            else:
                logger.info(f"Успешно подключен к исходной группе/каналу: {entity.title}")
        else:
            logger.error(f"Не удалось подключиться к исходной группе: {group_id}")
    
    # Получаем сущность для целевой группы
    logger.info(f"Подключение к целевой группе: {TARGET_GROUP}")
    target_entity = await get_entity_safely(client, TARGET_GROUP)
    if not target_entity:
        logger.error(f"Не удалось подключиться к целевой группе: {TARGET_GROUP}")
        return
    
    # Также проверяем тип целевой сущности
    if isinstance(target_entity, User):
        name = f"{target_entity.first_name} {target_entity.last_name if target_entity.last_name else ''}"
        logger.info(f"Успешно подключен к целевому пользователю: {name.strip()}")
    else:
        logger.info(f"Успешно подключен к целевой группе/каналу: {target_entity.title}")
    
    # Регистрируем обработчик для новых сообщений
    @client.on(events.NewMessage(chats=source_entities))
    async def handle_new_message(event):
        try:
            # Получаем информацию об источнике
            if isinstance(event.chat, User):
                source_name = f"{event.chat.first_name} {event.chat.last_name if event.chat.last_name else ''}".strip()
            else:
                source_name = event.chat.title
                
            logger.info(f"Получено новое сообщение ID: {event.message.id} из источника: {source_name}")
            
            content, media_path, source_info = await process_message(event.message)
            if content:
                logger.info(f"Сообщение ID: {event.message.id} готово к отправке в целевую группу")
                # Отправка в целевую группу
                if media_path:
                    logger.info(f"Отправка сообщения ID: {event.message.id} с медиа в целевую группу")
                    # Отправляем с поддержкой Markdown
                    await client.send_file(
                        target_entity, 
                        media_path, 
                        caption=content,
                        parse_mode='md'  # Включаем поддержку Markdown
                    )
                    # Очистка загруженного файла
                    if os.path.exists(media_path):
                        os.remove(media_path)
                        logger.info(f"Медиа-файл {media_path} удален после отправки")
                else:
                    logger.info(f"Отправка текстового сообщения ID: {event.message.id} в целевую группу")
                    # Отправляем с поддержкой Markdown
                    await client.send_message(
                        target_entity, 
                        content,
                        parse_mode='md'  # Включаем поддержку Markdown
                    )
                
                logger.info(f"Успешно обработано и переслано сообщение ID: {event.message.id} из {source_info}")
            else:
                logger.info(f"Сообщение ID: {event.message.id} не прошло обработку и не будет отправлено")
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения ID: {event.message.id}: {e}")
    
    logger.info("Бот запущен и ожидает новые сообщения...")
    # Запуск клиента до отключения
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
