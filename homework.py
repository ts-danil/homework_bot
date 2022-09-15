import os

from dotenv import load_dotenv
from http import HTTPStatus
import logging
from logging import StreamHandler
import requests
import telegram
import time
import sys

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 3
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """
    Функция отправляет сообщение в Telegram чат.
    Принимает на вход экземпляр класса Bot и строку с текстом сообщения.
    Чат определяется переменной окружения TELEGRAM_CHAT_ID.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение: "{message}".')
    except Exception as error:
        error_text = f'Сбой при отправке сообщения "{message}". Ошибка: {error}.'
        logger.error(error_text)
        raise Exception(error_text)


def get_api_answer(current_timestamp):
    """
    Функция делает запрос к API.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса возвращает ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise
        return response.json()
    except Exception as error:
        error_text = f'Эндпоинт {ENDPOINT} недоступен. Код ответа API: {response.status_code}. Ошибка: {error}.'
        logger.error(error_text)
        raise Exception(error_text)


def check_response(response):
    """
    Функция проверяет ответ API на корректность.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    try:
        if not isinstance(response, dict) or not isinstance(response['homeworks'], list):
            raise
        if not response.keys() & {'homeworks', 'current_date'}:
            raise
        return response['homeworks']
    except Exception as error:
        error_text = f'Отсутствуют ожидаемые ключи в ответе API. Ответ: {response}. Ошибка: {error}'
        logger.error(error_text)
        raise Exception(error_text)


def parse_status(homework):
    """
    Функция извлекает статус конкретной работы.
    В качестве параметра функция получает элемент из списка домашних работ.
    В случае успеха, функция возвращает строку для отправки в Telegram,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES
    """
    try:
        if 'homework_name' not in homework:
            raise Exception('Не найдено имя домашней работы.')
        homework_name = homework['homework_name']
        homework_status = homework['status']
        if homework_status not in HOMEWORK_STATUSES:
            raise Exception(f'Недокументированный статус домашней работы: {homework_status}.')
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        error_text = f'Недокументированный статус домашней работы: {homework}.'
        logger.error(error_text)
        raise Exception(error_text)


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
            logger.critical(f'Отсутствует обязательная переменная окружения: {token}. Программа принудительно остановлена.')
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_timestamp = 1660188682
    current_error = ''
    if check_tokens():
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if homeworks:
                    for homework in homeworks:
                        status = parse_status(homework)
                        send_message(bot, status)
                else:
                    print(current_timestamp)
                    logger.debug('Новые статусы отсутствуют')
                current_timestamp += RETRY_TIME
                current_error = ''
                time.sleep(RETRY_TIME)
            except Exception as error:
                if str(error) != current_error:
                    current_error = str(error)
                    message = f'Сбой в работе программы: {error}'
                    send_message(bot, message)
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
