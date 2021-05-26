import logging
import os
import requests
import telegram
import time

from logging.handlers import RotatingFileHandler

PRAKTIKUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
YP_PATH = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
LOG_FILE = 'homework.log'


def parse_homework_status(homework):
    """Parse homework and return verdict."""
    homework_name = homework['homework_name']
    if homework['status'] == 'rejected':
        verdict = 'К сожалению в работе нашлись ошибки.'
    else:
        verdict = ('Ревьюеру всё понравилось, '
                   'можно приступать к следующему уроку.')
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homework_statuses(current_timestamp):
    headers = {
        'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'
    }
    params = {
        'from_date': current_timestamp
    }
    homework_statuses = requests.get(YP_PATH, params=params, headers=headers)
    return homework_statuses.json()


def send_message(message, bot_client):
    """Send message to telegram chat."""
    return bot_client.send_message(CHAT_ID, message)


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        filename=LOG_FILE,
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )

    logger = logging.getLogger(__name__)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=40960, backupCount=5)
    logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    logger.setLevel(logging.WARNING)

    current_timestamp = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                for homework in new_homework.get('homeworks'):
                    msg = parse_homework_status(homework)
                    logger.setLevel(logging.INFO)
                    send_message(msg, bot)
                    logger.info(f'Сообщение отправлено: {msg}')
                    logger.setLevel(logging.WARNING)
            current_timestamp = new_homework.get(
                'current_date', current_timestamp)
            time.sleep(300)

        except Exception as e:
            err_msg = f'Бот столкнулся с ошибкой: {e}'
            logging.exception(err_msg)
            bot.send_message(CHAT_ID, err_msg)
            time.sleep(20)


if __name__ == '__main__':
    main()
