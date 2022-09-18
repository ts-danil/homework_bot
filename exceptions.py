class ApiError(Exception):
    """Ошибка при работе с API."""

    pass


class UnexpectedResponse(Exception):
    """Отсутствуют ожидаемые ключи в ответе API."""

    pass


class UnexpectedHomeworkStatus(Exception):
    """Недокументированный статус домашней работы."""

    pass
