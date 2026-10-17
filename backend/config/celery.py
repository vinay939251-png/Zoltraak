"""
Celery asynchronous task queue configuration.
Connects to Redis message broker and result backend.
Supports eager execution mode (CELERY_TASK_ALWAYS_EAGER) for resilient zero-dependency local runs.
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('zoltraak')

# Load settings using namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
