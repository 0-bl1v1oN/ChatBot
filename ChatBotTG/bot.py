import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # сначала можно оставить пустым

logging.basicConfig(level=logging.INFO)

kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📸 Счётчики"), KeyboardButton(text="🛠 Ремонт")],
        [KeyboardButton(text="🧳 Забытые вещи"), KeyboardButton(text="💸 Штраф")],
        [KeyboardButton(text="📝 Другое")],
    ],
    resize_keyboard=True,
)

async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            "Привет! Выбери категорию и отправь сообщение/фото.\n"
            "Все будет отправлено руководителю.",
            reply_markup=kb,
        )
        # полезно для первого запуска: вывести chat_id
        logging.info(f"User {m.from_user.id=} chat_id={m.chat.id}")

    @dp.message(F.text.in_({"📸 Счётчики","🛠 Ремонт","🧳 Забытые вещи","💸 Штраф","📝 Другое"}))
    async def set_category(m: Message):
        # сохраняем категорию прямо в памяти (на время жизни процесса)
        dp["category_%s" % m.from_user.id] = m.text
        await m.answer(f"Ок, категория: {m.text}\nТеперь пришли текст и/или фото/видео/файл.")

    @dp.message()
    async def forward_to_admin(m: Message):
        # если админ не задан — просто подсказываем
        if not ADMIN_CHAT_ID:
            await m.answer("ADMIN_CHAT_ID пока не задан. Посмотри chat_id в консоли после /start.")
            return

        category = dp.get("category_%s" % m.from_user.id, "📝 (без категории)")
        header = (
            f"🔔 Новый отчёт\n"
            f"Категория: {category}\n"
            f"От: {m.from_user.full_name} (@{m.from_user.username or 'нет'})\n"
            f"UserID: {m.from_user.id}\n"
        )

        # Сначала отправим заголовок
        await bot.send_message(chat_id=int(ADMIN_CHAT_ID), text=header)

        # Потом пересылаем само сообщение (с фото/видео/файлами)
        await m.forward(chat_id=int(ADMIN_CHAT_ID))

        await m.answer("✅ Отправлено руководителю.")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())