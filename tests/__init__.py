from distutils.version import LooseVersion

import django

DJANGO_20 = LooseVersion(django.__version__) > LooseVersion('2.0')
