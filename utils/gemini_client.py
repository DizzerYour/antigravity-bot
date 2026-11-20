import asyncio
import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

import config

ANTIGRAVITY_SYSTEM_PROMPT = (
    "Ты — Antigravity, мощный персональный AI-ассистент разработчика от Google DeepMind, "
    "работающий для своего пользователя на его смартфоне (OPPO Reno 14) и синхронизированный с его проектами.\n\n"
    "Твоя задача — быть полноценным мобильным AI-напарником и вторым пилотом, в точности как веб-версия Antigravity:\n"
    "1. 💡 РЕШЕНИЕ ЗАДАЧ И КОДИНГ: пиши чистый, современный, рабочий код на любых языках (Python, Dart/Flutter, JavaScript, TypeScript, C++, Go, PowerShell, Bash и др.). Обязательно объясняй логику и оформляй код в markdown-блоках с указанием языка.\n"
    "2. 🧠 АНАЛИЗ И АРХИТЕКТУРА: помогай проектировать приложения, базы данных, API, искать баги в логике, оптимизировать производительность и автономность устройств.\n"
    "3. 🖼 МУЛЬТИМОДАЛЬНОСТЬ: если пользователь присылает фото или скриншот (ошибки в коде, схемы, задачи, интерфейсы) — внимательно изучай изображение и давай точное решение.\n"
    "4. 🎙 ГОЛОСОВОЙ РЕЖИМ: на голосовые сообщения отвечай емко, по делу и информативно.\n"
    "5. 🤝 ХАРАКТЕР: дружелюбный, уверенный, технически эрудированный, с легким бро-вайбом (газз, кент, кайф, братуха — когда уместно), всегда готов помочь до победного конца."
)

AVAILABLE_MODELS = {
    "gemini-3.5-flash-lite": {
        "title": "⚡ Gemini 3.5 Flash Lite",
        "desc": "Ультрабыстрая, мгновенные ответы, идеальна для смартфона"
    },
    "gemini-3.5-flash": {
        "title": "⚖️ Gemini 3.5 Flash",
        "desc": "Сбалансированная модель для сложных алгоритмов и архитектуры"
    },
    "gemini-3.8-flash": {
        "title": "🚀 Gemini 3.8 Flash",
        "desc": "Новейшая модель с глубокими рассуждениями"
    },
    "gemini-3.1-flash-lite": {
        "title": "💡 Gemini 3.1 Flash Lite",
        "desc": "Стабильная легковесная модель"
    }
}

class GeminiAntigravityManager:
    def __init__(self):
        self._client: Optional[genai.Client] = None
        self._chats: Dict[int, Any] = {}
        self._user_models: Dict[int, str] = {}

    def get_client(self) -> genai.Client:
        api_key = config.get_gemini_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API ключ не настроен!\n"
                "Получи его бесплатно в Google AI Studio: https://aistudio.google.com "
                "и укажи командой /setkey."
            )
        if self._client is None:
            proxy = config.get_proxy()
            http_opts = None
            if proxy:
                http_opts = types.HttpOptions(client_args={"proxy": proxy})
                os.environ["HTTP_PROXY"] = proxy
                os.environ["HTTPS_PROXY"] = proxy
            self._client = genai.Client(api_key=api_key, http_options=http_opts)
        return self._client

    def reload_client(self):
        self._client = None
        self._chats.clear()

    def get_user_model(self, user_id: int) -> str:
        return self._user_models.get(user_id, config.get_gemini_model())

    def set_user_model(self, user_id: int, model_name: str) -> None:
        if model_name in AVAILABLE_MODELS:
            self._user_models[user_id] = model_name
            # Сбрасываем чат для пересоздания с новой моделью
            if user_id in self._chats:
                del self._chats[user_id]

    def get_or_create_chat(self, user_id: int):
        if user_id not in self._chats:
            client = self.get_client()
            model_name = self.get_user_model(user_id)
            cfg = types.GenerateContentConfig(
                system_instruction=ANTIGRAVITY_SYSTEM_PROMPT,
                temperature=0.7,
            )
            chat = client.chats.create(model=model_name, config=cfg)
            self._chats[user_id] = chat
        return self._chats[user_id]

    def clear_chat(self, user_id: int):
        if user_id in self._chats:
            del self._chats[user_id]

    async def ask_gemini(self, user_id: int, prompt: str) -> str:
        """Отправляет текстовый запрос в сессию диалога с Antigravity."""
        def _call_sync():
            chat = self.get_or_create_chat(user_id)
            resp = chat.send_message(prompt)
            return resp.text or "Пустой ответ."

        return await asyncio.to_thread(_call_sync)

    async def process_photo(self, user_id: int, photo_bytes: bytes, prompt: str, mime_type: str = "image/jpeg") -> str:
        """Анализирует фото/скриншот и отвечает на вопрос пользователя."""
        def _call_sync():
            client = self.get_client()
            model_name = self.get_user_model(user_id)
            image_part = types.Part.from_bytes(data=photo_bytes, mime_type=mime_type)
            text_prompt = prompt.strip() if prompt else "Проанализируй это изображение и дай подробный ответ."
            cfg = types.GenerateContentConfig(
                system_instruction=ANTIGRAVITY_SYSTEM_PROMPT,
                temperature=0.7,
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=[image_part, text_prompt],
                config=cfg
            )
            return resp.text or "Не удалось распознать изображение."

        return await asyncio.to_thread(_call_sync)

    async def process_voice_message(self, user_id: int, audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
        """Обрабатывает голосовое сообщение (транскрипция + развернутый ответ)."""
        def _call_sync():
            client = self.get_client()
            model_name = self.get_user_model(user_id)
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
            instruction = (
                "Пользователь надиктовал голосовое сообщение с телефона.\n"
                "1. Сначала в первой строке напиши: 🎙 *Вы сказали:* \"[точная транскрипция слов пользователя]\"\n"
                "2. Затем с новой строки дай развернутый, полезный и точный ответ на его вопрос или запрос от лица Antigravity."
            )
            cfg = types.GenerateContentConfig(
                system_instruction=ANTIGRAVITY_SYSTEM_PROMPT,
                temperature=0.7,
            )
            resp = client.models.generate_content(
                model=model_name,
                contents=[audio_part, instruction],
                config=cfg
            )
            return resp.text or "Не удалось обработать аудио."

        return await asyncio.to_thread(_call_sync)

gemini_manager = GeminiAntigravityManager()
