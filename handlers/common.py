from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import config
from utils.gemini_client import gemini_manager, AVAILABLE_MODELS

router = Router()

def is_authorized(user_id: int) -> bool:
    allowed_id = config.get_allowed_user_id()
    if allowed_id == 0:
        return True
    return user_id == allowed_id

def get_models_keyboard(current_model: str) -> InlineKeyboardMarkup:
    buttons = []
    for model_id, info in AVAILABLE_MODELS.items():
        is_active = (model_id == current_model)
        mark = " ✅" if is_active else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{info['title']}{mark}",
                callback_data=f"set_model:{model_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def handle_start(message: Message):
    user_id = message.from_user.id
    allowed_id = config.get_allowed_user_id()

    if allowed_id == 0:
        config.set_allowed_user(user_id)
        allowed_id = user_id

    if user_id != allowed_id:
        await message.answer("⛔ Доступ ограничен. Этот бот настроен для персонального использования владельцем.")
        return

    current_model = gemini_manager.get_user_model(user_id)
    model_title = AVAILABLE_MODELS.get(current_model, {}).get("title", current_model)

    welcome_text = (
        "🌌 *Салют! Я твой персональный AI-ассистент Antigravity.*\n\n"
        f"🤖 *Текущая модель:* `{model_title}`\n\n"
        "Теперь я всегда с тобой в кармане на телефоне. Ты можешь обращаться ко мне с любыми вопросами точно так же, как в IDE:\n\n"
        "💻 *Чем я могу помочь:*\n"
        "• **Программирование:** пиши любые задачи — напишу, исправлю, отлажу или объясню код на Python, Dart/Flutter, JS/TS, C++, Go, SQL и др.\n"
        "• **Архитектура и логика:** проектирование баз данных, подбор библиотек, поиск узких мест и алгоритмических решений.\n"
        "• **Мультимодальность:** присылай скриншоты ошибок, фото схем или кода — я разберу и дам готовое решение.\n"
        "• **Голосовой ввод:** надиктовывай голосовые сообщения на ходу — я внимательно слушаю и даю развернутый ответ.\n\n"
        "Задавай любой вопрос или выбери модель кнопкой ниже 👇"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧠 Выбрать модель AI", callback_data="open_model_picker"),
                InlineKeyboardButton(text="✨ Новый диалог", callback_data="reset_chat"),
            ]
        ]
    )

    await message.answer(welcome_text, reply_markup=kb, parse_mode="Markdown")

@router.message(Command("model"))
@router.message(Command("models"))
async def cmd_models(message: Message):
    if not is_authorized(message.from_user.id):
        return
    current = gemini_manager.get_user_model(message.from_user.id)
    text = (
        "🧠 *Выбор модели искусственного интеллекта:*\n\n"
        "Выбери подходящую модель под твои текущие задачи:\n\n"
        "• *Gemini 3.5 Flash Lite* — мгновенные ответы, идеальна для диалога и быстрых задач на смартфоне (по умолчанию).\n"
        "• *Gemini 3.5 Flash* — сбалансированная модель для более глубоких алгоритмов и архитектуры.\n"
        "• *Gemini 3.8 Flash* — флагманская новейшая Flash-модель со сложными рассуждениями.\n"
        "• *Gemini 3.1 Flash Lite* — стабильная легкая модель."
    )
    await message.answer(text, reply_markup=get_models_keyboard(current), parse_mode="Markdown")

@router.callback_query(F.data == "open_model_picker")
async def cb_open_model_picker(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    current = gemini_manager.get_user_model(callback.from_user.id)
    text = "🧠 *Выбери активную модель AI:*"
    await callback.message.answer(text, reply_markup=get_models_keyboard(current), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("set_model:"))
async def cb_set_model(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    model_id = callback.data.split(":", 1)[1]
    gemini_manager.set_user_model(callback.from_user.id, model_id)
    model_info = AVAILABLE_MODELS.get(model_id, {})
    title = model_info.get("title", model_id)

    await callback.message.edit_reply_markup(reply_markup=get_models_keyboard(model_id))
    await callback.answer(f"Выбрана модель: {title}")
    await callback.message.answer(
        f"✅ *Модель переключена на {title}!* 🚀\n"
        f"Диалог перезапущен с новой моделью. Жду твой вопрос!",
        parse_mode="Markdown"
    )

@router.message(Command("new"))
@router.message(Command("clear"))
async def handle_new_chat(message: Message):
    if not is_authorized(message.from_user.id):
        return
    gemini_manager.clear_chat(message.from_user.id)
    await message.answer("✨ *Контекст диалога очищен!* Я готов к новой теме или задаче.", parse_mode="Markdown")

@router.callback_query(F.data == "reset_chat")
async def cb_reset_chat(callback: CallbackQuery):
    if not is_authorized(callback.from_user.id):
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    gemini_manager.clear_chat(callback.from_user.id)
    await callback.message.answer("✨ *Новый диалог начат.* О чем поговорим?", parse_mode="Markdown")
    await callback.answer("Диалог сброшен")

@router.message(Command("help"))
async def handle_help(message: Message):
    if not is_authorized(message.from_user.id):
        return

    help_text = (
        "💡 *Возможности Antigravity AI:*\n\n"
        "• **Обычный чат:** пиши вопросы по разработке, учебе, кодингу, оптимизации или идеям.\n"
        "• **Голосовые сообщения:** просто зажми микрофон в Telegram и надиктуй вопрос.\n"
        "• **Фото и скриншоты:** отправь изображение с подписью — я проанализирую код, схему или ошибку.\n"
        "• `/model` — переключить активную модель AI (3.5 Flash Lite, 3.5 Flash, 3.8 Flash, 3.1 Flash Lite).\n"
        "• `/new` — начать новый диалог (сбросить историю беседы).\n"
        "• `/setkey <api_key>` — обновить Gemini API ключ прямо в чате."
    )
    await message.answer(help_text, parse_mode="Markdown")
