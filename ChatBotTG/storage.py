import csv
import sqlite3
from pathlib import Path
from typing import Optional


class ReportStorage:
    def __init__(self, db_path: str = "reports.db") -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    category TEXT NOT NULL,
                    object_code TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    username TEXT,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    content_type TEXT NOT NULL,
                    text_preview TEXT
                )
                """
            )

    def save_report(
        self,
        *,
        category: str,
        object_code: str,
        user_id: int,
        user_name: str,
        username: str,
        chat_id: int,
        message_id: int,
        content_type: str,
        text_preview: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO reports (
                    category, object_code, user_id, user_name, username,
                    chat_id, message_id, content_type, text_preview
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category,
                    object_code,
                    user_id,
                    user_name,
                    username,
                    chat_id,
                    message_id,
                    content_type,
                    text_preview,
                ),
            )

    def list_reports(
        self,
        *,
        object_code: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        where: list[str] = []
        params: list = []

        if object_code:
            where.append("object_code = ?")
            params.append(object_code)
        if category:
            where.append("category = ?")
            params.append(category)

        query = "SELECT id, created_at, category, object_code, user_name, username, content_type, text_preview FROM reports"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 50)))

        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(query, tuple(params)).fetchall()

        return [dict(row) for row in rows]

    def export_csv(self, file_path: str) -> str:
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "id",
            "created_at",
            "category",
            "object_code",
            "user_id",
            "user_name",
            "username",
            "chat_id",
            "message_id",
            "content_type",
            "text_preview",
        ]

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        return str(path)