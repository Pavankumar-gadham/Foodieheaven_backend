import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodie_haven.settings')
app = Celery('foodie_haven')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()