import logging
import os
import sys
import time
from asyncio.log import logger
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiError, UnexpectedHomeworkStatus, UnexpectedResponse

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logging.StreamHandler(sys.stdout)


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
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise ApiError(f'Эндпоинт недоступен {ENDPOINT}')
    else:
        if response.status_code != HTTPStatus.OK:
            raise ApiError(f'Сбой при работе с эндпоинт.'
                           f'{response.reason}'
                           f'API вернул {response.status_code}'
                           f'Содержание ответа: {response.text}'
                           f'Параметры запроса: {params}')
        return response.json()


def send_message(bot, message):
    """
    Функция отправляет сообщение в Telegram чат.
    Принимает на вход экземпляр класса Bot и строку с текстом сообщения.
    Чат определяется переменной окружения TELEGRAM_CHAT_ID.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as e:
        logger.error(f'При отправке сообщения возникла ошибка {e}',
                     exc_info=True)
    else:
        logger.info(f'Сообщение удачно отправлено: {message}')


def check_response(response):
    """
    Функция проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API не является словарем.'
                        f'response: {response} Тип: {type(response)}')
    if 'homeworks' not in response:
        raise UnexpectedResponse(f'Ответ API не содержит домашних работ.'
                                 f'response: {response}')
    if not isinstance(response['homeworks'], list):
        raise UnexpectedResponse(f'Homeworks из ответа API не является списком'
                                 f' Тип значения homeworks: '
                                 f'{type(response["homeworks"])}')
    return response['homeworks']


def parse_status(homework):
    """
    Функция извлекает статус конкретной работы.
    В качестве параметра функция получает элемент из списка домашних работ.
    В случае успеха, функция возвращает строку для отправки в Telegram,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES
    """
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError(f'Отсутствуют ожидаемые ключи в homework. '
                       f'Homework: {homework}')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise UnexpectedHomeworkStatus(f'Недокументированный статус '
                                       f'домашней работы: {homework_status}')
    verdict = HOMEWORK_STATUSES.get(homework_status)
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
    return all(tokens)


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_error = ''
    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная')
        sys.exit()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if bool(homeworks):
                send_message(bot, parse_status(homeworks[-1]))
            else:
                logger.debug('Новые статусы отсутствуют')
            current_error = ''
            current_timestamp += RETRY_TIME
        except Exception as error:
            logger.error(error)
            if str(error) != current_error:
                current_error = str(error)
                send_message(bot, str(error))
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
