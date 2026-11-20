import io
from aiogram import Router, F, Bot
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

import config
from handlers.common import is_authorized
from utils.gemini_client import gemini_manager

router = Router()

def split_text_into_chunks(text: str, max_chunk_size: int = 3800) -> list[str]:
    """Разбивает длинный ответ на аккуратные блоки по параграфам."""
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    current_chunk = ""
    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            current_chunk += (paragraph + "\n\n")
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            while len(paragraph) > max_chunk_size:
                chunks.append(paragraph[:max_chunk_size])
                paragraph = paragraph[max_chunk_size:]
            current_chunk = paragraph + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks

@router.message(Command("setkey"))
async def cmd_setkey(message: Message):
    if not is_authorized(message.from_user.id):
        return
    new_key = message.text[len("/setkey"):].strip()
    if not new_key:
        await message.answer(
            "ℹ️ *Использование:* `/setkey <твой_gemini_api_key>`\n\n"
            "Бесплатный ключ берется на [Google AI Studio](https://aistudio.google.com).",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        return

    cfg = config.load_config()
    cfg["gemini_api_key"] = new_key
    config.save_config(cfg)
    gemini_manager.reload_client()
    await message.answer("🔑 *Gemini API ключ успешно обновлен!*", parse_mode="Markdown")

# ОБРАБОТКА ФОТО И СКРИНШОТОВ
@router.message(F.photo)
async def handle_photo_message(message: Message, bot: Bot):
    if not is_authorized(message.from_user.id):
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status_msg = await message.answer("🔍 Анализирую изображение...")

    try:
        photo = message.photo[-1]
        photo_bytes_io = io.BytesIO()
        await bot.download(photo, destination=photo_bytes_io)
        photo_bytes = photo_bytes_io.getvalue()

        prompt = message.caption or "Что изображено на этом фото? Если здесь код или ошибка, объясни и предложи решение."
        reply = await gemini_manager.process_photo(message.from_user.id, photo_bytes, prompt=prompt)
        await status_msg.delete()

        chunks = split_text_into_chunks(reply)
        for chunk in chunks:
            try:
                await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                await message.answer(chunk)
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка анализа изображения: {e}")

# ОБРАБОТКА ГОЛОСОВЫХ СООБЩЕНИЙ
@router.message(F.voice)
async def handle_voice_message(message: Message, bot: Bot):
    if not is_authorized(message.from_user.id):
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status_msg = await message.answer("🎙 Слушаю голосовое...")

    try:
        voice_file = io.BytesIO()
        await bot.download(message.voice, destination=voice_file)
        audio_bytes = voice_file.getvalue()

        response_text = await gemini_manager.process_voice_message(message.from_user.id, audio_bytes, mime_type="audio/ogg")
        await status_msg.delete()

        chunks = split_text_into_chunks(response_text)
        for chunk in chunks:
            try:
                await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                await message.answer(chunk)
    except ValueError as ve:
        await status_msg.edit_text(f"⚠️ {ve}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка распознавания: {e}")

# ОБРАБОТКА ТЕКСТОВЫХ ЗАПРОСОВ (ANTIGRAVITY AI)
@router.message(F.text)
async def handle_text_message(message: Message, bot: Bot):
    if not is_authorized(message.from_user.id):
        return

    if message.text.startswith("/"):
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        reply = await gemini_manager.ask_gemini(message.from_user.id, message.text)
        chunks = split_text_into_chunks(reply)
        for chunk in chunks:
            try:
                await message.answer(chunk, parse_mode="Markdown")
            except Exception:
                await message.answer(chunk)
    except ValueError as ve:
        await message.answer(f"⚠️ {ve}", disable_web_page_preview=True)
    except Exception as e:
        await message.answer(f"❌ Ошибка Antigravity: {e}")
