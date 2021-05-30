import os
import requests
import time

import logging
import telegram

from logging.handlers import RotatingFileHandler

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
except Exception as e:
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

    verdict = RIGHT_STATUS_VERDICTS[hw_status]
    return f'У вас проверили работу "{hw_name}"! {verdict}'


def get_homework_statuses(current_timestamp):
    """Get all homework from current_timestamp date."""
    params = {
        'from_date': current_timestamp
    }
    try:
        homework_statuses = requests.get(
            YP_PATH, params=params, headers=HEADER)
    except Exception as e:
        logging.exception(f'Загрузка данных завершилась с ошибкой: {e}')
        return None
    return homework_statuses.json()


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
            homeworks = new_homework.get('homeworks')
            if homeworks is None:
                logging.info('Новых данных нет')
            else:
                for homework in reversed(homeworks):
                    msg = parse_homework_status(homework)
                    logging.info(f'Отправка сообщения {msg} в чат #{CHAT_ID}')
                    send_message(msg, bot)

            previous_timestamp = current_timestamp
            current_timestamp = new_homework.get(
                'current_date', current_timestamp)
            if current_timestamp is None:
                current_timestamp = previous_timestamp
            time.sleep(1200)
        except Exception as e:
            err_msg = f'Бот столкнулся с ошибкой: {e}'
            logging.exception(err_msg)
            send_message(err_msg, bot)
            time.sleep(20)


if __name__ == '__main__':
    main()
