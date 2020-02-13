import logging
import re
from copy import deepcopy

from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram import ParseMode
from telegram import Bot

from matrix import Matrix
from matrix import FakeMatrix

from config import config

logger = logging.getLogger(__name__)


class Sender:
    def __init__(self, telegram_bot=None, matrix_client=None):
        self._tgbot: Bot = telegram_bot
        self._matrix: [Matrix, FakeMatrix, None] = matrix_client if not isinstance(matrix_client, FakeMatrix) else None

        logger.info('Sender instance, telegram: %s, matrix: %s', bool(self._tgbot), bool(self._matrix))

        self._tg_kwargs = dict(
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            timeout=60
        )

    def send_message(self, repo, text, telegram=True, matrix=True, additional_telegram_kwargs: [None, dict] = None):
        sent_message_telegram, sent_message_matrix = None, None

        if repo.chat_id and self._tgbot and telegram:
            if config.jobs.github.test_chat_id:
                chat_id = config.jobs.github.test_chat_id
            else:
                chat_id = repo.chat_id

            kwargs = deepcopy(self._tg_kwargs)
            if additional_telegram_kwargs:
                for k, v in additional_telegram_kwargs.items():
                    kwargs[k] = v

            try:
                sent_message_telegram = self._tgbot.send_message(chat_id, text, **kwargs)
            except (BadRequest, TelegramError) as e:
                self._telegram_exception(e, text)
                return
        else:
            logger.info('(not posting on telegram)')

        if repo.get('room_id', None) and self._matrix and matrix:
            matrix_text = re.sub('\n', r'<br>', text.strip())  # replave \n with <br> and also strip original text
            # logger.info(matrix_text)

            try:
                sent_message_matrix = self._matrix.send_text_html(repo.room_id, matrix_text)
            except Exception as e:
                self._matrix_exception(e)
                return
        else:
            logger.info('(not posting on matrix)')

        return sent_message_telegram, sent_message_matrix

    def _telegram_exception(self, e: [BadRequest, TelegramError], text):
        if config.telegram.get('exceptions_log', None):
            chat_id = config.telegram
        else:
            chat_id = config.telegram.admins[0]

        logger.error('[tg] error while sending text: %s', e.message, exc_info=True)
        self._tgbot.send_message(chat_id, 'Error while sending message: {}'.format(e.message))
        self._tgbot.send_message(chat_id, text)

    def _matrix_exception(self, e):
        logger.error('[matrix] error while sending text: %s', str(e), exc_info=True)
