from combinedapp import create_app
from celery_config import celery_init_app

flask_app = create_app()
celery_app = celery_init_app(flask_app)
