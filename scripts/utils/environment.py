import os

def test_environment():
    os.environ['ENV'] = 'test'

def celery_worker_environment():
    os.environ['CELERY_WORKER_RUNNING'] = 'True'