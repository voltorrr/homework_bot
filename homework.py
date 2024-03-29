import logging
import os
import sys
import time
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from exceptions import (ExceptionGetAPIError,
                        ExceptionStatusError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('HOMEWORK_TOKEN')
TELEGRAM_TOKEN = os.getenv('TGRM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Успешная отправка сообщения.')
    except Exception as error:
        raise SystemError(f'Не отправляются сообщения, {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': params
    }
    logger.info(f"Запрос к эндпоинту '{ENDPOINT}' API-сервиса c "
                f"параметрами {requests_params}")
    try:
        response = requests.get(**requests_params)
        if response.status_code != HTTPStatus.OK:
            message = (f"Сбой в работе программы: Эндпоинт {ENDPOINT} c "
                       f"параметрами {requests_params} недоступен. status_code"
                       f": {response.status_code}, reason: {response.reason}, "
                       f"text: {response.text}")
            raise ExceptionStatusError(message)
    except Exception as error:
        raise ExceptionGetAPIError(
            f"Cбой при запросе к энпоинту '{ENDPOINT}' API-сервиса с "
            f"параметрами {requests_params}."
            f"Error: {error}")
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info("Проверка ответа API на корректность")
    if not isinstance(response, dict):
        message = (f"Ответ API получен в виде {type(response)}, "
                   "а должен быть словарь")
        raise TypeError(message)
    keys = ['current_date', 'homeworks']
    for key in keys:
        if key not in response:
            message = f"В ответе API нет ключа {key}"
            raise KeyError(message)
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        message = (f"API вернул {type(homework)} под ключом homeworks, "
                   "а должен быть список")
        raise TypeError(message)
    return homework


def parse_status(homework):
    """Извлекает из конкретной домашней работы статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    old_message = ''
    if not check_tokens():
        message = 'Отсутствуют необходимые переменные окружения'
        logger.critical(message)
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                verdict_status = parse_status(homework)
                if verdict_status != old_message:
                    send_message(bot, verdict_status)
                    old_message = verdict_status
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != old_message:
                bot.send_message(TELEGRAM_CHAT_ID, message)
                old_message = message
        finally:
            current_timestamp = int(time.time())
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
