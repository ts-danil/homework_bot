class API_error(Exception):
    """Ошибка при работе с API."""

    pass


class unexpected_response(Exception):
    """Отсутствуют ожидаемые ключи в ответе API."""

    pass


class unexpected_homework_status(Exception):
    """Недокументированный статус домашней работы."""

    pass
