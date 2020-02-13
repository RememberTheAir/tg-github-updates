import logging

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixHttpApi

from config import config

logger = logging.getLogger(__name__)

# room_id = "!MZJhJgkhKDpxLvTxXe:matrix.org"


class MsgType:
    # https://matrix.org/docs/spec/r0.0.1/client_server.html#m-room-message-msgtypes
    TEXT = 'm.text'
    EMOTE = 'm.emote'
    NOTICE = 'm.notice'
    IMAGE = 'm.image'
    FILE = 'm.file'
    LOCATION = 'm.location'
    VIDEO = 'm.video'
    AUDIO = 'm.audio'


class Matrix:
    def __init__(self):
        logger.info('logging in to Matrix as %s', config.matrix.username)

        self._client = MatrixClient(config.matrix.server)
        self._token = self._client.login(username=config.matrix.username, password=config.matrix.password, sync=False)
        self._api = MatrixHttpApi(config.matrix.server, self._token)

    def send_text(self, room_id, text):
        self._api.send_message(room_id, text)

    def send_notice_html(self, room_id, text):
        content = dict(
            body=text,
            format='org.matrix.custom.html',
            formatted_body=text,
            msgtype=MsgType.NOTICE
        )

        self._api.send_message_event(room_id, event_type='m.room.message', content=content)

    def send_text_html(self, room_id, text):
        content = dict(
            body=text,
            format='org.matrix.custom.html',
            formatted_body=text,
            msgtype=MsgType.TEXT
        )

        self._api.send_message_event(room_id, event_type='m.room.message', content=content)

    def send_notice(self, room_id, text):
        self._api.send_notice(room_id, text)


class FakeMatrix:
    def __init__(self, *args, **kwargs):
        pass
