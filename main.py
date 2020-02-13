import os
import json
import logging
import logging.config

from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import Filters

from config import config
from jobs import JOBS_CALLBACKS
import utils as u


def load_logging_config(config_file_path='logging.json'):
    with open(config_file_path, 'r') as f:
        logging_config = json.load(f)

    logging.config.dictConfig(logging_config)


logger = logging.getLogger(__name__)
load_logging_config()


@u.restricted
def delete_downloads(_, update):
    logger.info('cleaning download dir')

    files = [f for f in os.listdir('downloads/') if f != '.gitkeep']
    for f in files:
        os.remove(os.path.join('downloads', f))

    update.message.reply_text('Deleted {} files'.format(len(files)))


@u.restricted
def send_db(_, update):
    logger.info('sending_db')

    with open(config.database.filename, 'rb') as f:
        update.message.reply_document(f)


@u.restricted
def help_command(_, update):
    logger.info('help')

    commands = ['/del', '/db', '/start']

    update.message.reply_text('Commands: {}'.format(', '.join(commands)))


def main():
    updater = Updater(token=config.telegram.token, workers=config.telegram.run_async_workers)
    dispatcher = updater.dispatcher
    jobs = updater.job_queue

    logger.info('registering %d scheduled jobs', len(JOBS_CALLBACKS))
    for callback in JOBS_CALLBACKS:
        jobs.run_repeating(callback, interval=config.jobs.run_every, first=config.jobs.start_after)

    # dispatcher.add_handler(MessageHandler(~Filters.private & ~Filters.group & Filters.text, on_channel_post))
    dispatcher.add_handler(CommandHandler(['del'], delete_downloads, filters=Filters.private))
    dispatcher.add_handler(CommandHandler(['db'], send_db, filters=Filters.private))
    dispatcher.add_handler(CommandHandler(['start', 'help'], help_command, filters=Filters.private))

    logger.info('starting polling loop as @%s (run_async workers: %d)...', updater.bot.username, config.telegram.run_async_workers)
    updater.start_polling(clean=False)
    updater.idle()


if __name__ == '__main__':
    main()
