# -*- coding: utf-8 -*-
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_language_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает и возвращает Reply-клавиатуру для выбора языка.
    """
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton("🇷🇺 Русский")
    btn2 = KeyboardButton("🇬🇧 English")
    markup.add(btn1, btn2)
    return markup

def get_model_keyboard() -> InlineKeyboardMarkup:
    """
    Создает и возвращает Inline-клавиатуру для выбора модели суммаризации.
    """
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("BART (Fine-tuned)", callback_data='model_bart')
    btn2 = InlineKeyboardButton("Flan-T5 (Base)", callback_data='model_t5')
    markup.add(btn1, btn2)
    return markup