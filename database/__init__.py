from peewee import DoesNotExist

from .models import db
from .models import Commit
from .models import Release


def create_tables():
    with db:
        db.create_tables([Commit, Release])


create_tables()
