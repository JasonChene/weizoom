#coding:utf8
from django.conf import settings
import logging

# This will cause your tasks to be called immediately at the point you say "task.delay(...)", so you can test the whole path (without any asynchronous behavior).
if settings.MODE == 'develop':
	# 如果需要在开发环境用同步模式，将CELERY_ALWAYS_EAGER置为True
	CELERY_ALWAYS_EAGER = False
	BROKER_URL = 'redis://redis.weapp.com//'
	# 置为True之后，会看到worker的异常，适合调试模式
	CELERY_EAGER_PROPAGATES_EXCEPTIONS = False
else:
	CELERY_ALWAYS_EAGER = False
	CELERY_EAGER_PROPAGATES_EXCEPTIONS = False
	BROKER_URL = 'amqp://rmq.weapp.com//'

CELERY_RESULT_BACKEND = 'redis://redis.weapp.com/3/'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT=['json']
CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = True
CELERYD_CONCURRENCY =  15
CELERYD_TASK_TIME_LIMIT = 60

if CELERY_ALWAYS_EAGER:
	logging.info("develop mode, no celery asynchronous behaviors")

from kombu import Queue, Exchange

#CELERY_DEFAULT_QUEUE = "weapp_default"
#CELERY_DEFAULT_ROUTING_KEY = 'default'
# CELERY_QUEUES = (
# 	#Queue('default', Exchange('default'), routing_key='default'),
# 	#Queue('services', Exchange('services'), routing_key='services.#'),
# 	#Queue('watchdog', Exchange('watchdog'), routing_key='watchdog.#')
# 	Queue('default', Exchange('default'), routing_key='default'),
# 	#Queue('services', routing_key='services.#'),
# 	#Queue('watchdog', routing_key='watchdog.#')
# )

"""
update by bert at 2015-06-19
增加队列name，并且动态路由
"""
QUEUE_LIST = []
QUEUE_LIST.append(Queue('default', Exchange('default'), routing_key='default'))
for task in settings.INSTALLED_TASKS:
	QUEUE_LIST.append(Queue(task, routing_key=task))
CELERY_QUEUES = tuple(QUEUE_LIST)

CELERY_DEFAULT_QUEUE = "default"
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

class MyRouter(object):

	def route_for_task(self, task, args=None, kwargs=None):
		# print settings.INSTALLED_TASKS

		if task == 'watchdog.send':
			return {
					'queue': 'default',
					}

		if task.find('.tasks.') > -1:
			task = task[:task.find('.tasks.')]

		if task in settings.INSTALLED_TASKS:
			return {
					'queue': task,
					}
		else:
			return None

# CELERY_ROUTES本来也可以用一个大的含有多个字典的字典,但是不如直接对它做一个名称统配
CELERY_ROUTES = (MyRouter(), )

