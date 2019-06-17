#!/usr/bin/env python3
import json
import logging
import os
import redis
from flask import Flask, jsonify
from flask_restplus import Api, Resource
from pytz import timezone
from utils import make_celery, timezone_aware, get_datetime, counter
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.config.update(
    CELERY_BROKER_URL='redis://broker:6379',
    CELERY_RESULT_BACKEND='redis://broker:6379',
    CELERY_ENABLE_UTC='True'
)
celery = make_celery(app)

# CONFIGURATIONS
redis_db = redis.StrictRedis(host="broker", port=6379, db=0,
                             charset="utf-8", decode_responses=True)

logging.basicConfig(format='[%(asctime)s.%(msecs)03d] Function "%(funcName)s" from module "%(module)s" says: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)

counter_until = int(os.getenv('COUNTER'))

tz = os.getenv('TZ')
localtime = timezone(tz)

# TASK
@celery.task(bind=True, name='app.count')
def count(self, counter_value):
    return counter(counter_value)


# REST API
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='1.0', title='Tasks API',
          description='Simple tasks management REST API, using Flask + Celery')
api.namespaces.clear()
ns = api.namespace(
    'api', description='Allows to submit, schedule, and list tasks')


@ns.route('/task')
class Task(Resource):

    def get(self):
        '''Lists all processed tasks'''
        tasks = []
        for key in redis_db.scan_iter("celery-task-meta-*"):
            content = json.loads(redis_db.get(key))
            tasks.append({
                'id': content['task_id'],
                'status': content['status'],
                'date': timezone_aware(content['date_done'], tz)
            })

        tasks_by_date = sorted(tasks, key=lambda k: k['date'], reverse=True)
        all_tasks = {'tasks': tasks_by_date}

        if tasks:
            return jsonify(all_tasks)
        else:
            return jsonify({'info': 'No tasks has been issued so far.'})

    def post(self):
        '''Creates a new task at the current date/time'''
        count.apply_async([counter_until])
        response = jsonify({'status': 'Your task is been processed.'})
        return response


@ns.route('/<string:task_id>')
@ns.param('task_id', 'The specific task id you want to get details from.')
class TaskDetails(Resource):

    def get(self, task_id):
        '''Shows details from a specified task by it's id'''
        task = redis_db.get("celery-task-meta-" + str(task_id))
        if task:
            content = json.loads(task)
            task = {
                'id': content['task_id'],
                'status': content['status'],
                'result': content['result'],
            }
            return jsonify(task)
        else:
            return jsonify({'info': "That id can't be found."})


@ns.route('/<string:run_at>')
@ns.param('run_at',
          'When the task is expected to run, in the format YYYY-MM-DD-HH-mm-ss\ne.g. 2019-06-20-15-10-59\nNote that all fileds are optional, but seconds; i.e. /59 means to schedule a new task to the current date and time, but at 59 seconds.')
@ns.response(202, 'Your task is scheduled to be processed at...')
class ScheduledTask(Resource):

    def post(self, run_at):
        '''Schedules a task to a specified date/time'''
        due_date = get_datetime(run_at, tz)
        count.apply_async([counter_until], eta=localtime.localize(due_date))
        response = jsonify(
            {'status': f'Your task is scheduled to be processed at {due_date.strftime("%Y-%m-%d %H:%M:%S")}'})
        response.status_code = 202
        return response


api.add_resource(Task, '/task')
api.add_resource(TaskDetails, '/task/<string:task_id>')
api.add_resource(ScheduledTask, '/schedule/<string:run_at>')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
