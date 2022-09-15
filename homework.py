from http import HTTPStatus
import os

from dotenv import load_dotenv
import logging
from logging import StreamHandler
import requests
import telegram
import time
import sys

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 3
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class API_respond_not_200(Exception):
    pass


class homeworks_not_list(Exception):
    pass


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def get_api_answer(current_timestamp):
    """
    Функция делает запрос к API.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise API_respond_not_200(f'API вернул {response.status_code}')
    return response.json()


def send_message(bot, message):
    """
    Функция отправляет сообщение в Telegram чат.
    Принимает на вход экземпляр класса Bot и строку с текстом сообщения.
    Чат определяется переменной окружения TELEGRAM_CHAT_ID.
    """
    bot.send_message(TELEGRAM_CHAT_ID, message)


def check_response(response):
    """
    Функция проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response['homeworks'], list):
        raise homeworks_not_list('домашки приходят не в виде списка в ответ от API')
    return response['homeworks']


def parse_status(homework):
    """
    Функция извлекает статус конкретной работы.
    В качестве параметра функция получает элемент из списка домашних работ.
    В случае успеха, функция возвращает строку для отправки в Telegram,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Функция проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения,
    необходимая для работы программы — функция возвращает False, иначе — True.
    """
    tokens = (PRACTICUM_TOKEN,
              TELEGRAM_TOKEN,
              TELEGRAM_CHAT_ID)
    for token in tokens:
        if bool(token) is False:
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_timestamp = 1660188682
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                status = parse_status(homework)
                send_message(bot, status)
            current_timestamp += RETRY_TIME
            time.sleep(RETRY_TIME)
        except Exception as error:
            print(error)


if __name__ == '__main__':
    main()
