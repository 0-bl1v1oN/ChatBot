from pathlib import Path

from ChatBotTG.core import parse_reports_command
from ChatBotTG.storage import ReportStorage


def test_parse_reports_command_filters_and_limit():
    object_code, category, limit = parse_reports_command('/reports object=KV-12 category=📸Счётчики limit=100')
    assert object_code == 'KV-12'
    assert category == '📸Счётчики'
    assert limit == 50


def test_storage_save_list_and_export(tmp_path: Path):
    db_path = tmp_path / 'reports.db'
    storage = ReportStorage(str(db_path))
    storage.init_db()

    storage.save_report(
        category='📸 Счётчики',
        object_code='KV-12',
        user_id=1,
        user_name='Иван',
        username='ivan',
        chat_id=10,
        message_id=20,
        content_type='photo',
        text_preview='Показания отправлены',
    )

    rows = storage.list_reports(object_code='KV-12', category='📸 Счётчики', limit=10)
    assert len(rows) == 1
    assert rows[0]['object_code'] == 'KV-12'

    export_path = storage.export_csv(str(tmp_path / 'reports.csv'))
    content = Path(export_path).read_text(encoding='utf-8')
    assert 'object_code' in content
    assert 'KV-12' in content