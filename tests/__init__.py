from distutils.version import LooseVersion

import django
from django.apps import AppConfig

DJANGO_20 = LooseVersion(django.__version__) >= LooseVersion("2.0")


class TestsConfig(AppConfig):
    name = "tests"
    verbose_name = "Tests"
