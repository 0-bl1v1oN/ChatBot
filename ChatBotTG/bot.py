import asyncio
import logging
import os
from typing import Optional

try:
    from ChatBotTG.core import DraftReport, build_admin_header, parse_remind_command, parse_reports_command
except ModuleNotFoundError:
    # Позволяет запускать как `python bot.py` из папки ChatBotTG
    from core import DraftReport, build_admin_header, parse_remind_command, parse_reports_command

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile, KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

try:
    from ChatBotTG.storage import ReportStorage
except ModuleNotFoundError:
    from storage import ReportStorage



load_dotenv()
load_dotenv("id.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_ID: Optional[int] = int(ADMIN_CHAT_ID_RAW) if ADMIN_CHAT_ID_RAW else None
DB_PATH = os.getenv("REPORTS_DB_PATH", "reports.db")

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
    storage = ReportStorage(DB_PATH)
    storage.init_db()

    @dp.message(CommandStart())
    async def start(m: Message) -> None:
        await m.answer(
            "Привет! Выбери категорию отчёта.\n"
            "Дальше бот попросит код объекта и примет финальное сообщение (текст/фото/видео/файл).\n"
            "Команда /myid покажет твой chat id.",
            reply_markup=kb,
        )
        logging.info("User id=%s chat_id=%s", m.from_user.id if m.from_user else None, m.chat.id)

    @dp.message(Command("myid"))
    async def my_id(m: Message) -> None:
        await m.answer(f"Твой chat_id: `{m.chat.id}`", parse_mode="Markdown")

    @dp.message(Command("remind"))
    async def remind(m: Message) -> None:
        minutes, text, error = parse_remind_command(m.text or "")
        if error:
            await m.answer(f"{error}\nПример: /remind 30 Проверить квартиру 12")
            return

        asyncio.create_task(send_reminder(bot, m.chat.id, minutes, text))
        await m.answer(f"✅ Ок, напомню через {minutes} мин: {text}")

        @dp.message(Command("reports"))
    async def reports(m: Message) -> None:
        if ADMIN_CHAT_ID is None or m.chat.id != ADMIN_CHAT_ID:
            await m.answer("Команда доступна только руководителю.")
            return

        object_code, category, limit = parse_reports_command(m.text or "")
        items = storage.list_reports(object_code=object_code, category=category, limit=limit)
        if not items:
            await m.answer("Отчёты не найдены по заданным фильтрам.")
            return

        lines = ["📚 Последние отчёты:"]
        for row in items:
            lines.append(
                f"#{row['id']} | {row['created_at']} | {row['category']} | {row['object_code']} | {row['user_name']} (@{row['username'] or 'нет'})"
            )
        await m.answer("\n".join(lines))

    @dp.message(Command("export"))
    async def export_reports(m: Message) -> None:
        if ADMIN_CHAT_ID is None or m.chat.id != ADMIN_CHAT_ID:
            await m.answer("Команда доступна только руководителю.")
            return

        export_path = storage.export_csv("ChatBotTG/exports/reports.csv")
        await m.answer_document(document=FSInputFile(export_path), caption="Экспорт отчётов CSV")


    @dp.message(F.text.in_(CATEGORIES))
    async def set_category(m: Message) -> None:
        if not m.from_user:
            return

        dp[f"draft_{m.from_user.id}"] = DraftReport(category=m.text)
        await m.answer("Ок. Теперь введи код квартиры/объекта (например: KV-12).")

    @dp.message()
    async def collect_and_forward(m: Message) -> None:
        if not m.from_user:
            return

        if ADMIN_CHAT_ID is None:
            await m.answer(
                "ADMIN_CHAT_ID пока не задан.\n"
                "1) Напиши /myid в чате руководителя с ботом\n"
                "2) Добавь значение в .env или id.env: ADMIN_CHAT_ID=<число>"
            )
            return

        user_key = f"draft_{m.from_user.id}"
        draft: Optional[DraftReport] = dp.get(user_key)
        if not draft:
            await m.answer("Сначала выбери категорию через кнопки ниже.", reply_markup=kb)
            return

        if draft.object_code is None:
            if not m.text:
                await m.answer("Нужен код объекта текстом, например KV-12.")
                return

            draft.object_code = m.text.strip()
            dp[user_key] = draft
            await m.answer(
                "Отлично. Теперь отправь финальный отчёт: текст и/или фото/видео/файл.\n"
                "После отправки я сразу перешлю руководителю."
            )
            return

        header = build_admin_header(
            category=draft.category,
            object_code=draft.object_code,
            user_name=m.from_user.full_name,
            username=m.from_user.username or "",
            user_id=m.from_user.id,
        )

        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=header)
        await m.forward(chat_id=ADMIN_CHAT_ID)
        preview_text = (m.text or m.caption or "").strip()
        if len(preview_text) > 200:
            preview_text = preview_text[:200] + "..."

        storage.save_report(
            category=draft.category,
            object_code=draft.object_code,
            user_id=m.from_user.id,
            user_name=m.from_user.full_name,
            username=m.from_user.username or "",
            chat_id=m.chat.id,
            message_id=m.message_id,
            content_type=m.content_type,
            text_preview=preview_text,
        )

        await m.answer("✅ Отчёт отправлен руководителю и сохранён в базе.")
        dp.pop(user_key, None)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())