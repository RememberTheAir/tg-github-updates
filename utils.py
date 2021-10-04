import logging
import os
import hashlib
import urllib3
from functools import wraps
from html import escape

from telegram import ParseMode

from config import config

urllib3.disable_warnings()

logger = logging.getLogger(__name__)

BUF_SIZE = 65536  # needed to calculate hashes: read files in 64kb chunks


def get_md5_sha1(file_path):
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
            sha1.update(data)

    return md5.hexdigest(), sha1.hexdigest()


def download_to_file(url, file_name):
    connection_pool = urllib3.PoolManager()
    resp = connection_pool.request('GET', url)

    file_path = os.path.join('downloads', file_name)
    with open(file_path, 'wb') as f:
        f.write(resp.data)

    resp.release_conn()

    return file_path


def bs_find_first(soup, tag_to_find):
    for link in soup.find_all(tag_to_find):
        url = link.get('href')
        if url and "rink.hockeyapp.net/api/2/apps" in url:
            return url


def restricted(func):
    @wraps(func)
    def wrapped(bot, update, *args, **kwargs):
        if update.effective_user.id not in config.telegram.admins:
            update.message.reply_text("You can't use this command")
            return

        return func(bot, update, *args, **kwargs)

    return wrapped


def logerrors(func):
    @wraps(func)
    def wrapped(bot, job, *args, **kwargs):
        try:
            return func(bot, job, *args, **kwargs)
        except Exception as e:
            logger.error('error while running job: %s', str(e), exc_info=True)
            text = 'An error occurred while running a job: <code>{}</code>'.format(escape(str(e)))
            bot.send_message(config.telegram.admins[0], text, parse_mode=ParseMode.HTML)

    return wrapped
