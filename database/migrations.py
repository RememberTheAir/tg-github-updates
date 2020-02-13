import logging
import argparse
import sys
import os
import datetime

import peewee
import sqlite3
from playhouse.migrate import *


logging.basicConfig(format='[%(asctime)s][%(name)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()


def main(db_filename):
	db = peewee.SqliteDatabase(db_filepath, pragmas={'journal_mode': 'wal'})

	migrator = SqliteMigrator(db)

	added_on = peewee.DateTimeField(default=datetime.datetime.now, null=True)
	post_id = peewee.IntegerField(null=True)
	checked = peewee.BooleanField(default=False, null=True)
	sent = peewee.BooleanField(default=False, null=True)

	logger.info('Starting migration....')

	try:
		migrate(
			migrator.add_column('Releases', 'added_on', added_on),
			migrator.add_column('Releases', 'post_id', post_id),
		    migrator.add_column('Releases', 'checked', checked),
		    migrator.add_column('Releases', 'sent', sent)
		)
	except (peewee.DatabaseError, sqlite3.DatabaseError):
		print('database file {} is encrypted or is not a database'.format(db_filepath))
		sys.exit(1)

	logger.info('...migration completed')


if __name__ == '__main__':
	parser.add_argument("-db", "--database", action="store",
		help="Database file path")

	args = parser.parse_args()
	if not args.database:
		print('pass a db filename using the -db [file path] argument')
		sys.exit(1)

	db_filepath = os.path.normpath(args.database)
	if not os.path.isfile(db_filepath):
		print('{} does not exist or is a directory'.format(db_filepath))
		sys.exit(1)

	main(db_filepath)
