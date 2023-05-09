class ExceptionStatusError(Exception):
    """Класс исключения при не корректном статусе ответа."""

    def __init__(self, message):
        self.message = message


class ExceptionGetAPIError(Exception):
    """Класс исключения при ошибке запроса к API."""

    def __init__(self, message):
        self.message = message