#!/usr/bin/env python3
import dateutil.parser
import logging
import pytz
import time
from celery import Celery
from datetime import datetime

logging.basicConfig(format='[%(asctime)s.%(msecs)03d] Function "%(funcName)s" from module "%(module)s" says: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
        include=[app.import_name]
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def timezone_aware(datetime_str, timezone_str):
    dt = dateutil.parser.parse(datetime_str)
    utc_based = pytz.timezone('UTC')
    tz_based = pytz.timezone(timezone_str)
    timestamp = utc_based.localize(dt).astimezone(tz_based)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")


def get_datetime(run_at, timezone_str):
    utc_based = pytz.timezone('UTC')
    tz_based = pytz.timezone(timezone_str)
    now = utc_based.localize(datetime.now()).astimezone(tz_based)
    schedule = dict(enumerate(run_at.split('-')[::-1]))
    second = int(schedule.get(0, now.second))
    minute = int(schedule.get(1, now.minute))
    hour = int(schedule.get(2, now.hour))
    day = int(schedule.get(3, now.day))
    month = int(schedule.get(4, now.month))
    year = int(schedule.get(5, now.year))
    return datetime(year, month, day, hour, minute, second)


def counter(count_until=10):
    count = 0
    status = 'Still counting...'
    while count < count_until:
        time.sleep(1)
        count += 1
        logging.info(f'{count}/{count_until}')
    status = 'Counting completed!'
    return status
