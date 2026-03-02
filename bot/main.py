# -*- coding: utf-8 -*-
import os
import logging
import asyncio
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

import keyboards

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте файл .env")

logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения истории диалога по user_id
dialogue_history = {}

# Загрузка моделей (Inference)
logging.info("Загрузка моделей в память...")

BART_MODEL_PATH = "ainize/bart-base-cnn" 
T5_MODEL_PATH = "google/flan-t5-base"

model_bart = AutoModelForSeq2SeqLM.from_pretrained(BART_MODEL_PATH)
tokenizer_bart = AutoTokenizer.from_pretrained(BART_MODEL_PATH)

model_t5 = AutoModelForSeq2SeqLM.from_pretrained(T5_MODEL_PATH)
tokenizer_t5 = AutoTokenizer.from_pretrained(T5_MODEL_PATH)

# Переменные для хранения текущей выбранной модели
current_model = model_bart
current_tokenizer = tokenizer_bart
current_model_name = "BART (Fine-tuned)"

logging.info("Модели успешно загружены!")

# Вспомогательные функции
def generate_summary(text: str, model, tokenizer) -> str:
    """
    Синхронная функция для генерации саммари. 
    Вызывается в отдельном потоке, чтобы не блокировать асинхронный цикл бота.
    """
    input_ids = tokenizer.encode(text, return_tensors='pt', max_length=512, truncation=True)
    output_ids = model.generate(input_ids, max_length=200, num_return_sequences=1, early_stopping=True)
    return tokenizer.decode(output_ids[0], skip_special_tokens=True)

# Обработчики команд (Handlers)
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    markup = keyboards.get_language_keyboard()
    await message.answer("Привет! 👋 Я умею кратко пересказывать длинные диалоги.\n\nВыберите язык:", reply_markup=markup)

@dp.message_handler(lambda message: message.text in ["🇷🇺 Русский", "🇬🇧 English"])
async def language_selected(message: types.Message):
    if message.text == "🇷🇺 Русский":
        await message.answer("Язык изменен на 🇷🇺 (Русский)", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == "🇬🇧 English":
        await message.answer("Language changed to 🇬🇧 (English)", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = (
        "Доступные команды:\n\n"
        "/model - Выбор модели для суммаризации\n"
        "/checkmodel - Посмотреть название текущей модели\n"
        "/clear - Очистка истории ваших сообщений\n"
        "/help - Вывести список доступных команд\n\n"
        "Просто отправьте мне длинный текст диалога, и я пришлю его краткое содержание!"
    )
    await message.answer(help_text)

@dp.message_handler(commands=['model'])
async def model_command(message: types.Message):
    markup = keyboards.get_model_keyboard()
    await message.answer("Выберите модель для суммаризации:", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data in ['model_bart', 'model_t5'])
async def process_model_selection(callback_query: types.CallbackQuery):
    global current_model, current_tokenizer, current_model_name
    
    if callback_query.data == 'model_bart':
        current_model = model_bart
        current_tokenizer = tokenizer_bart
        current_model_name = "BART (Fine-tuned)"
        await callback_query.answer("Модель BART выбрана")
        await callback_query.message.edit_text("✅ Текущая модель изменена на: BART (Fine-tuned)")
        
    elif callback_query.data == 'model_t5':
        current_model = model_t5
        current_tokenizer = tokenizer_t5
        current_model_name = "Flan-T5 (Base)"
        await callback_query.answer("Модель T5 выбрана")
        await callback_query.message.edit_text("✅ Текущая модель изменена на: Flan-T5 (Base)")

@dp.message_handler(commands=['checkmodel'])
async def checkmodel_command(message: types.Message):
    await message.answer(f"Текущая модель: {current_model_name}")

@dp.message_handler(commands=['clear'])
async def process_clear_command(message: types.Message):
    user_id = message.from_user.id
    dialogue_history[user_id] =[]
    await message.reply("Ваша история диалогов очищена.")

@dp.message_handler()
async def summarize_handler(message: types.Message):
    """
    Основной обработчик текста. Получает текст, прогоняет через ML-модель и возвращает результат.
    """
    user_input = message.text
    user_id = message.from_user.id

    # Проверка на ASCII-символы 
    if not all(ord(char) < 128 for char in user_input):
        await message.answer("Извините, пока я понимаю только английский текст (ASCII-символы).")
        return

    # Сохраняем сообщение в историю конкретного пользователя
    if user_id not in dialogue_history:
        dialogue_history[user_id] = []
    dialogue_history[user_id].append(user_input)

    # Уведомляем пользователя, что процесс пошел (генерация может занимать время)
    processing_msg = await message.answer("⏳ Генерирую саммари, подождите немного...")

    try:
        # Запускаем тяжелую ML-модель в отдельном потоке
        summary = await asyncio.to_thread(
            generate_summary, 
            user_input, 
            current_model, 
            current_tokenizer
        )
        
        if summary:
            await processing_msg.edit_text(f"📝 *Summary:*\n{summary}", parse_mode="Markdown")
        else:
            await processing_msg.edit_text("⚠️ Не удалось сгенерировать саммари (получен пустой ответ).")
            
    except Exception as e:
        logging.error(f"Ошибка при генерации у пользователя {user_id}: {e}")
        await processing_msg.edit_text("❌ Извините, произошла ошибка при обработке текста моделями.")

# Запуск бота
if __name__ == "__main__":
    logging.info("Бот запущен!")
    # skip_updates=True пропускает сообщения, отправленные пока бот был выключен
    executor.start_polling(dp, skip_updates=True)