import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

# Поддерживаем оба имени файла: .env и id.env
load_dotenv()
load_dotenv("id.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_ID: Optional[int] = int(ADMIN_CHAT_ID_RAW) if ADMIN_CHAT_ID_RAW else None

logging.basicConfig(level=logging.INFO)

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Счётчики"), KeyboardButton(text="🛠 Ремонт")],
        [KeyboardButton(text="🧳 Забытые вещи"), KeyboardButton(text="💸 Штраф")],
        [KeyboardButton(text="📝 Другое")],
    ],
    resize_keyboard=True,
)

CATEGORIES = {"📸 Счётчики", "🛠 Ремонт", "🧳 Забытые вещи", "💸 Штраф", "📝 Другое"}


async def send_reminder(bot: Bot, chat_id: int, delay_minutes: int, reminder_text: str) -> None:
    await asyncio.sleep(delay_minutes * 60)
    await bot.send_message(chat_id, f"⏰ Напоминание: {reminder_text}")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден. Укажи токен в .env или id.env, например:\n"
            "BOT_TOKEN=123456:ABC..."
        )

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(m: Message) -> None:
        await m.answer(
            "Привет! Выбери категорию и отправь сообщение/фото.\n"
            "Я перешлю это руководителю.\n"
            "Команда /myid покажет твой chat id.",
            reply_markup=kb,
        )
        logging.info("User id=%s chat_id=%s", m.from_user.id if m.from_user else None, m.chat.id)

    @dp.message(Command("myid"))
    async def my_id(m: Message) -> None:
        await m.answer(f"Твой chat_id: `{m.chat.id}`", parse_mode="Markdown")

    @dp.message(Command("remind"))
    async def remind(m: Message) -> None:
        # Формат: /remind 30 Проверить квартиру 12
        parts = (m.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await m.answer("Использование: /remind <минуты> <текст>\nПример: /remind 30 Проверить квартиру 12")
            return

        minutes = int(parts[1])
        if minutes < 1 or minutes > 24 * 60:
            await m.answer("Минуты должны быть в диапазоне 1..1440")
            return

        text = parts[2]
        asyncio.create_task(send_reminder(bot, m.chat.id, minutes, text))
        await m.answer(f"✅ Ок, напомню через {minutes} мин: {text}")

    @dp.message(F.text.in_(CATEGORIES))
    async def set_category(m: Message) -> None:
        if not m.from_user:
            return
        dp[f"category_{m.from_user.id}"] = m.text
        await m.answer(f"Ок, категория: {m.text}\nТеперь пришли текст и/или фото/видео/файл.")

    @dp.message()
    async def forward_to_admin(m: Message) -> None:
        if not m.from_user:
            return

        if ADMIN_CHAT_ID is None:
            await m.answer(
                "ADMIN_CHAT_ID пока не задан.\n"
                "1) Напиши /myid в чате руководителя с ботом\n"
                "2) Добавь значение в .env или id.env: ADMIN_CHAT_ID=<число>"
            )
            return

        category = dp.get(f"category_{m.from_user.id}", "📝 (без категории)")
        header = (
            "🔔 Новый отчёт\n"
            f"Категория: {category}\n"
            f"От: {m.from_user.full_name} (@{m.from_user.username or 'нет'})\n"
            f"UserID: {m.from_user.id}\n"
        )

        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=header)
        await m.forward(chat_id=ADMIN_CHAT_ID)
        await m.answer("✅ Отправлено руководителю.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())