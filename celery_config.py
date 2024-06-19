from celery import Celery, Task

def celery_init_app(app):
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(
        app.import_name,
        backend=app.config['CELERY']['result_backend'],
        broker=app.config['CELERY']['broker_url']
    )
    celery.Task = FlaskTask
    celery.config_from_object(app.config['CELERY'])
    return celery
