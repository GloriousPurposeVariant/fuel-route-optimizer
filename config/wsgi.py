import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()


def _warm_up():
    # Imported here because it needs Django's apps to be loaded first.
    from routing.warmup import warm_up

    warm_up()


_warm_up()
