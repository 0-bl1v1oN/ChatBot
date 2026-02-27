from ChatBotTG.core import build_admin_header, parse_remind_command


def test_parse_remind_command_ok():
    minutes, text, error = parse_remind_command('/remind 30 Проверить квартиру 12')
    assert error is None
    assert minutes == 30
    assert text == 'Проверить квартиру 12'


def test_parse_remind_command_invalid_format():
    minutes, text, error = parse_remind_command('/remind xx text')
    assert minutes is None
    assert text is None
    assert 'Использование' in error


def test_parse_remind_command_out_of_range():
    minutes, text, error = parse_remind_command('/remind 2000 test')
    assert minutes is None
    assert text is None
    assert '1..1440' in error


def test_build_admin_header_contains_fields():
    header = build_admin_header('📸 Счётчики', 'KV-12', 'Иван', 'ivan', 123)
    assert 'Категория: 📸 Счётчики' in header
    assert 'Объект: KV-12' in header
    assert 'От: Иван (@ivan)' in header
    assert 'UserID: 123' in header
    assert 'Время:' in header