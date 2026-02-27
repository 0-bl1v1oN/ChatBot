from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DraftReport:
    category: str
    object_code: Optional[str] = None


def parse_remind_command(text: str) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Returns (minutes, reminder_text, error_message)."""
    parts = (text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        return None, None, "Использование: /remind <минуты> <текст>"

    minutes = int(parts[1])
    if minutes < 1 or minutes > 24 * 60:
        return None, None, "Минуты должны быть в диапазоне 1..1440"

    return minutes, parts[2], None


def build_admin_header(category: str, object_code: str, user_name: str, username: str, user_id: int) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        "🔔 Новый отчёт\n"
        f"Категория: {category}\n"
        f"Объект: {object_code}\n"
        f"От: {user_name} (@{username or 'нет'})\n"
        f"UserID: {user_id}\n"
        f"Время: {timestamp}"
    )



def parse_reports_command(text: str) -> tuple[Optional[str], Optional[str], int]:
    """Парсит /reports [object=<код>] [category=<категория>] [limit=<n>]."""
    object_code = None
    category = None
    limit = 10

    parts = (text or "").split()[1:]
    for part in parts:
        if part.startswith("object="):
            object_code = part.split("=", 1)[1].strip() or None
        elif part.startswith("category="):
            category = part.split("=", 1)[1].strip() or None
        elif part.startswith("limit="):
            raw = part.split("=", 1)[1].strip()
            if raw.isdigit():
                limit = int(raw)

    limit = max(1, min(limit, 50))
    return object_code, category, limit