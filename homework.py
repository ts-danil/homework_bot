import logging
import os
import time
from asyncio.log import logger
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (API_error,
                        unexpected_homework_status,
                        unexpected_response)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(level=logging.DEBUG,
                    filename='main.log',
                    filemode='w',
                    format='%(asctime)s [%(levelname)s] %(message)s')


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
        error_text = (f'Сбой при работе с эндпоинт.'
                      f'API вернул {response.status_code}')
        logger.error(error_text)
        raise API_error(error_text)
    return response.json()


def send_message(bot, message):
    """
    Функция отправляет сообщение в Telegram чат.
    Принимает на вход экземпляр класса Bot и строку с текстом сообщения.
    Чат определяется переменной окружения TELEGRAM_CHAT_ID.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение удачно отправлено: {message}')
    except Exception:
        logger.error(f'Сообщение не отправлено: {message}')


def check_response(response):
    """
    Функция проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response['homeworks'], list):
        error_text = f'Отсутствуют ожидаемые ключи в ответе API: {response}'
        logger.error(error_text)
        raise unexpected_response(error_text)
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
    if homework_status not in HOMEWORK_STATUSES:
        error_text = (f'Недокументированный статус'
                      f'домашней работы: {homework_status}')
        logger.error(error_text)
        raise unexpected_homework_status(error_text)
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
            token = ''
            logger.critical('Отсутствует обязательная переменная')
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_error = ''
    it_run = check_tokens()
    while it_run:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if bool(homeworks):
                for homework in homeworks:
                    send_message(bot, parse_status(homework))
            else:
                logger.debug('Новые статусы отсутствуют')
            current_error = ''
            current_timestamp += RETRY_TIME
            time.sleep(RETRY_TIME)
        except Exception as error:
            if str(error) != current_error:
                current_error = str(error)
                send_message(bot, str(error))


if __name__ == '__main__':
    main()
