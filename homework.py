import os
import logging
import time
from json.decoder import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
import telegram

LOG_FILE = os.path.join(os.path.expanduser('~'), 'homework.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
    handlers=[
        RotatingFileHandler(
            filename=LOG_FILE,
            maxBytes=65535,
            backupCount=3
        ),
    ]
)

try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except KeyError as e:
    err_msg = f'Ошибка - переменная среды {e} не установлена!'
    logging.exception(err_msg)
    exit(err_msg)

HEADER = {
    'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'
}

YP_PATH = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'

RIGHT_STATUS_VERDICTS = {
    'rejected': 'К сожалению в работе нашлись ошибки.',
    'approved': ('Ревьюеру всё понравилось, '
                 'можно приступать к следующему уроку.'),
    'reviewing': 'Ваша работа всё ещё проверяется.',
}

# Если добавлять "У вас проверили работу в этот словарь", то тесты ругаются.
# Они проверяют соответствие строке.
WRONG_VERDICTS = {
    'wrong_data': 'Неверный ответ сервера. Данные отсутствуют.',
    'wrong_status': ('Статус в ответе от сервера не совпадает с необходимыми.'
                     'Уточните спецификации API.')
}


def parse_homework_status(homework):
    """Parse homework and return verdict."""
    hw_name = homework.get('homework_name')
    hw_status = homework.get('status')

    if hw_name is None or hw_status is None:
        verdict = WRONG_VERDICTS['wrong_data']
        logging.error(verdict)
        return verdict

    if hw_status not in RIGHT_STATUS_VERDICTS:
        verdict = WRONG_VERDICTS['wrong_status']
        logging.error(verdict)
        return verdict

    # решил вынести в отдельную проверку, чтобы не ругались тесты.
    if hw_status == 'reviewing':
        return RIGHT_STATUS_VERDICTS['reviewing']

    verdict = RIGHT_STATUS_VERDICTS[hw_status]
    return f'У вас проверили работу "{hw_name}"! {verdict}'


def get_homework_statuses(current_timestamp):
    """Get all homeworks from current_timestamp date."""
    params = {
        'from_date': current_timestamp
    }
    try:
        homework_statuses = requests.get(
            YP_PATH, params=params, headers=HEADER)
        hw_statuses = homework_statuses.json()
    except (requests.exceptions.HTTPError,
            JSONDecodeError) as err:
        err_msg = f'Загрузка данных завершилась с ошибкой: {err}'
        logging.exception(err_msg)
        return None
    return hw_statuses


def send_message(message, bot_client):
    """Send message to CHAT_ID telegram chat."""
    return bot_client.send_message(text=message, chat_id=CHAT_ID)


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    logging.debug('Запуск бота...')
    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework is not None:
                homeworks = new_homework.get('homeworks')
                # homeworks разворачивается потому, что в homeworks
                # работы идут от последней к первой.
                # Ситуация, когда работ будет много - тестовая,
                # когда from_date принимает значение даты до начала
                # отправки заданий или 0, т.е. за всё время.
                # Второй вариант - когда на сайте практикума
                # сломался API и не отдаёт какое-то время json
                for homework in reversed(homeworks):
                    msg = parse_homework_status(homework)
                    logging.info(f'Отправка сообщения {msg} в чат #{CHAT_ID}')
                    send_message(msg, bot)

                current_timestamp = new_homework.get(
                    'current_date', current_timestamp) or current_timestamp
            time.sleep(1200)
        except Exception as e:
            err_msg = f'Бот столкнулся с ошибкой: {e}'
            logging.exception(err_msg)
            send_message(err_msg, bot)
            time.sleep(20)


if __name__ == '__main__':
    main()
