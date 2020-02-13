import logging
import datetime

import peewee

from config import config

logger = logging.getLogger(__name__)

db = peewee.SqliteDatabase(config.database.filename, pragmas={'journal_mode': 'wal'})


class Commit(peewee.Model):
    repository = peewee.CharField()
    sha = peewee.CharField(index=True)

    class Meta:
        table_name = 'Commits'
        primary_key = peewee.CompositeKey('repository', 'sha')
        database = db


class Release(peewee.Model):
    repository = peewee.CharField()
    release_id = peewee.IntegerField(index=True)
    post_id = peewee.IntegerField(null=True)
    added_on = peewee.DateTimeField(default=datetime.datetime.now, null=True)
    checked = peewee.BooleanField(default=False, null=True)
    sent = peewee.BooleanField(default=False, null=True)

    class Meta:
        table_name = 'Releases'
        primary_key = peewee.CompositeKey('repository', 'release_id')
        database = db


class ReleaseToSend(peewee.Model):
    repository = peewee.CharField()
    release_id = peewee.IntegerField(index=True)
    checked = peewee.BooleanField(default=False)  # whhether we already checked assets for a release
    sent = peewee.BooleanField(default=False)

    class Meta:
        table_name = 'ReleasesToSend'
        primary_key = peewee.CompositeKey('repository', 'release_id')
        database = db


class Asset(peewee.Model):
    release = peewee.ForeignKeyField(Release)
    added_on = peewee.DateTimeField(default=datetime.datetime.now)
    checked = peewee.BooleanField(default=False)
    sent = peewee.BooleanField(default=False)

    class Meta:
        table_name = 'Assets'
        database = db
