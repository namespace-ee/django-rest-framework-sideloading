from distutils.version import LooseVersion

import django
from django.apps import AppConfig
from django.core.management import call_command

DJANGO_20 = LooseVersion(django.__version__) >= LooseVersion('2.0')


class TestsConfig(AppConfig):
    name = 'tests'
    verbose_name = "Tests"

    def ready(self):
        # apply migrations
        call_command('migrate')
