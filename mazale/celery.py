import os
from celery import Celery

# Replace 'your_project' with your actual project name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mazale.settings')

app = Celery('mazake')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')